from dataclasses import dataclass
from typing import Any, Type
from enum import Enum


class MNUEnum(Enum):
    ...


@dataclass
class EventHolder:
    event: MNUEnum
    payload: Any = None

    def check(self, *events_type: MNUEnum):
        for event in events_type:
            if self.event == event:
                return True
        return False


class ServerEvent(MNUEnum):
    #FROM WORKERS
    WORKER_PREPARE                   = 0
    WORKER_READY                     = 1
    WORKER_STOPPED                   = 2
    WORKER_STOPPED_AS_FIRST_RECEIVER = 3
    WORKER_EVENTS_BUS_LOCKED         = 5
    WORKER_EVENTS_BUS_UNLOCKED       = 6
    WORKER_COMPLETED_UPLOAD          = 8

    #FROM SERVER
    INCOMING_TOKEN      = 20
    STOP_FIRST_RECEIVER = 25

    #FROM ASSETS HANDLER
    AH_ASSETS_ARE_OVER = 100

    #WARNING
    WORKER_TOKEN_EXPIRED = 300

    #ERRORS
    WORKER_DRIVER_INITIALIZING_FAILURE      = 500
    WORKER_DRIVER_INIT_ATTEMPTS_EXCEEDED    = 501
    WORKER_DRIVER_INIT_TECHNICAL_ERROR      = 502 # payload: MNUDriverInitError
    WORKER_RECEIVED_NON_EVENT_HOLDER_OBJECT = 511
    WORKER_RECEIVED_NON_U_D_HOLDER_OBJECT   = 512
    WORKER_UNKNOWN_ERROR_WHILE_UPLOAD       = 520
    WORKER_UPLOAD_TIMEOUT_EXCEPTION         = 521


class UIRequestEvent(MNUEnum):
    NEW_UI_CLIENT_REGISTERED = 0 # payload: {}
    UI_COMMAND_UPLOADING     = 1 # payload: {action: str}
    UI_COMMAND_DRIVERS       = 2 # payload: {action: str, count: str}
    UI_COMMAND_SERVER_ACTION = 3 # payload: {action: str}
