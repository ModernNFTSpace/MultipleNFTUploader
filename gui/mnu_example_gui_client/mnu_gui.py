import os
import sys

os.environ["KIVY_NO_ARGS"] = "1"
directory = os.path.abspath(__file__ + "/../../../")
sys.path.append(directory)

from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread, Event
from queue import Queue, Empty as QueueEmptyException

from typing import Optional, Union, Literal, Any, get_args

from mnu_api_primitives import UIStateHolder, construct_MNUAPIPrimitive_from_dict, _type_of_primitive_holder

from config import MNUClientConfig

import requests
import socket
import json
import time

from kivy.app import App
from kivy.lang.builder import Builder
from kivy.animation import Animation
from kivy.uix.screenmanager import ScreenManager, Screen, WipeTransition
from kivy.properties import NumericProperty, OptionProperty, StringProperty, DictProperty, BooleanProperty

from kivy.core.window import Window
from kivy.config import Config
from kivy.clock import Clock

Config.set('kivy', 'log_level', 'error')

Builder.load_file("kivy_markup.kv")


def check_port_availability(port: int) -> bool:
    """
    Check port availability

    :param port: Port number
    :return: True if port is free or connection refused(in general it mean that the port is free), False if port already used
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) != 0


def find_free_port(start_from: int = 18041) -> int:
    """
    Find free port for binding

    :param start_from: First port which will be checked
    :return: Free port number
    """
    while not check_port_availability(start_from):
        start_from += 1
    return start_from


class MNUClientRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, r_code: int = 201, headers = tuple(tuple())):
        self.send_response(r_code)
        for h in headers:
            if len(h)>1:
                self.send_header(h[0], h[1])
        self.end_headers()

    def _check_session(self) -> bool:
        return self.server.mnu_session is not None and self.server.mnu_session == self.headers.get("mnu_session")

    def _try_load_json_body(self):
        content_length = int(self.headers.get('content-length'), 0)
        try:
            request_body = json.loads(self.rfile.read(content_length))
        except json.JSONDecodeError:
            request_body = {}
        return request_body

    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_POST(self):
        if self._check_session():
            request_body = self._try_load_json_body()
            if request_body and isinstance(request_body, dict) and request_body.get(_type_of_primitive_holder, False):
                self.server.trigger_state_update(construct_MNUAPIPrimitive_from_dict(request_body))

            self._set_headers()
        else:
            self._set_headers(403)


class MNUploaderClientServer(HTTPServer):
    """
    Server/client wrapper for working with MNUServer
    """

    available_endpoints = Literal["server/stop", "uploading/stop", "uploading/start"]
    available_commands = Literal["server", "uploading"]

    def __init__(self, mnu_server_address: DictProperty, server_state_bus: Queue, use_callback: bool, client_addr: str = "127.0.0.1", request_handler_class=MNUClientRequestHandler, bind_and_activate=True):
        self.mnu_server_address = mnu_server_address
        self.server_state_bus = server_state_bus
        self.use_callback = use_callback
        self.client_port = find_free_port()
        client_address = (client_addr, self.client_port)
        super(MNUploaderClientServer, self).__init__(client_address, request_handler_class, bind_and_activate)

        self.callback_addr = f"http://{client_addr}:{self.client_port}/"

        self.server_thread = None # type: Optional[Thread]

        self.mnu_session = None # type: Optional[str]

    def make_init_server_address(self):
        return f"http://{self.mnu_server_address['addr']}:{self.mnu_server_address['port']}/v1/ui/init"

    def _make_server_command_address(self, command: available_commands, action: Any):
        return f"http://{self.mnu_server_address['addr']}:{self.mnu_server_address['port']}/v1/ui/commands/{command}/{action}"

    def init_session(self, return_bus: Queue):
        headers = {"mnu_ui_secret": MNUClientConfig().mnu_ui_secret}
        body = {"callback_url": self.callback_addr}
        try:
            resp = requests.post(self.make_init_server_address(), json=body, headers=headers)
        except Exception as e:
            time.sleep(2)
            return_bus.put(None)
            return
        if resp.status_code == 200:
            #success
            try:
                resp = resp.json()
                self.mnu_session = resp["session_key"]
            except Exception:
                ...
        else:
            #invalid secret
            ...
        return_bus.put(self.mnu_session)

    def send_command(self, command: available_endpoints):
        if self.mnu_session is None:
            raise ValueError("MNUploaderClientServer.mnu_session must be valid token, not NoneType")
        args = get_args(self.available_endpoints)
        if command in args:
            headers = {"mnu_session_key": self.mnu_session}
            if command == "server/stop":
                url = self._make_server_command_address("server", "stop")
                requests.put(url, headers=headers)
            elif command == "uploading/stop":
                url = self._make_server_command_address("uploading", "stop")
                requests.put(url, headers=headers)
            elif command == "uploading/start":
                url = self._make_server_command_address("uploading", "start")
                requests.put(url, headers=headers)

    def start(self):
        if self.use_callback:
            self.server_thread = Thread(target=self.serve_forever, name="Server-CallbackListener", daemon=True)
            self.server_thread.start()

    def trigger_state_update(self, new_state: UIStateHolder):
        self.server_state_bus.put(new_state)

#
# GUI Section
#


class MNUConnectionScreen(Screen):
    name: str = "MNUConnectionScreen"

    def setup_server_address(self, server_init_event: Event, try_to_connect_after_init: bool = False):
        Clock.schedule_once(lambda dt: self._check_server_init(server_init_event, try_to_connect_after_init))

    def _check_server_init(self, server_init_event: Event, try_to_connect_after_init: bool):
        if server_init_event.is_set():
            self.disabled = False
            if try_to_connect_after_init:
                self.connect_btn_trigger(App.get_running_app(), 1.5)
        else:
            Clock.schedule_once(lambda dt: self._check_server_init(server_init_event, try_to_connect_after_init))

    def connect_btn_trigger(self, app, request_time_limit: Union[int, float] = 5):
        self.disabled = True
        self.ids.mnu_connection_error.opacity = 0
        self.spinner_anim = Animation(angle=360, duration=-1)
        self.spinner_anim.start(self.ids.connection_spinner)


        return_bus = app._connect_to_server()
        interval = 0.1

        def _wrapper(dt):
            self._wait_request_end(interval, return_bus, app, request_time_limit)

        Clock.schedule_once(_wrapper)

    def _wait_request_end(self, interval, return_bus: Queue, app, limit=5, timer=0):
        if limit>timer:
            if timer>= interval*3 and self.ids.connection_spinner.opacity != 1:
                self.ids.connection_spinner.opacity = 1
            try:
                res = return_bus.get(timeout=interval)
                if res is not None:
                    app._session_granted()
                    self._finish_connection(True)
                else:
                    self._finish_connection(False)
                return
            except QueueEmptyException:
                ...
            Clock.schedule_once(lambda dt: self._wait_request_end(interval, return_bus, app, limit, timer+interval))
        else:
            self._finish_connection(False)

    def _finish_connection(self, success: bool):
        if not success:
            self.ids.mnu_connection_error.opacity = 1
        self.disabled = False
        self.ids.connection_spinner.opacity = 0
        self.spinner_anim.cancel(self.ids.connection_spinner)


class MNUSessionScreen(Screen):
    name: str = "MNUSessionScreen"

    opt_server_address = StringProperty("...")
    opt_server_status  = OptionProperty("shutdown", options=["shutdown", "ready"])

    opt_collection_name = StringProperty("mnu")
    opt_uploading_time = NumericProperty(0)

    opt_remaining_time = NumericProperty(86400)

    opt_drivers_count = DictProperty({"count": 1, "max": 4})
    opt_assets_count = DictProperty({"count": 11, "max": 40})

    opt_driver_init_time = NumericProperty(0)

    opt_upload_status = OptionProperty("Stopped", options=["Waiting for drivers...", "Stopped", "Uploading..."])

    opt_disable_upload_btns = BooleanProperty(False)
    opt_disable_start_upload_btns = BooleanProperty(False)

    def update_state(self, new_state: UIStateHolder):
        #TODO: Check once collection exists via https://api.opensea.io/api/v1/collection/collection-sluq
        #      And add hyperlink to markup
        self.ids.btns_container.disabled = False
        self.opt_server_status = new_state.server_info.server_status
        self.opt_disable_upload_btns = new_state.drivers_data.active_drivers <= 0
        self.opt_upload_status = "Waiting for drivers..." if self.opt_disable_upload_btns else ("Uploading..." if new_state.drivers_data.uploading_is_active else "Stopped")

        self.opt_collection_name = new_state.assets_data.collection_name

        self.opt_drivers_count["count"] = new_state.drivers_data.active_drivers
        self.opt_drivers_count["max"] = new_state.drivers_data.maximum_drivers

        self.opt_assets_count["count"] = new_state.assets_data.assets_uploaded
        self.opt_assets_count["max"] = new_state.assets_data.assets_in_collection

        self.opt_disable_start_upload_btns = new_state.drivers_data.uploading_is_active

        self.opt_driver_init_time = new_state.average_t_s_o_l_driver_init
        self.opt_uploading_time = new_state.average_t_s_o_l_upload

        self.opt_remaining_time = (self.opt_assets_count["max"] - self.opt_assets_count["count"])*self.opt_uploading_time

        is_server_running = "shutdown" != self.opt_server_status
        if not is_server_running:
            self.ids.btns_container.disabled = True
            self.opt_upload_status = "Stopped"

    def send_command(self, command: MNUploaderClientServer.available_endpoints, app):
        self.ids.btns_container.disabled = True
        app._send_command(command)


class MNUploaderGUI(App):
    use_callback: bool = True
    server_address = DictProperty({"addr": "127.0.0.1", "port": 18040})

    def __init__(self, server_address: str, server_port: int, try_to_connect_after_init: bool = False, **kwargs):
        super(MNUploaderGUI, self).__init__(**kwargs)
        self.try_to_connect_after_init = try_to_connect_after_init

        self.server_address["addr"] = server_address
        self.server_address["port"] = server_port

        self.server_state_bus = Queue()

        self.server = None # type: Optional[MNUploaderClientServer]
        self.server_initialized_event = Event()

        self.connection_screen = MNUConnectionScreen()
        self.session_screen = MNUSessionScreen()

        self.screen_manager = ScreenManager(transition=WipeTransition())
        self.screen_manager.add_widget(self.connection_screen)
        self.screen_manager.add_widget(self.session_screen)

    def _set_server_addr(self, value):
        self.server_address["addr"] = value

    def _set_server_port(self, instance, value: str):
        if value.isdigit():
            self.server_address["port"] = int(value)
        else:
            instance.text = ""

    def _send_command(self, command: MNUploaderClientServer.available_endpoints):
        Thread(target=self.server.send_command, args=(command,), name="SendingCommandToServer", daemon=True).start()

    def _session_granted(self):
        self.server.start()
        Clock.schedule_interval(self._listen_for_server_state_change, 0.1)
        self.session_screen.opt_server_address = f"{self.server_address['addr']}:{self.server_address['port']}"
        self.session_screen.update_state(UIStateHolder())
        self.screen_manager.transition.duration = 0.5
        self.screen_manager.transition.direction = 'left'
        self.screen_manager.current = "MNUSessionScreen"

    def _listen_for_server_state_change(self, dt):
        if not self.server_state_bus.empty():
            last_state = None # type: Optional[UIStateHolder]
            for i in range(self.server_state_bus.qsize()):
                last_state = self.server_state_bus.get()
            self.session_screen.update_state(last_state)

    def _connect_to_server(self) -> Queue:
        self.server_initialized_event.wait()
        return_bus = Queue()
        Thread(target=self.server.init_session, args=(return_bus,), name="InitRequest", daemon=True).start()
        return return_bus

    def build(self):
        Config.set('graphics', 'resizable', False)

        Window.size = (500, 400)

        return self.screen_manager

    def close(self):
        ...

    def on_start(self):
        self.connection_screen.setup_server_address(server_init_event=self.server_initialized_event, try_to_connect_after_init=self.try_to_connect_after_init)
        Thread(target=self.start_server).start()

    def start_server(self):
        self.server = MNUploaderClientServer(self.server_address, self.server_state_bus, self.use_callback)
        self.server_initialized_event.set()

if __name__ == "__main__":
    MNUploaderGUI("127.0.0.1", 18040).run()
