from collections.abc import MutableMapping
from config import CollectionConfig

from dataclasses import dataclass, asdict
from typing import Optional, Type, Generator
from time import time

from secrets import token_hex

import os
import re
import json

from rich.console import Console

console = Console()


url_pattern = re.compile(r"^(?:http(s)?:\/\/)[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:\/?#[\]@!\$&'\(\)\*\+,;=.]+$")


def check_callback_url(url_callback: str):
    return url_pattern.fullmatch(url_callback) is not None


class SessionsHolder:
    """
    Containing active clients sessions, with linked data

    !Sessions have not duration time. Ending only when server restarting
    #TODO: Add duration functionality
    """
    @dataclass
    class Session:
        session_key: str
        callback_url: Optional[str]
        client_name: Optional[str] = "UnnamedUIClient"

        def __post_init__(self):
            if not check_callback_url(self.callback_url):
                self.callback_url = None

        def unsubscribe(self):
            self.callback_url = None

        @staticmethod
        def generate_key() -> str:
            return token_hex(16)

        @property
        def have_callback(self):
            return self.callback_url is not None

    def __init__(self, mnu_ui_secret: str):
        self.mnu_ui_secret = mnu_ui_secret # type: str # See config.MNUSecrets for details
        self.sessions = []

    def _gen_new_session_key(self):
        while True:
            s_key = self.Session.generate_key()
            if self.get_session(s_key) is None:
                return s_key

    def get_session(self, session_key) -> Optional[Session]:
        """

        :param session_key: Key given during session opening
        :return: Session if exist
        """
        for session in self.sessions:
            if session.session_key == session_key:
                return session
        return None

    def open_session(self, secret_from_client: str, callback_url: Optional[str], client_name: Optional[str]) -> Optional[str]:
        """
        Open new client session if secret is valid

        :param secret_from_client: Secret from UI client. Must be identical to self.mnu_ui_secret
        :param callback_url: URL which will used for callback request from server. Can be None if don`t needed
        :param client_name: Name of the UI client
        :return: True if session opened, False otherwise
        """
        if secret_from_client == self.mnu_ui_secret:
            new_session_key = self._gen_new_session_key()
            self.sessions.append(self.Session(
                new_session_key,
                callback_url=callback_url,
                client_name=client_name
            ))
            return new_session_key
        return None

    def get_callback_subscribers(self) -> Generator[Session, None, None]:
        """
        Return all clients which subscribe on callbacks
        :return: Generator[Session]
        """
        for session in self.sessions:
            if session.have_callback:
                yield session


@dataclass
class RecaptchaTokenHolder:
    token: str
    timestamp: int = 0 # Unix Timestamp of time when recaptcha was passed
    can_be_expire: bool = True
    live_time = 60*2 - 5

    @property
    def expired(self) -> bool:
        return self.timestamp+self.live_time >= time() if self.can_be_expire else False


DEFAULT_COLLECTION_INFO = CollectionConfig().dict_like


class SingleAssetData(MutableMapping):
    """
    Each object of this class is a dict, like:
        {
          "id": INT,
          "assetPath": ABSOLUTE_PATH_STR,
          "collection": STR,
          "description": NULL or STR,
          "externalLink": NULL or STR,
          "maxSupply": STR(INT),
          "name": ASSET_NAME_STR,
          "chain": BLOCKCHAIN_NAME_STR,
          "unlockableContent": NULL or STR,
          "isNsfw": BOOL,
          "properties": [{"name":STR,"value":STR}],
          "levels": [{"name":STR,"value":INT,"max":INT}],
          "stats": [{"name":STR,"value":INT,"max":INT}]
        }
    """
    necessary_keys = ["collection", "name", "description", "externalLink", "properties", "levels", "stats",
                      "unlockableContent", "isNsfw", "maxSupply", "chain"]

    def __init__(self, dict_with_data: dict, collection_info: dict = DEFAULT_COLLECTION_INFO) -> None:
        """
        dict_with_data -    must be be one dict from COLLECTION_DATA,
                            namely:
                                dict, like: {"id": INT, "attrs": [STR], "path": STR_ABSOLUTE_PATH, "file_name": STR}
        """
        self.use_absolute_path = collection_info.get("use_absolute_path", True)
        self.origin      = dict_with_data
        self.origin_info = collection_info
        self.store = {
            "id": str(self.id),
            "assetPath": self.path,
            "collection": self.collection_name,
            "name": self.name,
            "externalLink": self.external_link,
            "description": self.description,
            "properties": self.properties,
            "levels": self.levels,
            "stats": self.stats,
            "unlockableContent": self.unlockable_content,
            "isNsfw": self.nsfw_content,
            "maxSupply": str(self.supply),
            "chain": self.blockchain
        }

    def as_upload_data_dict(self) -> dict:
        """
        Return dict which contain full data about asset
        :return: dict with data
        """
        return {key: self.store.get(key, None) for key in self.necessary_keys}

    @property
    def single_asset_name(self) -> str:
        return self.origin_info["single_asset_name"]

    @property
    def collection_name(self) -> str:
        return self.origin_info["collection_name"]

    @property
    def asset_external_link_base(self) -> str:
        return self.origin_info["asset_external_link_base"]

    @property
    def collection_description(self) -> str:
        return self.origin_info["collection_description"]

    @property
    def id(self) -> int:
        return self.origin["id"]

    @property
    def path(self) -> str:
        """
        Return abs path to the asset file
        :return: Absolute path
        """
        if self.use_absolute_path and self.origin["path"]:
            return self.origin["path"]
        else:
            assert self.origin_info["collection_dir_local_path"]
            assert self.origin["file_name"]
            return os.path.abspath(os.path.join(self.origin_info["collection_dir_local_path"], self.origin["file_name"]))

    @property
    def name(self) -> str:
        return f'{self.single_asset_name}#{self.origin["id"]}'

    @property
    def external_link(self) -> Optional[str]:
        return None

    @property
    def description(self) -> Optional[str]:
        return self.collection_description if self.collection_description else None

    @property
    def properties(self) -> list:
        return []

    @property
    def levels(self) -> list:
        return []

    @property
    def stats(self) -> list:
        return []

    @property
    def unlockable_content(self) -> Optional[str]:
        return None

    @property
    def nsfw_content(self) -> bool:
        return False

    @property
    def supply(self) -> int:
        return 1

    @property
    def blockchain(self) -> str:
        return 'MATIC'

    def __str__(self):
        return f'<{self.__class__.__name__} ID={self.id}>'

    def __repr__(self):
        return self.__str__()

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = value

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)


@dataclass
class UploadDataHolder:
    _token: RecaptchaTokenHolder
    _asset: SingleAssetData

    @property
    def file_path(self) -> str:
        return self._asset["assetPath"]

    @property
    def asset_id(self) -> int:
        return self._asset.id

    @property
    def asset_data_for_upload(self) -> dict:
        asset_data = self._asset.as_upload_data_dict()
        asset_data.update({"recaptchaToken": self.token})
        return asset_data

    @property
    def asset_data_json(self) -> str:
        return json.dumps(self.asset_data_for_upload)

    @property
    def token_expired(self) -> bool:
        return self._token.expired

    @property
    def token(self) -> str:
        """
        :return: Recaptcha token
        """
        return self._token.token


class UploadResponseHolder:
    """
    Container for response received after uploading asset

    Also checking correctness of the response

    Correct request will return:
        on successes:
            {"data":{"assets":{"create":{"tokenId":STR,"assetContract":{"address":STR,"chain":STR,"id":STR},"id":STR}}},"status":200 or INT}
        on errors:
            {"errors":[{"message":STR,"locations":[...]}], ..., "status":200 or INT}


    """
    @dataclass
    class AssetDataFromResponse:
        asset_id: int
        token_id: str
        contract_address: str
        contract_chain: str # Blockchain name in uppercase
        contract_type: str # Base64 encoded str(AssetContractType:INT)
        asset_type: str # Base64 encoded str(AssetType:INT)

    def __init__(self, raw_response: str, start_of_upload_time: float, asset_id: int):
        self.time_spent_on_upload = time()-start_of_upload_time # type: float
        self.raw_response = raw_response
        self._asset_id = asset_id # type: int
        self.store = {} # type: dict # contain json decoded response
        self.asset = None # type: Optional[UploadResponseHolder.AssetDataFromResponse]
        self.invalid_request = False # type: bool # True if error was occurred while making request to API
        self.successful_response = False # type: bool # True if response is correct, contain data about uploaded asset and API return no errors
        try:
            self.store = json.loads(raw_response) # type: dict
        except json.JSONDecodeError:
            self.invalid_request = True
        else:
            if self.store["status"] != 200:
                self.invalid_request = True
            elif self.store.get("errors", None) is None:
                self.successful_response = True
                create_data    = self.store.get("data", {}).get("assets", {}).get("create", {})
                asset_contract = create_data.get("assetContract", {})
                self.asset = self.AssetDataFromResponse(
                    asset_id=self.asset_id,
                    token_id=create_data.get("tokenId", None),
                    contract_address=asset_contract.get("address", None),
                    contract_chain=asset_contract.get("chain", None),
                    contract_type=asset_contract.get("id", None),
                    asset_type=create_data.get("id", None)
                )

    def __str__(self):
        return f"<{self.__class__.__name__} successes={self.successes} asset_id={self.asset_id}>"

    def __repr__(self):
        return self.__str__()

    @property
    def successes(self) -> bool:
        """
        :return: True if request and response was successes
        """
        return not self.invalid_request and self.successful_response

    @property
    def asset_id(self):
        return self._asset_id

    @property
    def dict_for_save(self):
        """
        At first you must verify `successes` of response. Return dict for storing in data_keeper file. See documentation.
        :return: dict of self.asset values
        """
        return asdict(self.asset)


def getAssetDataHolderClass() -> Type[SingleAssetData]:
    """
    Return class which will be used to represent the asset data
    :return: Last inheritor of SingleAssetData
    """
    return SingleAssetData.__subclasses__()[-1]


if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    from os import path

    import asset_data_holder  # imported for registering subclasses

    module_description = Table.grid(padding=1)
    module_description.add_column(no_wrap=True)
    module_description.add_row("This module provide classes for storing and represent of data used during the upload")
    module_description.add_row()
    module_description.add_row("Classes:")

    classes_description = Table.grid()
    classes_description.add_column(style="green")
    classes_description.add_column(style="yellow")
    classes_description.add_row("RecaptchaTokenHolder ", "Contain Recaptcha Token")
    classes_description.add_row("SingleAssetData", "Inherit from this class for represent data of your assets. MNU will use last inheritor")
    classes_description.add_row("UploadDataHolder", "Wrapper for [green]RecaptchaTokenHolder[/] and [green]SingleAssetData")

    module_description.add_row(classes_description)

    AssetDataClass = getAssetDataHolderClass()
    module_description.add_row()
    module_description.add_row(f"[green]{AssetDataClass}[/] [yellow]will be used as an Asset Data Holder[/]")

    console = Console()
    console.print(
        Panel.fit(
            module_description,
            box=box.ROUNDED,
            padding=(1, 2),
            title=f"[b red]{path.basename(__file__)}",
            border_style="bright_blue"
        ),
        justify="center"
    )
