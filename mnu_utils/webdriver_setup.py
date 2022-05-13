from typing import Optional, Tuple
from urllib.request import urlopen, urlretrieve
from urllib.parse import urljoin
from glob import glob

from . import MNU_WEBDRIVER_DIR_PATH, MNU_WEBDRIVER_EXE_NAME, CURRENT_PLATFORM

import zipfile
import random
import string
import re
import io
import os


class WebDriverPatcher:
    """
    Removing "cdc_" token from webdriver binary
    """

    def __init__(self, web_driver_path: str):
        self.executable_path = web_driver_path

    @staticmethod
    def random_cdc():
        cdc = random.choices(string.ascii_lowercase, k=26)
        cdc[-6:-4] = map(str.upper, cdc[-6:-4])
        cdc[2] = cdc[0]
        cdc[3] = "_"
        return "".join(cdc).encode()

    def patch_binary(self) -> int:
        """
        Patches the ChromeDriver binary
        :return: Count of affected lines
        """
        linect = 0
        replacement = self.random_cdc()

        with io.open(self.executable_path, "r+b") as fh:
            for line in iter(lambda: fh.readline(), b""):
                if b"cdc_" in line:
                    fh.seek(-len(line), 1)
                    newline = re.sub(b"cdc_.{22}", replacement, line)
                    fh.write(newline)
                    linect += 1
            return linect

    def is_already_patched(self) -> bool:
        """
        Check binary for patch

        :return: True if binary already patched
        """
        with io.open(self.executable_path, "rb") as fh:
            for line in iter(lambda: fh.readline(), b""):
                if b"cdc_" in line:
                    return False
            else:
                return True


class WebDriverDownloader:
    chromedriver_api_base: str = "https://chromedriver.storage.googleapis.com"
    chromedriver_get_latest: str = "LATEST_RELEASE"
    chromedriver_zip_name: str = "chromedriver_%s.zip"

    #TODO: add support for all platforms
    if CURRENT_PLATFORM == "win32" or CURRENT_PLATFORM == "cygwin":
        chromedriver_zip_name %= "win32"
    else:
        raise NotImplemented()

    def __init__(self, chrome_major_version: Optional[int] = None, webdriver_dir: str = MNU_WEBDRIVER_DIR_PATH):
        """
        :param chrome_major_version: Major version of Google Chrome, for which will be downloaded WebDriver.
                                     Chrome versioning: [major].[minor].[build].[patch], for example: 100.0.4896.20
        """
        self.target_version = self.get_latest_version(chrome_major_version)
        self.webdriver_dir = webdriver_dir

    def download(self) -> str:
        """
        Download zip archive with webdriver binary

        :return: Path where the archive was stored
        """
        url_path = f"{self.chromedriver_api_base}/{self.target_version}/{self.chromedriver_zip_name}"
        return urlretrieve(url_path)[0]

    def get_webdriver_executable(self, path_binary: bool = True) -> str:
        """
        Download webdriver zip archive, extract and optionally patch it. Patching make webdriver more undetectable for anti-bot systems

        :parameter path_binary: If True, binary will be patched after downloading
        :return: WebDriver executable path
        """

        zip_path = self.download()
        with zipfile.ZipFile(zip_path, 'r') as f_zip:
            f_zip.extractall(self.webdriver_dir)

        unzipped = glob(f"{os.path.join(self.webdriver_dir, MNU_WEBDRIVER_EXE_NAME)}*")
        if len(unzipped)<1:
            raise zipfile.BadZipFile(f"Unsuccessful extracting: {self.webdriver_dir}")

        unzipped_exe = unzipped[0]

        if path_binary:
            patcher = WebDriverPatcher(unzipped_exe)
            patcher.patch_binary()

        return unzipped_exe

    def get_latest_version(self, major_version: Optional[int] = None) -> str:
        """
        Get latest version(?by major version) of Chrome Driver

        :param major_version: If specified will be returned latest version for this major version
        :return: String, like: "100.0.40.2"
        """
        if major_version is None:
            major_version = self.try_find_chrome_version()

        get_latest = urljoin(self.chromedriver_api_base, self.chromedriver_get_latest if major_version is None else f"{self.chromedriver_get_latest}_{major_version}")
        return urlopen(get_latest).read().decode()

    def try_find_chrome_version(self) -> Optional[int]:
        #TODO
        """
        Try to find Chrome version and return major version
        
        :return: Major version of Chrome
        """

        return None


def download_webdriver(chrome_major_version: Optional[int] = None, patch_driver: bool = True) -> Tuple[str, str]:
    """
    Download WebDriver for specified major version or for latest version, and path binary if needed. See WebDriverPatcher for details

    :param chrome_major_version: If specified will be returned latest version for this major version
    :param patch_driver: If True, webdriver will be patched after downloading
    :returns: tuple(version, w_path),
        - str version - version of downloaded driver
        - str w_path - path to downloaded webdriver
    """
    downloader = WebDriverDownloader(chrome_major_version)

    w_path = downloader.get_webdriver_executable(patch_driver)
    return downloader.target_version, w_path


if __name__ == "__main__":
    download_webdriver()
