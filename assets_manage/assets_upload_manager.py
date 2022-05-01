from events import ServerEvent as SE, EventHolder
from data_holders import UploadDataHolder, console
from driver_init import init_driver_before_success, driver_upload_asset
from config import MetamaskConfig, CollectionConfig
from assets_manage.assets_handler import AssetsHandler

from typing import Union
from time import time as UnixTimestamp
from threading import Thread, Event, Lock
from queue import Queue, Empty as QueueEmptyException

from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.common.exceptions import TimeoutException

from urllib3.exceptions import HTTPError


class DriverInstance:
    """
    Class of workers, which will upload assets
    """
    def __init__(self, input_bus: Queue, output_bus: Queue, auth_lock: Lock, input_bus_lock: Event, worker_id: int) -> None:
        self.input_bus      = input_bus
        self.output_bus     = output_bus
        self.auth_lock      = auth_lock
        self.input_bus_lock = input_bus_lock

        self.worker_id = worker_id

        self.driver = None # type: Union[RemoteWebDriver, None]
        self.driver_init_time = None # type: Union[int, None] # UnixTimestamp

        self.close_event = Event()
        #self._prepare_for_work()
        self.working_thread = Thread(name=f"MNU-Worker-{self.worker_id}", target=self._prepare_for_work)
        self.working_thread.start()

    def close(self, join_thread=False) -> None:
        """
        Close driver and join thread if needed

        :param join_thread: Indicates to wait until the main thread will completed
        """
        self.close_event.set()
        if join_thread:
            self.working_thread.join()

    def _prepare_for_work(self) -> None:
        """Configure driver and start listen for events"""
        self.output_bus.put(EventHolder(SE.WORKER_PREPARE, self.worker_id))
        try:
            self._configure()
        except HTTPError as e:
            console.log(f"App was closed before, driver(worker_id={self.worker_id}) was initialized. You may close Browser by yourself", style="yellow")

        self._listen_events()

    def _configure(self) -> None:
        self.driver = init_driver_before_success(
            self.worker_id,
            self.output_bus,
            MetamaskConfig().secret_phase,
            MetamaskConfig().temp_password,
            auth_lock=self.auth_lock
        )
        self.driver_init_time = UnixTimestamp()

    def _listen_events(self) -> None:
        while not self.close_event.is_set():

            if not self.input_bus_lock.wait(2):
                continue
            try:
                incoming_event = self.input_bus.get(timeout=2)
            except QueueEmptyException:
                continue

            if not isinstance(incoming_event, EventHolder):
                self.output_bus.put(EventHolder(SE.WORKER_RECEIVED_NON_EVENT_HOLDER_OBJECT))
                continue

            if incoming_event.check(SE.INCOMING_TOKEN):
                incoming_payload = incoming_event.payload # type: UploadDataHolder

                if not isinstance(incoming_payload, UploadDataHolder):
                    self.output_bus.put(EventHolder(SE.WORKER_RECEIVED_NON_U_D_HOLDER_OBJECT))
                    continue

                if incoming_payload.token_expired:
                    self.output_bus.put(EventHolder(SE.WORKER_TOKEN_EXPIRED, incoming_payload.token))
                    continue
                self._try_upload(incoming_payload)

        if self.close_event.is_set():
            self.output_bus.put(EventHolder(SE.WORKER_STOPPED, self.worker_id))

        if self.driver is not None:
            self.driver.quit()

    def _try_upload(self, incoming_payload: UploadDataHolder) -> None:
        asset_id = incoming_payload.asset_id

        try:
            upload_response = driver_upload_asset(
                asset_data=incoming_payload.asset_data_for_upload,
                asset_id=asset_id,
                asset_abs_file_path=incoming_payload.file_path,
                driver=self.driver,
                wait_in_sec=CollectionConfig().max_upload_time
            )
            self.output_bus.put(EventHolder(SE.WORKER_COMPLETED_UPLOAD, upload_response))
        except TimeoutException:
            self.output_bus.put(EventHolder(SE.WORKER_UPLOAD_TIMEOUT_EXCEPTION, asset_id))
        except Exception:
            self.output_bus.put(EventHolder(SE.WORKER_UNKNOWN_ERROR_WHILE_UPLOAD, asset_id))


class AssetsUploadManager:
    """
    Configuring and managing pool of drivers, which will be run uploading process
    """

    _maximum_drivers = 4

    def __init__(self, server_event_bus: Queue) -> None:
        self.workers_bus = Queue() # type: Queue[EventHolder] # pushing to this queue assets nested in a UploadDataHolder # EventHolder(SE.INCOMING_TOKEN, payload=UploadDataHolder())
        self.output_bus = server_event_bus

        self.auth_lock = Lock()
        self.workers_bus_lock = Event()

        self.lock_drivers_input_bus()

        self.last_worker_id = 0 # type: int
        self.workers_pool = dict() # type: dict[int, DriverInstance]

        self.assets_handler = AssetsHandler(self.workers_bus, self.output_bus)

    def init_drivers(self, amount: int = 1) -> None:
        if len(self.workers_pool)<1:
            self.add_drivers(amount)
        else:
            self.close_drivers()
            self.init_drivers(amount)
            #TODO: add functionality for restarting

    def add_drivers(self, amount: int = 1):
        amount = amount if self.drivers_count + amount <= self.maximum_drivers else self.maximum_drivers - self.drivers_count
        for i in range(amount):
            self.add_driver()

    def add_driver(self) -> None:
        if self.drivers_count+1 <= self.maximum_drivers:
            self.workers_pool[self.last_worker_id] = DriverInstance(
                self.workers_bus,
                self.output_bus,
                self.auth_lock,
                self.workers_bus_lock,
                self.last_worker_id
            )
            self.last_worker_id+=1
        else:
            console.log("[yellow]Drivers limit exceed[/]")

    def stop_drivers(self, amount: int = 1) -> None:
        """Stop a certain amount of drivers"""
        amount = amount if amount <= self.drivers_count else self.drivers_count
        for i in range(amount):
            self.stop_last_drive()

    def stop_last_drive(self) -> None:
        if self.drivers_count>0:
            self.last_worker_id -= 1
            self.workers_pool.pop(self.last_worker_id).close(join_thread=False)

    def stop_target_driver(self, driver_id: str) -> None:
        """
        Raise stop event for target driver

        :param driver_id: Id of driver, which must stopped
        """
        #TODO

    def close_drivers(self) -> None:

        for driver in self.workers_pool.values():
            driver.close(join_thread=True)
        self.last_worker_id = 0
        self.workers_pool.clear()

    def on_stop(self):
        """Called when app is closing"""
        self.lock_drivers_input_bus()
        self.assets_handler.stop()
        self.close_drivers()

    def lock_drivers_input_bus(self) -> None:
        self.workers_bus_lock.clear()
        self.output_bus.put(EventHolder(SE.WORKER_EVENTS_BUS_LOCKED))

    def unlock_drivers_input_bus(self) -> None:
        self.workers_bus_lock.set()
        self.output_bus.put(EventHolder(SE.WORKER_EVENTS_BUS_UNLOCKED))

    @property
    def uploaded_assets_count(self):
        return self.assets_handler.uploaded_assets_count

    @property
    def assets_count(self):
        return self.assets_handler.assets_count

    @property
    def drivers_count(self) -> int:
        return len(self.workers_pool)

    @property
    def maximum_drivers(self) -> int:
        return self._maximum_drivers

    @property
    def have_drivers(self) -> bool:
        return self.drivers_count>0


if __name__ == "__main__":
    """Try init N drivers, then close all"""
    # TODO
    import time
    from queue import Empty
    event_bus = Queue()
    manager = AssetsUploadManager(event_bus)
    print(manager.have_drivers)
    target_count =3
    try:

        manager.init_drivers(target_count)
        while not manager.have_drivers:
            time.sleep(0.5)

        print("listening...", manager.have_drivers)
        count = 0
        while manager.have_drivers:
            if count>=target_count:
                break
            try:
                event = event_bus.get(timeout=0.5) # type: EventHolder
                if event.check(SE.WORKER_READY):
                    count += 1
                print(event)
            except Empty:
                ...
            time.sleep(0.2)
    except KeyboardInterrupt:
        ...
    finally:
        print("closing...")
        manager.close_drivers()
    print("end", event_bus.qsize())
