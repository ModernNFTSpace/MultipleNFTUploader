from os import path
from rich.console import Console

import argparse
import sys

console = Console()

CURRENT_PLATFORM = sys.platform


class AverageTime:
    """Accumulating value and calculating average"""
    def __init__(self) -> None:
        self.count = 0 # type: int
        self.sum   = 0 # type: float

    def __len__(self) -> int:
        return self.count

    @property
    def average(self) -> float:
        return self.sum/self.count if self.count>0 else 0

    @property
    def safe_average(self) -> float:
        """
        Use if you need to divide by returned value
        :return: Zero Division safe value
        """
        return self.sum/self.count if self.count>0 else 1

    def add(self, value: float) -> None:
        self.sum   += value
        self.count += 1


def get_server_argparser() -> argparse.ArgumentParser:
    from config import MNUServerConfig
    arguments = argparse.ArgumentParser()

    group = arguments.add_argument_group("Server arguments")
    group.add_argument("--ui", help="Autorun UI", action=argparse.BooleanOptionalAction, default=True)
    group.add_argument("--external-ui", help="Path to external UI implementation",
                           default=MNUServerConfig().external_gui_path)
    group.add_argument("--port", help="Server port. UI will connect to this port",
                           default=MNUServerConfig().server_port)
    return arguments


def abs_path_to_dir(file_path: str) -> str:
    return path.dirname(path.abspath(file_path))


MNU_BASE_DIR = abs_path_to_dir(__file__+"/../")

MNU_WEBDRIVER_DIR_PATH = path.join(MNU_BASE_DIR, "bin")
MNU_WEBDRIVER_EXE_NAME = "chromedriver"
MNU_WEBDRIVER_ABS_PATH  = path.join(MNU_WEBDRIVER_DIR_PATH, MNU_WEBDRIVER_EXE_NAME)

MNU_WEBDRIVER_ABS_PATH_PATTERN  = f"{MNU_WEBDRIVER_ABS_PATH}*"


def abs_path_from_base_dir_relative(relative_path: str) -> str:
    return path.join(MNU_BASE_DIR, relative_path)
