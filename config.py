import os
import yaml
from abc import abstractmethod
from dataclasses import dataclass
from hashlib import md5
from typing import Any, Iterable, Sequence, Mapping
from secrets import token_bytes
from random import sample

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
new_line = "\n"


class ConfigInitException(Exception):
    def __init__(self, *args, error_message: Any = None):
        super(ConfigInitException, self).__init__(*args)
        self.error_message = error_message

    def __str__(self):
        return super().__str__() if self.error_message is None else f"[{self.error_message}]"


class ConfigFileNotFound(ConfigInitException, ValueError):
    ...


class IncorrectPropertyType(ConfigInitException, ValueError):
    ...


class PropertyRequired(ConfigInitException, ValueError):
    ...


class FileNamesConflict(ConfigInitException, ValueError):
    def __init__(self, file_name: str):
        super(FileNamesConflict, self).__init__(error_message=f"File [yellow]{file_name}[/] listed in several configs (it`s [red]conflict[/])")


class ExceptionsFoundedDuringInit(ConfigInitException):
    ...


class AuditorConfigException(ConfigInitException):
    """Signal parent class for mnu auditor"""


class AuditorConfigMismatchesFound(AuditorConfigException):
    ...


class AuditorConfigFilenamesConflict(AuditorConfigException):
    ...


#TODO: rewrite logic using typing
class ConfigClass:
    """
    Class for providing easy way for store and manipulating with configuration data

    For creating own config, you must only inherit from this class, and override methods like @classmethod:
     - config_file
     - config_methods
    """
    @dataclass
    class ConfAttr:
        name: str
        required: bool = False
        default: Any = None

    _instance = None

    _configs_dir = "configs"

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self, hide_errors: bool = False, disable_warnings: bool = False):
        self.hide_errors = hide_errors
        self.disable_warnings = disable_warnings
        self.captured_errors = [] # type: list[ConfigInitException]
        file_name = self.config_file_path()
        if not os.path.isfile(file_name):
            self.captured_errors.append(ConfigFileNotFound(f"[File not found [red]{self.config_file()}[/]]"))
        else:
            with open(file_name, 'r') as f:
                from_conf = yaml.safe_load(f)

            for attr_obj in self.config_attrs():
                attr = from_conf.get(attr_obj.name, attr_obj.default)

                if attr_obj.required and attr is None:
                    self.captured_errors.append(PropertyRequired(f"[Option [yellow]{attr_obj.name}[/] required but [red]not found[/]]"))
                elif attr_obj.default is not None and not isinstance(attr, type(attr_obj.default)):
                    self.captured_errors.append(IncorrectPropertyType(f"[Property {attr_obj.name} have [red]{type(attr)}[/] type but [green]{type(attr_obj.default)}[/] required]"))
                else:
                    setattr(self, attr_obj.name, attr)

        if not self.hide_errors and len(self.captured_errors)>0:
            raise ExceptionsFoundedDuringInit(*self.captured_errors)

    def __getattr__(self, item):
        if self.hide_errors and not self.disable_warnings:
            print(f"<{self.__class__.__name__}> attribute '{item}' error")

    def __str__(self):
        return f'<{self.__class__.__name__} {new_line.join((f"{new_line}{conf.name}={getattr(self, conf.name, None)}" for conf in self.config_attrs()))}>'

    def __repr__(self):
        return f'<{self.__class__.__name__} Conf={self.config_file()}>'

    @property
    def dict_like(self):
        """
        Convert config to a dict
        :return: Config from current object in dict-like form
        """
        return {attr.name: getattr(self, attr.name, attr.default) for attr in self.config_attrs()}

    @classmethod
    def configs_dir(cls) -> str:
        """
        :return: Configs base dir absolute path
        """
        return os.path.join(BASE_PATH, cls._configs_dir)

    @classmethod
    def config_file_path(cls) -> str:
        """
        :return: Config file absolute path
        """
        return os.path.join(cls.configs_dir(), cls.config_file())

    @classmethod
    def _save_config(cls, data: dict) -> None:
        """
        Saving the given data to a file
        :param data: Dict of data for saving
        :return: None
        """
        with open(cls.config_file_path(), 'w') as f:
            yaml.dump(data, f)

    def save(self) -> None:
        """
        Save current config object data
        :return: None
        """
        self._save_config(self.dict_like)

    @classmethod
    def _generate_empty_conf(cls) -> None:
        """
        Generate default config and save to file
        :return: None
        """
        dir_path = cls.configs_dir()
        if not os.path.isdir(dir_path):
            os.makedirs(dir_path)
        props_dict = {attr.name: attr.default for attr in cls.config_attrs()}
        cls._save_config(props_dict)

    @classmethod
    @abstractmethod
    def config_file(cls) -> str:
        """
        :return: Name of config file
        :rtype: str
        """
        ...

    @classmethod
    @abstractmethod
    def config_attrs(cls) -> Iterable[ConfAttr]:
        """
        :return: Iterable object, which contain ConfAttr instances
        :rtype: Iterable
        """
        a = cls.ConfAttr
        return (
            a("Name", required=False, default=None),
        )


class MetamaskConfig(ConfigClass):
    @classmethod
    def config_file(cls):
        return "metamask.conf"

    @classmethod
    def config_attrs(cls):
        pass_rand = "".join(
            sample(
                md5(token_bytes(16)).hexdigest(),
                k=8
            )
        )
        a = cls.ConfAttr
        return [
            a("secret_phase", required=True),
            a("temp_password", required=True, default=f"MNU_M3tam@skp@$${pass_rand}")
        ]


class CollectionConfig(ConfigClass):
    @classmethod
    def config_file(cls):
        return "opensea_collection.conf"

    @classmethod
    def config_attrs(cls):
        a = cls.ConfAttr
        return [
            a("collection_name", required=True),
            a("collection_dir_local_path", required=True),
            a("use_absolute_path", default=True),
            a("max_upload_time", default=60),
            a("single_asset_name", default=""),
            a("asset_external_link_base", default=""),
            a("collection_description", default=""),
        ]


class MNUServerConfig(ConfigClass):
    @classmethod
    def config_file(cls):
        return "server.conf"

    @classmethod
    def config_attrs(cls):
        a = cls.ConfAttr
        return [
            a("only_local_host", required=True, default=True),
            a("server_port", required=True, default=18040),
            a("use_default_ui", required=True, default=True),
            a("autorun_external_gui", default=True),
            a("external_gui_path", default="gui/mnu_example_gui_client/main.py"),
        ]


class MNUSecrets(ConfigClass):
    """
    Provide keys for very simple authentication
    """
    @classmethod
    def config_file(cls):
        return "mnu_secrets.conf"

    @classmethod
    def config_attrs(cls):
        a = cls.ConfAttr
        return [
            a("worker_secret", required=True, default=md5(b"MNUWorkerSecret").hexdigest()),
            a("ui_secret", required=True, default=md5(b"MNUUISecret").hexdigest()),
        ]


class MNUClientConfig(ConfigClass):
    """
    Provide keys for very simple authentication
    """
    @classmethod
    def config_file(cls):
        return "mnu_client.conf"

    @classmethod
    def config_attrs(cls):
        a = cls.ConfAttr
        return [
            a("mnu_ui_secret", required=True, default=md5(b"MNUUISecret").hexdigest()),
            a("server_port", required=True, default=18040),
            a("server_addr", required=True, default="127.0.0.1"),
            a("auto_connect", default=False),
        ]


def search_mismatches() -> Mapping[str, list]:
    """
    Check correctness of configs

    :return: Return errors grouped by config class
    """
    config_exceptions = {}
    for sub_cls in ConfigClass.__subclasses__():
        current_config_name = sub_cls.__name__
        if current_config_name not in config_exceptions:
            config_exceptions[current_config_name] = []
        try:
            config_exceptions[current_config_name] = sub_cls(hide_errors=True).captured_errors
        except ConfigInitException as e:
            config_exceptions[current_config_name].append(e)
    return config_exceptions


def check_filenames_conflict() -> Sequence[str]:
    """
    Checking for config filenames conflict

    :return: Conflicting filenames
    """
    from collections import Counter
    return [config_file for config_file, count in Counter(sub_cls.config_file() for sub_cls in ConfigClass.__subclasses__()).items() if count>1]


def gen_empty_configs() -> Sequence[str]:
    """
    Create empty configs

    :return: Error or success messages
    """
    messages = []
    for sub_cls in ConfigClass.__subclasses__():
        """Generating"""
        sub_cls._generate_empty_conf()
        messages.append(f"[green]{sub_cls.__name__}`s[/] config was successfully generated [[yellow]{sub_cls.config_file()}[/]]")
    return messages

if __name__=="__main__":
    help_message = \
    """
        python config.py [OPTION]
        
        -p      (default)parse configs for searching mismatches
        -c      check for filenames conflict
        -g      generate empty configs
    """
    import sys

    from rich.console import Console
    from rich.prompt import Confirm
    from rich.panel import Panel
    from rich.table import Table
    from rich.align import Align
    from rich import box

    console = Console()
    args = sys.argv[1:]
    if '-p' in args or len(args)==0:
        captured_exceptions = search_mismatches() # type: Mapping[str, list]
        if sum(len(ce) for ce in captured_exceptions.values()) < 1:
            console.print("[green]All configs files are correct[/]", justify="center")
        else:
            output_table = Table.grid(padding=1)
            output_table.add_column(no_wrap=True)
            output_table.add_column(no_wrap=True)

            for config_name, exceptions in captured_exceptions.items():
                if len(exceptions)<1:
                    continue
                except_list = Table.grid(padding=0)
                except_list.add_column(no_wrap=True)
                for c_e in exceptions:
                    except_list.add_row(str(c_e))

                output_table.add_row(config_name, except_list)

            console.print(
                Panel.fit(
                    output_table,
                    box=box.ROUNDED,
                    padding=(1, 2),
                    title=f"[b red]Founded mismatches",
                    border_style="bright_blue"
                ),
                justify="center"
            )
    elif '-c' in args:
        duplicated_filenames = check_filenames_conflict()

        if len(duplicated_filenames) < 1:
            console.print("[green]All configs use separate files[/]", justify="center")
        else:
            output_table = Table.grid(padding=1)
            output_table.add_column(no_wrap=True, justify="center", style="yellow")

            for duplicate in duplicated_filenames:
                output_table.add_row(duplicate)

            console.print(
                Panel.fit(
                    Align(output_table, align="center"),
                    box=box.ROUNDED,
                    padding=(1, 2),
                    title=f"[b red]This files uses in several configs. \nFix it",
                    border_style="bright_blue",
                ),
                justify="center"
            )

    elif '-g' in args:
        if Confirm.ask("You want to generate new [red]empty[/] configurations?", default=True):
            returned_messages = gen_empty_configs()
            console.print("\n"+"\n".join(returned_messages))

    else:
        console.print(f"\n{help_message.lstrip()}")
