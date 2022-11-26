from typing import Sequence, Tuple
import os


module_path = os.path.dirname(os.path.abspath(__file__))

injections_files = \
    {
        "mnu_uploader_form": os.path.join(module_path, "mnu_uploader_form.html"),
        "mnu_uploader_script": os.path.join(module_path, "mnu_uploader_script.js"),
    }


def injections_exists() -> Sequence[Tuple[bool, str]]:
    return [(os.path.isfile(path), path) for key, path in injections_files.items()]


def replace_dom() -> str:
    """
    Injection for replacing DOM
    :return: js script
    """
    with open(injections_files["mnu_uploader_form"], 'r') as f:
        hmtl_body = f.read()
    return \
        f"""
var newHTML = `{hmtl_body}`;
document.open("text/html", "replace");document.write(newHTML);document.close();"""


def asset_upload_injection() -> str:
    """
    Injection for asset upload
    :return: js script
    """
    with open(injections_files["mnu_uploader_script"], 'r') as f:
        return f.read()


def open_new_tab_and_reload_it(url: str = "https://google.com", new_window: bool = True, reload_after: int = 5000):
    return f'let tab = window.open("{url}","{"_blank" if new_window else "_self"}"); setTimeout(function(){{tab.location.reload();}}, {reload_after});'
