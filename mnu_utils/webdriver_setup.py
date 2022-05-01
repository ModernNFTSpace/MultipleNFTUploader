import random
import string
import re
import io


class WebDriverPatcher:

    def __init__(self, web_driver_path="chromedriver.exe"):
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


if __name__ == "__main__":
    patcher = WebDriverPatcher()
    patcher.patch_binary()
