from queue import Queue, Empty as QueueEmptyException
from threading import Thread, Event
from typing import Type, Optional

import os
import time
import yaml

from data_holders import getAssetDataHolderClass, RecaptchaTokenHolder, UploadDataHolder, SingleAssetData, UploadResponseHolder
from events import EventHolder, ServerEvent
from config import CollectionConfig

import asset_data_holder  # imported for registering subclasses


class MNUAssetsHandlerException(Exception):
    """Base exception for assets_handler module"""


class CollectionDirNotFound(MNUAssetsHandlerException):
    """Assets handler can`t find the collection dir"""


class ManifestNotFound(MNUAssetsHandlerException):
    """Assets handler can`t find the manifest file"""


class ManifestFileCorrupted(MNUAssetsHandlerException):
    """Manifest file have unknown format or corrupted"""


class DataKeeperFileCorrupted(MNUAssetsHandlerException):
    """Data keeper file have unknown format or corrupted"""


class AssetsHandler:
    """
    Class provide mechanism for loading assets from the disk and their further uploading
    """

    AssetHolderClass: Type[SingleAssetData] = getAssetDataHolderClass() # See <asset_data_holder> module for details. This class will be used to represent assets data
    workers_emulate_data: str = "JTQxJTcyJTY1JTVGJTc1JTVGJTczJTc1JTcyJTY1JTVGJTY5JTc0JTVGJTY5JTczJTVGJTczJTYxJTY2JTY1JTVGJTVGJTYyJTc1JTc0JTVGJTc0JTY4JTYxJTZFJTZCJTcz" # ?)

    collection_manifest: str = "0manifest.yaml" # file which must contain information about assets. Each element of manifest will be represent using AssetHolderClass
    collection_data_keeper: str = "0data_keeper.yaml" # file which will be contain data of uploaded assets(blockchain data). See data_holders.UploadResponseHolder.AssetDataFromResponse for details about data

    def __init__(self, assets_uploader_bus: Queue, output_bus: Queue, collection_config: CollectionConfig = CollectionConfig()):

        if not os.path.isdir(collection_config.collection_dir_local_path):
            raise CollectionDirNotFound(collection_config.collection_dir_local_path)

        self.collection_config = collection_config
        self.collection_dir = collection_config.collection_dir_local_path # type: str

        self.collection_manifest = os.path.join(self.collection_dir, self.collection_manifest)
        self.collection_data_keeper = os.path.join(self.collection_dir, self.collection_data_keeper)

        self.manifest_data = {} # type: dict # data from manifest. See manifest_structure.puml for example
        if not os.path.isfile(self.collection_manifest):
            raise ManifestNotFound(self.collection_manifest)
        else:
            with open(self.collection_manifest, "r") as f:
                try:
                    manifest = yaml.safe_load(f) # type: dict
                except yaml.YAMLError:
                    raise ManifestFileCorrupted(f"Error while decoding {self.collection_manifest}")

                if not isinstance(manifest, dict) or "assets_data" not in manifest:
                    raise ManifestFileCorrupted(type(manifest), manifest.keys())
                self.manifest_data = manifest

        self.uploaded_assets_ids = [] # type: list # contain ids of assets which already uploaded

        if os.path.isfile(self.collection_data_keeper):
            #TODO: read only strings with ids(collection_data_keeper is a dict)
            with open(self.collection_data_keeper, "r") as f:
                try:
                    data_keeper = yaml.safe_load(f) # type: dict
                except yaml.YAMLError:
                    raise DataKeeperFileCorrupted(f"Error while decoding {self.collection_data_keeper}")

                if not isinstance(data_keeper, dict):
                    raise DataKeeperFileCorrupted(type(data_keeper))
                self.uploaded_assets_ids = list(data_keeper.keys())

        self.assets_uploader_bus = assets_uploader_bus
        self.output_bus          = output_bus # bus for communication with server
        self.incoming_token_bus  = Queue() # type: Queue # bus with valid tokens from recaptcha workers

        self.stop_event = Event()
        self.assets_handler_thread = Thread(name="AssetsHandlerThread", target=self.start, daemon=True)
        self.assets_handler_thread.start()

    def put_token(self, new_token: RecaptchaTokenHolder):
        self.incoming_token_bus.put(new_token)

    def asset_uploading_failed(self, asset_id: int) -> bool:
        """
        Called when asset uploading failed

        :param asset_id: Id of asset which not uploaded
        :return: True if at least one asset was affected
        """
        for asset_name, asset_data in self.manifest_data["assets_data"].items():
            if asset_data["id"] == asset_id:
                self.manifest_data["assets_data"][asset_name]["upload_in_progress"] = False
                return True
        return False

    def asset_uploaded(self, response_data: UploadResponseHolder) -> bool:
        """
        Mark asset as uploaded and save response data

        :param response_data: Data received after uploading
        :return: True if upload was successful, False otherwise
        """
        asset_id = response_data.asset_id
        if response_data.successes:
            self.uploaded_assets_ids.append(asset_id)
            data_for_save = {asset_id: response_data.dict_for_save}
            with open(self.collection_data_keeper, 'a+') as f:
                yaml.dump(data_for_save, f)
            return True
        else:
            self.asset_uploading_failed(asset_id)
            return False

    def _get_image_data_for_uploading(self) -> Optional[dict]:
        """
        Searching for not uploaded asset and returning it

        :return: Asset data for upload
        """
        #TODO: use iterator for finding not uploaded asset
        for asset_name, data in self.manifest_data["assets_data"].items():
            if not data.get("upload_in_progress", False) and data["id"] not in self.uploaded_assets_ids:
                self.manifest_data["assets_data"][asset_name]["upload_in_progress"] = True
                return data
        return None

    @property
    def uploaded_assets_count(self):
        return len(self.uploaded_assets_ids)

    @property
    def assets_count(self):
        return len(self.manifest_data["assets_data"])

    def start(self, emulate_recaptcha_workers=True) -> None:
        if emulate_recaptcha_workers:
            threshold = 0.1
            recaptcha_token = RecaptchaTokenHolder(self.workers_emulate_data, can_be_expire=False)
            while not self.stop_event.is_set():
                if self.assets_uploader_bus.qsize() < 20:
                    asset_data = self._get_image_data_for_uploading()
                    if asset_data is not None:
                        self.assets_uploader_bus.put(
                            EventHolder(
                                ServerEvent.INCOMING_TOKEN,
                                UploadDataHolder(
                                    recaptcha_token,
                                    self.AssetHolderClass(
                                        asset_data,
                                        collection_info=self.collection_config.dict_like
                                    )
                                )
                            )
                        )
                    else:
                        self.output_bus.put(EventHolder(ServerEvent.AH_ASSETS_ARE_OVER))
                        break
                else:
                    time.sleep(0.5)
                    continue
                time.sleep(threshold)
        else:
            while not self.stop_event.is_set():
                try:
                    new_token = self.incoming_token_bus.get(timeout=2)
                except QueueEmptyException:
                    ...

                if isinstance(new_token, RecaptchaTokenHolder):
                    #TODO
                    #Now not actual
                    ...

    def stop(self) -> None:
        self.stop_event.set()
        self.assets_handler_thread.join()


if __name__ == "__main__":
    #exit()
    output_bus = Queue()
    assets_bus = Queue()

    c_config = CollectionConfig()
    c_config.asset_external_link_base = "https://test.com"
    c_config.collection_description = 'Test Collection description'
    c_config.collection_dir_local_path = '../dev/22.04.01_15-50-55'
    c_config.collection_name = 'Test Collection' # in production must be real collection slug
    c_config.max_upload_time = 100
    c_config.single_asset_name = 'Test asset'

    a_h = AssetsHandler(assets_bus, output_bus)
    print("started")

    a_h.stop()

