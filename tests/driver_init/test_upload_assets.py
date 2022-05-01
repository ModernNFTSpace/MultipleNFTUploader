import pytest
import shutil

from random import randint
from typing import Sequence

from dummy_png_generator import generate_dummy_png
from data_holders import UploadResponseHolder
from driver_init import check_webdriver_exists, driver_upload_asset


@pytest.fixture(scope="session")
def dummy_files_dir(tmpdir_factory):
    fn = tmpdir_factory.mktemp("test_dummies")
    yield fn
    shutil.rmtree(str(fn), ignore_errors=True)


def _generate_params(count):
    sizes = ((500, "kb"), (2, "mb"), (1, "mb"))

    def _infinite_gen():
        ind = 0
        while True:
            yield sizes[ind]
            ind = (ind+1) % len(sizes)

    return (
        {
            "name": "MNU Test",
            "size": size,
            "id": i
        }
        for size, i in zip(_infinite_gen(), range(count)))


@pytest.mark.incremental
class TestUploading:
    dummies_for_upload = 2
    max_waiting_time = 20

    _uploads_failed = 0
    upload_results = [] # type: Sequence[UploadResponseHolder]

    driver = None

    @pytest.fixture(params=_generate_params(dummies_for_upload))
    def asset_data_dict(self, request, dummy_files_dir):
        collection_slug = pytest.metamask_conf["COLLECTION_SLUG"]
        dummy_path = generate_dummy_png(request.param['size'], dest_dir=str(dummy_files_dir))

        return dummy_path, request.param['id'], {
            "collection": collection_slug,
            "name": f"{request.param['name']} | {request.param['size'][0]} {request.param['size'][1]}",
            "description": "Testing MNU on dummy files",
            "externalLink": None,
            "properties": [
                {"name": "Size", "value": request.param['size'][0]},
                {"name": "Size units", "value": request.param['size'][1]}
            ],
            "levels": [
                {"name": "Test level", "value": randint(0, 100), "max": 100}
            ],
            "stats": [
                {"name": "Test stat", "value": randint(0, 100), "max": 100}
            ],
            "unlockableContent": "Uploaded via MNU",
            "isNsfw": False,
            "maxSupply": 1,
            "chain": 'MATIC'
        }

    def test_check_webdriver_exists(self):
        assert check_webdriver_exists()

    def test_driver_init(self, request):
        self.__class__.driver = request.getfixturevalue("driver")

    @pytest.mark.xfail
    def test_upload(self, asset_data_dict):
        dummy_path, asset_id, asset_dict = asset_data_dict
        try:
            result = driver_upload_asset(
                asset_data=asset_dict,
                asset_id=asset_id,
                asset_abs_file_path=dummy_path,
                driver=self.driver,
                wait_in_sec=self.max_waiting_time
            )
            self.__class__.upload_results.append(result)
            assert result.successes
        except Exception as e:
            #Upload error
            self.__class__._uploads_failed += 1
            raise e

    def test_uploading_success(self):
        """
        Test passed if at least one upload was completed without errors
        """
        assert self._uploads_failed < self.dummies_for_upload

    def teardown_class(self):
        for res in self.upload_results:
            print(f"\nAsset(id={res.asset_id}) {'' if res.successes else 'NOT '}UPLOADED, raw response:\n{res.raw_response}")
