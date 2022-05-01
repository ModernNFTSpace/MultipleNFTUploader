from os import path


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


def abs_path_to_dir(file_path: str) -> str:
    return path.dirname(path.abspath(file_path))


MNU_BASE_DIR = abs_path_to_dir(__file__+"/../")

MNU_WEBDRIVER_BASE_PATH = path.join("bin", "chromedriver")
MNU_WEBDRIVER_ABS_PATH  = path.join(MNU_BASE_DIR, MNU_WEBDRIVER_BASE_PATH)

MNU_WEBDRIVER_ABS_PATH_PATTERN  = path.join(MNU_BASE_DIR, f"{MNU_WEBDRIVER_BASE_PATH}*")


def abs_path_from_base_dir_relative(relative_path: str) -> str:
    return path.join(MNU_BASE_DIR, relative_path)
