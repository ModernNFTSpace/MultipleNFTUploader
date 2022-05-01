from typing import Dict, Tuple
import pytest

from queue import Queue

from events import EventHolder, ServerEvent
from driver_init import init_driver_before_success


# For testing reasons you may use this Metamask Secret Phrases
# Hardcoded permanently.
#
# For uploading paste your credentials to config.CollectionConfig config file

pytest.metamask_conf = {
    "SECRET_PHRASE": "can truly carbon leader pattern dream conduct acquire shadow base loyal stadium",
    "TEMP_PASSWORD": "MNU_M3tam@skp@$$25a163",
    "COLLECTION_SLUG": "ttt-with-t",
}


@pytest.fixture(scope="session")
def driver():
    init_events = Queue()
    max_attempts = 2

    m_secret = pytest.metamask_conf["SECRET_PHRASE"]
    m_password = pytest.metamask_conf["TEMP_PASSWORD"]

    new_driver = init_driver_before_success(
        worker_id=0,
        output_bus=init_events,
        max_attempts=max_attempts,
        secret_phases=m_secret,
        temp_password=m_password
    )
    for i in range(init_events.qsize()):
        ev = init_events.get()  # type: EventHolder
        if ev.check(ServerEvent.WORKER_READY):
            break
        elif ev.check(ServerEvent.WORKER_DRIVER_INIT_ATTEMPTS_EXCEEDED):
            # driver initialization failed
            raise Exception("Driver initialization failed")

    yield new_driver
    new_driver.quit()

# store history of failures per test class name and per index in parametrize (if parametrize used)
_test_failed_incremental: Dict[str, Dict[Tuple[int, ...], str]] = {}


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "incremental: Stop tests after failure"
    )


def pytest_runtest_makereport(item, call):
    if "incremental" in item.keywords:
        # incremental marker is used
        if call.excinfo is not None:
            # the test has failed
            # retrieve the class name of the test
            cls_name = str(item.cls)
            # retrieve the index of the test (if parametrize is used in combination with incremental)
            parametrize_index = (
                tuple(item.callspec.indices.values())
                if hasattr(item, "callspec")
                else ()
            )
            # retrieve the name of the test function
            test_name = item.originalname or item.name
            # store in _test_failed_incremental the original name of the failed test
            _test_failed_incremental.setdefault(cls_name, {}).setdefault(
                parametrize_index, test_name
            )


def pytest_runtest_setup(item):
    if "incremental" in item.keywords:
        # retrieve the class name of the test
        cls_name = str(item.cls)
        # check if a previous test has failed for this class
        if cls_name in _test_failed_incremental:
            # retrieve the index of the test (if parametrize is used in combination with incremental)
            parametrize_index = (
                tuple(item.callspec.indices.values())
                if hasattr(item, "callspec")
                else ()
            )
            # retrieve the name of the first test function to fail for this class name and index
            test_name = _test_failed_incremental[cls_name].get(parametrize_index, None)
            # if name found, test has failed for the combination of class name & test name
            if test_name is not None:
                pytest.xfail("previous test failed ({})".format(test_name))