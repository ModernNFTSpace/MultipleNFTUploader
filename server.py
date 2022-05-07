from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from config import MNUSecrets, CollectionConfig
from version import __version__, __server_version__, __name__ as app_name

from data_holders import UploadResponseHolder, SessionsHolder
from events import EventHolder, ServerEvent, UIRequestEvent
from assets_manage.assets_upload_manager import AssetsUploadManager
from mnu_api_primitives import UIStateHolder
from mnu_utils import console

from typing import Optional
from threading import Thread, Event, Semaphore
from queue import Queue

import socket
import requests

import json
import time

from rich.status import Status
from rich.tree import Tree


class MNUServerException(Exception):
    """Base Server Exception"""


class StopServerException(Exception):
    """Mainly used to stop the server"""


def check_port_availability(port: int) -> bool:
    """
    Check port availability

    :param port: Port number
    :return: True if port is free or connection refused(in general it mean that the port is free), False if port already used
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) != 0


class MNURequestHandler(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        super(MNURequestHandler, self).__init__(request, client_address, server)

    def _set_headers(self, r_code=200, headers=tuple(tuple())):
        self.send_response(r_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        for h in headers:
            if len(h)>1:
                self.send_header(h[0], h[1])
        self.end_headers()

    def _check_path(self, path) -> bool:
        return path in self.path.strip('/')

    def _get_params_after_path(self, path) -> list[str]:
        raw_params = self.path.split(path)[-1].strip('/')

        return raw_params.split('/')

    def _check_secret(self) -> bool:
        return self.server.mnu_ui_secret == self.headers.get("mnu_ui_secret")

    def _check_auth(self) -> Optional[SessionsHolder.Session]:
        session_key = self.headers.get("mnu_session_key")
        if session_key is None:
            return None

        return self.server.sessions_holder.get_session(session_key)

    def _try_load_json_body(self):
        content_length = int(self.headers.get('content-length'), 0)
        try:
            request_body = json.loads(self.rfile.read(content_length))
        except json.JSONDecodeError:
            request_body = {}
        return request_body

    def _push_event_to_bus(self, event: UIRequestEvent, **payload):
        self.server.ui_events_bus.put(EventHolder(event=event, payload=payload))

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        """
        /ui/state
        """
        if self._check_secret() is None:
            self._set_headers(401)
            return

        if self._check_path('ui/state'):
            self._set_headers(200)
            self.wfile.write(self.server.server_state.json_encoded().encode('utf-8'))

        else:
            self._set_headers(404)

    def do_POST(self):
        """
        /ui/init
        """

        if self._check_path('ui/init'):

            request_body = self._try_load_json_body()

            client_name = self.headers.get('ui_client_name', None)
            new_session_key = self.server.sessions_holder.open_session(
                self.headers.get("mnu_ui_secret"),
                request_body.get("callback_url", None),
                client_name
            )

            if new_session_key is None:
                self._set_headers(403)
                return
            else:
                self._set_headers(200)
                self.wfile.write(f'{{"session_key":"{new_session_key}"}}'.encode('utf-8'))
                self._push_event_to_bus(UIRequestEvent.NEW_UI_CLIENT_REGISTERED)

        else:
            self._set_headers(404)

    def do_PUT(self):
        """
        /ui/commands/uploading/{action}
        /ui/commands/drivers/{action}/{count}
        /ui/commands/server/stop
        """

        session = self._check_auth()
        if session is None:
            self._set_headers(401)
            return

        if self._check_path('ui/commands/uploading'):
            params = self._get_params_after_path('ui/commands/uploading')
            if len(params) != 1:
                self._set_headers(404)
                return
            action = params[0]
            self._push_event_to_bus(UIRequestEvent.UI_COMMAND_UPLOADING, action=action)

        elif self._check_path('ui/commands/drivers'):
            params = self._get_params_after_path('ui/commands/drivers')
            if len(params) != 2:
                self._set_headers(404)
                return
            action, count = params
            self._push_event_to_bus(UIRequestEvent.UI_COMMAND_DRIVERS, action=action, count=count)

        elif self._check_path('ui/commands/server/stop'):
            self._push_event_to_bus(UIRequestEvent.UI_COMMAND_SERVER_ACTION, action='stop')

        else:
            self._set_headers(404)


class MNUServer(ThreadingHTTPServer):
    """
    ModernNFTUploader`s Server provide API for:
        (CaptchaWorkers(!suspended indefinitely)) paths:
            /worker/init
            /worker/captcha_token
        (UserInterface) paths:
            See docs/mnu_server_api.yaml for details
    """
    _server_version = __server_version__

    def __init__(self, ui_events_bus: Queue, server_address, request_handler_class=MNURequestHandler, bind_and_activate=True):
        super(MNUServer, self).__init__(server_address, request_handler_class, bind_and_activate)
        self.ui_events_bus = ui_events_bus
        self.mnu_ui_secret = MNUSecrets().ui_secret
        self.sessions_holder = SessionsHolder(self.mnu_ui_secret)
        self.server_state = UIStateHolder()
        self.server_state.set_state_change_callback(self.server_state_changed)

        self._server_thread = Thread(name="ServerThread-Main", target=self.serve_forever)
        self._state_distributor_lock = Semaphore(20)
        self._state_distributor_stop_event = Event()
        self._state_distributor_thread = Thread(name="ServerThread-StateDistributor", target=self.server_state_distributor)

    def server_state_changed(self):
        pass

    def _send_state(self, client_session: SessionsHolder.Session, state: dict):
        try:
            headers = {"mnu_session": client_session.session_key}
            resp = requests.post(client_session.callback_url, json=state, headers=headers)
            if resp.status_code != 201:
                client_session.unsubscribe()
        except Exception:
            client_session.unsubscribe()
        finally:
            self._state_distributor_lock.release()

    def server_state_distributor(self, wait_requests: bool = False):
        def infinity_range():
            i = 0
            while True:
                yield i
                i += 1
        _threads = []
        one_cycle = wait_requests
        while not self._state_distributor_stop_event.is_set() or one_cycle:
            one_cycle = False
            _threads.clear()
            for client_session, subscriber_index in zip(self.sessions_holder.get_callback_subscribers(), infinity_range()):
                self._state_distributor_lock.acquire()
                new_request = Thread(
                    name=f"StateDistributor-Request-{subscriber_index}",
                    target=self._send_state,
                    daemon=True,
                    kwargs={"client_session": client_session, "state": self.server_state.as_dict()}
                )
                new_request.start()
                _threads.append(new_request)
            time.sleep(0.3)

        if wait_requests:
            for thr in _threads:
                thr.join()

    def start(self):
        self.server_state.server_info.server_status = "ready"
        self._server_thread.start()
        self._state_distributor_thread.start()

    def stop(self):
        self.server_state.server_info.server_status = "shutdown"
        self._state_distributor_stop_event.set()
        self.shutdown()
        self._server_thread.join()
        self.server_close()
        self.server_state.drivers_data.uploading_is_active = False


class MNUHandler:
    """
    Class provide communication between UI and program
    #TODO: rewrite to asyncio for best performance
    """
    _server_address = "127.0.0.1" # you can change this on "0.0.0.0" or "" for listen on all interfaces. But not recommended for security reasons
    _init_drivers_on_start = 1 # on 1 opensea account 1 driver

    def __init__(self, port: int):
        self.uploader_events_bus = Queue() # type: Queue[EventHolder] # bus with events from workers(uploaders)
        self.ui_events_bus = Queue() # type: Queue[EventHolder] # bus with events from UI(MNUServer pushing events)
        self.upload_manager = AssetsUploadManager(self.uploader_events_bus)
        self.server = MNUServer(ui_events_bus=self.ui_events_bus, server_address=(self._server_address, port))

        self._configure()

    def _configure(self):
        self.server.server_state.setup_values(
            assets_in_collection=self.upload_manager.assets_count,
            assets_uploaded=self.upload_manager.uploaded_assets_count,
            collection_name=CollectionConfig().collection_name,

            maximum_drivers=self.upload_manager.maximum_drivers,

            app_name=app_name,
            app_version=__version__,
            server_version=self.server._server_version
        )

    def run(self, rich_status: Optional["Status"] = None):
        self.server.start()
        self.upload_manager.init_drivers(self._init_drivers_on_start)
        try:
            while True:
                if not self.uploader_events_bus.empty():
                    #
                    # Uploading events handling section
                    #
                    upload_event = self.uploader_events_bus.get(block=False) # type: EventHolder
                    try:
                        assert isinstance(upload_event, EventHolder)

                        payload = upload_event.payload
                        if upload_event.check(ServerEvent.WORKER_COMPLETED_UPLOAD):
                            if not isinstance(payload, UploadResponseHolder):
                                raise ValueError(f"payload type: {type(payload)}")
                            upload_response = payload # type: UploadResponseHolder
                            if self.upload_manager.assets_handler.asset_uploaded(upload_response):
                                self.server.server_state.trigger_asset_upload(upload_response.time_spent_on_upload)
                            else:
                                self.upload_manager.lock_drivers_input_bus()
                                #print errors

                                u_errors = upload_response.store.get("errors", None) # type: Optional[list[dict]]
                                if u_errors is not None:
                                    root = Tree(f"[red]Errors occurred during uploading asset(id={upload_response.asset_id})", highlight=True, guide_style="green")
                                    for err in u_errors:
                                        root.add(f"[red]{err.get('message', 'Unknown error')}")
                                    console.log(root)
                                else:
                                    console.log(f"[red]Error occurred during uploading asset(id={upload_response.asset_id})")

                        elif upload_event.check(ServerEvent.WORKER_STOPPED, ServerEvent.WORKER_STOPPED_AS_FIRST_RECEIVER):
                            self.server.server_state.trigger_set_drivers_count(self.upload_manager.drivers_count)
                        elif upload_event.check(ServerEvent.WORKER_PREPARE):
                            ...
                        elif upload_event.check(ServerEvent.WORKER_READY):
                            self.server.server_state.trigger_set_drivers_count(self.upload_manager.drivers_count)
                            if isinstance(payload, dict):
                                self.server.server_state.trigger_driver_init(payload["duration"])

                        elif upload_event.check(ServerEvent.WORKER_EVENTS_BUS_LOCKED):
                            self.server.server_state.drivers_data.uploading_is_active = False
                        elif upload_event.check(ServerEvent.WORKER_EVENTS_BUS_UNLOCKED):
                            self.server.server_state.drivers_data.uploading_is_active = True

                        elif upload_event.check(ServerEvent.WORKER_DRIVER_INITIALIZING_FAILURE):
                            ...
                        elif upload_event.check(ServerEvent.WORKER_DRIVER_INIT_ATTEMPTS_EXCEEDED):
                            ...

                        elif upload_event.check(ServerEvent.WORKER_RECEIVED_NON_EVENT_HOLDER_OBJECT):
                            ...
                        elif upload_event.check(ServerEvent.WORKER_RECEIVED_NON_U_D_HOLDER_OBJECT):
                            ...

                        elif upload_event.check(ServerEvent.WORKER_UNKNOWN_ERROR_WHILE_UPLOAD):
                            self.upload_manager.assets_handler.asset_uploading_failed(payload)
                        elif upload_event.check(ServerEvent.WORKER_UPLOAD_TIMEOUT_EXCEPTION):
                            self.upload_manager.assets_handler.asset_uploading_failed(payload)

                        elif upload_event.check(ServerEvent.WORKER_TOKEN_EXPIRED):
                            ...
                    except AssertionError as AE:
                        console.log("[red]During handling uploading event received wrong type EventHandler[/]", AE)
                    except ValueError as VE:
                        console.log("[red]During handling uploading event received wrong type payload[/]", VE)

                if not self.ui_events_bus.empty():
                    #
                    # UI action events handling section
                    #
                    ui_event = self.ui_events_bus.get(block=False) # type: EventHolder
                    try:
                        assert isinstance(ui_event.payload, dict)
                        if ui_event.check(UIRequestEvent.NEW_UI_CLIENT_REGISTERED):
                            self.server.server_state.trigger_client_connected()

                        elif ui_event.check(UIRequestEvent.UI_COMMAND_UPLOADING):
                            action = ui_event.payload["action"]
                            if action == "stop":
                                self.upload_manager.lock_drivers_input_bus()
                            elif action == "start":
                                self.upload_manager.unlock_drivers_input_bus()
                            else:
                                console.log(f"[yellow]During handling UI_COMMAND_UPLOADING received wrong action([red]{action}[/])[/]")

                        elif ui_event.check(UIRequestEvent.UI_COMMAND_DRIVERS):
                            action, str_count = ui_event.payload["action"], ui_event.payload["count"] # type: (str, str)
                            count = 0
                            if str_count.isdigit():
                                count = int(str_count)
                            elif str_count == "all":
                                count = self.upload_manager.maximum_drivers
                            elif str_count == "one":
                                count = 1

                            if action == "add":
                                self.upload_manager.add_drivers(count)
                            elif action == "remove":
                                self.upload_manager.stop_drivers(count)
                            elif action == "remove_all_and_add":
                                self.upload_manager.close_drivers()
                                self.upload_manager.init_drivers(count)

                        elif ui_event.check(UIRequestEvent.UI_COMMAND_SERVER_ACTION):
                            action = ui_event.payload["action"] # Now action -> only "stop"
                            # TODO: Add functionality
                            raise StopServerException()

                    except KeyError as KE:
                        console.log("[red]Error during accessing payload key[/]", KE)

                    except AssertionError as AE:
                        console.log("[red]During handling UI event received wrong type payload[/]", AE)

        except (KeyboardInterrupt, StopServerException):
            if rich_status is not None:
                rich_status.update('Server closing, please wait', spinner='hamburger', spinner_style="blue")
            self.on_stop()

    def on_stop(self):
        self.server.stop()
        self.upload_manager.on_stop()

        #last notify
        self.server.server_state_distributor(wait_requests=True)


def main():
    from mnu_utils import get_server_argparser
    import subprocess
    import sys
    import os

    arguments = get_server_argparser()

    parsed_args = arguments.parse_args()

    autorun_ui = parsed_args.ui
    server_port = int(parsed_args.port)
    external_ui_path = parsed_args.external_ui

    def run_gui_with_delay(ui_path=external_ui_path, server_addr=MNUHandler._server_address, server_port=server_port,
                           delay=2, auto_connect=True):
        ui_path = os.path.abspath(ui_path)
        if os.path.isfile(ui_path):
            try:
                time.sleep(delay)
                subprocess.Popen(
                    [sys.executable, ui_path, f"--server-addr={server_addr}", f"--server-port={server_port}",
                     f"{'--auto-connect' if auto_connect else ''}"])
            except Exception as e:
                console.log(f"[red]Error occurred while calling UI({e})")
        else:
            console.log(f"[red]UI path is invalid({ui_path})")

    console.log("App started")

    with console.status("Server starting...", spinner="dots", spinner_style="red") as status:
        handler = MNUHandler(server_port)
        if autorun_ui:
            console.log(f"Starting UI # {external_ui_path}")
            Thread(target=run_gui_with_delay, name="UI-Runner", daemon=True).start()
        else:
            console.log(f"UI autorun turned off")
        status.update('Server working', spinner='hamburger', spinner_style="green")
        handler.run(status)
    console.log("App closed.")


if __name__ == "__main__":
    main()
