from dataclasses import dataclass, asdict
from typing import Optional, Callable, Type, Literal

import json

from mnu_utils import AverageTime

_type_of_primitive_holder = "__primitive_type"


@dataclass
class MNUploaderAPIPrimitive:
    """
    Basic primitive which can be transporting via API
    """

    def __post_init__(self):
        ...

    def reinit_from_dict(self, data: dict) -> None:
        """
        Reinitialize attributes from given dict
        Affecting only existing attributes, so it save to pass not verified dict

        :param data: MNUploaderAPIPrimitive.json_encoded()
        """

        base_class  = self._get_base_class()
        annotations = getattr(self, "__annotations__", {})
        for key, value in data.items():
            if key in annotations and hasattr(self, key):
                attr = getattr(self, key)
                if isinstance(attr, base_class):
                    attr.reinit_from_dict(value) # at this stage value is dict
                else:
                    setattr(self, key, value)

    @classmethod
    def _get_base_class(cls) -> Type:
        """Literally return MNUploaderAPIPrimitive"""
        return cls.__mro__[-2]

    def as_dict(self) -> dict:
        d = asdict(self)
        d[_type_of_primitive_holder] = self.__class__.__name__ # Class representing type
        return d

    def json_encoded(self) -> str:
        return json.dumps(self.as_dict())


@dataclass
class ServerInfo(MNUploaderAPIPrimitive):
    """Information about app and server"""

    #Server info
    app_name: str = ""
    app_version: str = ""
    server_version: str = ""
    server_status: Literal["ready", "shutdown"] = "ready"


@dataclass
class AssetsData(MNUploaderAPIPrimitive):
    """Information about available assets"""

    #Assets data
    assets_in_collection: int = 0
    assets_uploaded: int = 0

    collection_name: str = "None"

    last_uploaded_asset: str = ""



@dataclass
class DriversData(MNUploaderAPIPrimitive):
    """Information about drivers working on uploading of assets"""

    #Drivers data
    active_drivers: int = 0
    maximum_drivers: int = 4

    uploading_is_active: bool = False


@dataclass
class UIStateHolder(MNUploaderAPIPrimitive):
    """Class containing the current state of the server to represent it in the UI"""

    #Assets data
    assets_data: AssetsData = AssetsData()

    #Drivers data
    drivers_data: DriversData = DriversData()

    #Server data
    server_info: ServerInfo = ServerInfo()
    active_ui_clients: int = 0

    #Timing
    time_spent_on_last_upload: float = 0.0
    time_spent_on_last_driver_init: float = 0.0
    average_t_s_o_l_upload: float = 0.0
    average_t_s_o_l_driver_init: float = 0.0

    def __post_init__(self) -> None:
        super(UIStateHolder, self).__post_init__()
        self.average_upload_time = AverageTime()
        self.average_driver_init_time = AverageTime()
        self.state_change_callback = None

        return
        #deprecated
        def call_callback(trigger_func: Optional[Callable] = None):
            def _inner(*args, **kwargs):
                if callable(trigger_func):
                    trigger_func(*args, **kwargs)
                if callable(self.state_change_callback):
                    self.state_change_callback()
            return _inner

        for trigger in dir(self):
            if "trigger_" in trigger:
                setattr(self, trigger, call_callback(getattr(self, trigger)))

    def set_state_change_callback(self, callback: Callable):
        self.state_change_callback = callback

    def setup_values(self,
                     assets_in_collection: int,
                     assets_uploaded: int,
                     collection_name: str,

                     maximum_drivers: int,

                     app_name: str,
                     app_version: str,
                     server_version: str
                     ) -> None:
        """Called for setting default or saved from last session values"""
        self.assets_data.assets_in_collection = assets_in_collection
        self.assets_data.assets_uploaded      = assets_uploaded
        self.assets_data.collection_name      = collection_name

        self.drivers_data.maximum_drivers     = maximum_drivers

        self.server_info.app_name             = app_name
        self.server_info.app_version          = app_version
        self.server_info.server_version       = server_version

    def trigger_asset_upload(self, time_spent_on_it: float) -> None:
        """
        Called when one asset was uploaded

        :param time_spent_on_it: Time spent on uploading asset
        """
        self.average_upload_time.add(time_spent_on_it)
        self.time_spent_on_last_upload = time_spent_on_it
        self.average_t_s_o_l_upload = self.average_upload_time.average
        self.assets_data.assets_uploaded += 1

    def trigger_driver_init(self, time_spent_on_it: float) -> None:
        """
        Called when one driver was initialized

        :param time_spent_on_it: Time spent on driver init
        """
        self.average_driver_init_time.add(time_spent_on_it)
        self.time_spent_on_last_driver_init = time_spent_on_it
        self.average_t_s_o_l_driver_init = self.average_driver_init_time.average

    def trigger_client_connected(self):
        """
        Called when new UI client registered
        """
        self.active_ui_clients += 1

    def trigger_client_disconnected(self):
        """
        Called when new UI client unregistered
        #TODO: currently not using
        """
        self.active_ui_clients -= 1

    def trigger_set_drivers_count(self, count):
        self.drivers_data.active_drivers = count


def get_MNUAPIPrimitive_by_name(name: str) -> Optional[Type[MNUploaderAPIPrimitive]]:
    for subclass in MNUploaderAPIPrimitive.__subclasses__():
        if subclass.__name__ == name:
            return subclass
    return None


def construct_MNUAPIPrimitive_from_dict(data: dict) -> Optional[MNUploaderAPIPrimitive]:
    primitive_type_name = data.get(_type_of_primitive_holder, None)
    if primitive_type_name is not None:
        primitive_type = get_MNUAPIPrimitive_by_name(primitive_type_name)
        if primitive_type is not None:
            new_api_primitive = primitive_type()
            new_api_primitive.reinit_from_dict(data)
            return new_api_primitive

    return None


def construct_MNUAPIPrimitive_from_json(data: str) -> Optional[MNUploaderAPIPrimitive]:
    try:
        return construct_MNUAPIPrimitive_from_dict(json.loads(data))
    except json.JSONDecodeError:
        return None


if __name__ == "__main__":
    from data_holders import console
    from rich.console import Group
    from rich.table import Table
    from rich.highlighter import ReprHighlighter
    from rich.panel import Panel
    from rich.tree import Tree
    from rich.json import JSON
    from rich.rule import Rule

    import os

    console.print(Rule(os.path.basename(__file__)))

    root = Tree("Module", highlight=True)

    hierarchy = root.add("[red]Hierarchy", guide_style="red")
    base_class = MNUploaderAPIPrimitive._get_base_class()
    b_c_node = hierarchy.add(base_class.__name__, style="green")
    for sub_cls in base_class.__subclasses__():
        b_c_node.add(Group(
            sub_cls.__name__,
            Panel.fit(sub_cls.__doc__, style="white", title="[red]↓", title_align="left")
        ))

    examples = root.add("[blue]Example of usage", guide_style="blue")

    a_instance = UIStateHolder()
    a_as_json  = a_instance.json_encoded()
    b_instance = construct_MNUAPIPrimitive_from_json(a_as_json)

    highlight_obj = lambda obj: ReprHighlighter()(str(obj).replace("(", "(\n").replace(")", "\n)").replace(", ", ",\n"))

    stand_0 = Table.grid()
    stand_0.add_column()
    stand_0.add_column()
    stand_0.add_column()
    stand_0.add_row(
        Panel.fit(
            highlight_obj(a_instance),
            title="[green]Original object",
            border_style="bright_cyan"
        ),
        Panel.fit(
            JSON(a_as_json),
            title="[green]JSON-encoded object",
            border_style="bright_cyan"
        ),
        Panel.fit(
            highlight_obj(b_instance),
            title="[green]Object reconstructed from JSON",
            border_style="bright_cyan"
        )
    )

    examples.add(stand_0)

    console.print(root)
