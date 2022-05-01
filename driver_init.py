from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver as WebDriverParentClass
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, TimeoutException

from random import randint

from threading import Lock
from queue import Queue

from rich import print

import time
import json
import js_injections

from glob import glob
from typing import Union

from config import CollectionConfig, MetamaskConfig
from data_holders import UploadResponseHolder
from events import EventHolder, ServerEvent
from mnu_utils import abs_path_from_base_dir_relative, MNU_WEBDRIVER_ABS_PATH, MNU_WEBDRIVER_ABS_PATH_PATTERN


class MNUDriverInitError(Exception):
    ...


class UnexpectedResult(MNUDriverInitError):
    ...


class LaunchLimitExceeded(MNUDriverInitError):
    ...


SECRET = MetamaskConfig().secret_phase
PASSWORD = MetamaskConfig().temp_password

EXTENSION_PATH   = abs_path_from_base_dir_relative('metamask/10.10.2_0.crx')


def check_webdriver_exists(webdriver_path: str = MNU_WEBDRIVER_ABS_PATH_PATTERN) -> bool:
    return len(glob(webdriver_path))>0


def driver_init(secret_phases=SECRET, temp_password=PASSWORD, auth_lock: Lock = Lock(), hide_warnings: bool = False, webdriver_path: str = MNU_WEBDRIVER_ABS_PATH) -> WebDriverParentClass:
    """
    Configuring driver for uploading
    #TODO: Refactoring
    """

    opt = webdriver.ChromeOptions()

    # Disabled due to small impact and increasing loading time
    #
    #opt.add_argument(f"--user-data-dir={PROFILES_PATH}")
    #opt.add_argument(f"--profile-directory={SELECTED_PROFILE}")

    # Disabled for passing Cloudflare protection
    # CF detecting mismatch with real user agent
    #
    #opt.add_argument(f'user-agent={USER_AGENT["google chrome"]}')

    opt.add_argument('--disable-blink-features=AutomationControlled')
    opt.add_argument(f"window-size={randint(1100, 1900)},{randint(700, 1000)}")
    opt.add_argument("--mute-audio")
    opt.add_extension(EXTENSION_PATH)
    opt.add_experimental_option('excludeSwitches', ['enable-logging', "enable-automation"])
    opt.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=Service(webdriver_path), options=opt)
    ####
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    #driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.53 Safari/537.36'})
    ####

    def wait_for_element(by, data, sec=2, cond=EC.presence_of_element_located, web_driver=driver, poll_frequency=0.5):
        return WebDriverWait(web_driver, sec, poll_frequency=poll_frequency).until(cond((by, data)))

    def wait_for_elements(by, data, sec=2, cond=EC.presence_of_all_elements_located, web_driver=driver, poll_frequency=0.5):
        return WebDriverWait(web_driver, sec, poll_frequency=poll_frequency).until(cond((by, data)))

    def step(max_repeat=10, sleep_time=1, step_hide_warnings=False, auto_run=False, _args=[]):
        def _inner(func):
            def try_execute_step(*args, max_repeat=max_repeat):
                for attempt in range(1, max_repeat + 1):
                    try:
                        res = func(*args)
                    except (AssertionError, UnexpectedResult) as AE:
                        if not (hide_warnings or step_hide_warnings):
                            print(f'[yellow]Attempt {attempt} not passed[/]', func)
                        if attempt >= max_repeat:
                            raise LaunchLimitExceeded(f'Function failed {max_repeat} attempts').with_traceback(None) from AE

                        time.sleep(sleep_time)
                        continue
                    break
                return res

            return try_execute_step if not auto_run else try_execute_step(*_args)

        return _inner

    @step(auto_run=False)
    def switch_to_last_window():
        assert len(driver.window_handles) > 1
        driver.switch_to.window(driver.window_handles[-1])

    @step(auto_run=False)
    def close_all_tab_except_last():
        for w in driver.window_handles[:-1]:
            driver.switch_to.window(w)
            driver.close()
        driver.switch_to.window(driver.window_handles[-1])

    @step()
    def configure_meta_mask():
        for w in driver.window_handles[1:]:
            driver.switch_to.window(w)
            driver.close()

        driver.switch_to.window(driver.window_handles[-1])

        driver.get(
            'chrome-extension://nkbihfbeogaeaoehlefnkodbefgpgknn/home.html#initialize/create-password/import-with-seed-phrase')

        time.sleep(1)
        inputs = wait_for_elements(By.XPATH, '//input')
        assert len(inputs) == 3
        return inputs

    inputs = configure_meta_mask()

    @step(auto_run=True)
    def signin_metamask():
        inputs[0].send_keys(secret_phases)
        inputs[1].send_keys(temp_password)
        inputs[2].send_keys(temp_password)

        current_url = driver.current_url
        wait_for_element(By.CSS_SELECTOR, '.first-time-flow__terms').click()
        wait_for_element(By.CSS_SELECTOR, '.first-time-flow__button').click()
        for i in range(10):
            if current_url != driver.current_url:
                break
            time.sleep(1)
        #print(driver.current_url)
        assert '#initialize/end-of-flow' in driver.current_url or '#initialize/seed-phrase-intro' in driver.current_url

    @step(auto_run=True)
    def signin_opensea_with_metamask(): # on this step you may caught some troubles with cloudflare
        # TODO: find way to replace time.sleep to sensitive wait
        driver.get('https://opensea.io')
        try:
            wait_for_element(By.XPATH, '//div[@id="cf-wrapper"]', sec=2)
            driver.execute_script(js_injections.open_new_tab_and_reload_it('https://opensea.io/login?referrer=%2Faccount', new_window=True))
            time.sleep(10) # average time spent on passing protection
            close_all_tab_except_last()

            # check Cloudflare passing
            wait_for_elements(By.XPATH, '//*[@id="cf-hcaptcha-container"]//iframe', sec=2,
                              cond=EC.visibility_of_any_elements_located)
            raise UnexpectedResult("Cloudflare show captcha")
        except TimeoutException:
            driver.get('https://opensea.io/login?referrer=%2Faccount')   # cf passed

        @step(auto_run=True)
        def check_for_access_denied():
            """
            Sometimes CloudFlare drop Access Denied, why this is happening is still unclear.

            On this step CF passed. To fix Access Denied only needed:
             - get main domain
             - get needed URL again
            """
            try:
                wait_for_element(By.XPATH, '//span[contains(@class, "code-label")]', sec=1) # span with error code
                driver.get("https://opensea.io/")
                driver.get("https://opensea.io/login?referrer=%2Faccount")
                raise UnexpectedResult("Check access again")
            except TimeoutException:
                ... # all ok

        @step(auto_run=False)
        def bypass_cloudflare():
            try:
                time.sleep(10)
                wait_for_element(By.XPATH, '//div[@id="cf-wrapper"]', sec=3)
                try:
                    wait_for_element(By.XPATH, '//*[@id="cf-spinner-please-wait"]', sec=2)
                    wait_for_element(By.XPATH, '//*[@id="cf-spinner-please-wait"]', sec=60, cond=EC.invisibility_of_element_located, poll_frequency=2) # you need to wait
                    try:

                        wait_for_element(By.XPATH, '//*[@id="cf-spinner-redirecting"]', sec=3, cond=EC.visibility_of_element_located)
                        #wait_for_element(By.XPATH, '//div[@id="cf-wrapper"]', sec=3, cond=EC.invisibility_of_element_located)
                        print('po')
                    except TimeoutException as e:
                        print(e)
                        driver.refresh()
                        raise UnexpectedResult('Cloudfire not passed(maybe captcha)')
                except TimeoutException:
                    driver.refresh()
                    raise UnexpectedResult('Cloudfire | Slow connection')
            except TimeoutException as e:
                print(e)
                ... # all ok

        with auth_lock:
            wait_for_element(By.XPATH, '//span[contains(text(), "MetaMask")]/../..', sec=5).click()

            current_window = driver.current_window_handle

            switch_to_last_window() # switch_to_metamask_popup

            wait_for_element(By.XPATH, '//*[@id="app-content"]/div/div[2]/div/div[2]/div[3]/div[2]/button[2]', sec=5).click()  # step 1
            wait_for_element(By.XPATH, '//*[@id="app-content"]/div/div[2]/div/div[2]/div[2]/div[2]/footer/button[2]', sec=5).click()  # step 2
            driver.switch_to.window(current_window)

            @step(auto_run=True, max_repeat=5)
            def _confirm():
                assert '/account' in driver.current_url

    driver_conf_end_time = time.time()
    #event_bus.put(UploaderEvent(EventType.time_spent_on_last_driver_start, payload=driver_conf_end_time-driver_start_time))

    @step(auto_run=True, max_repeat=3, sleep_time=0.1)
    def get_uploading_page():

        start_time = time.time()
        upload_url = 'https://opensea.io/asset/create' #f'https://opensea.io/collection/{collection_name}/assets/create'
        driver.get(upload_url)

        @step(max_repeat=30, sleep_time=0.1, step_hide_warnings=True)
        def _get_confirm(base_url='/account'):
            assert base_url not in driver.current_url

        _get_confirm()
        if '/login?' in driver.current_url:
            current_window = driver.current_window_handle

            wait_for_element(By.XPATH, '//span[contains(text(), "MetaMask")]/../..').click()

            switch_to_last_window() # switch_to_metamask_popup

            wait_for_element(By.XPATH, '//*[@id="app-content"]/div/div[2]/div/div[3]/button[2]').click()  # confirm
            driver.switch_to.window(current_window)

            @step(auto_run=True, max_repeat=25, sleep_time=0.2, step_hide_warnings=True)
            def _confirm():
                assert '/login' not in driver.current_url

    driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": ["features-proxy.opensea.io", "api.amplitude.com", "google-analytics.com"]})
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_script(js_injections.replace_dom())
    driver.execute_script(js_injections.asset_upload_injection(), 1) # only one "thread" due to banning
    return driver


def init_driver_before_success(
        worker_id: int,
        output_bus: Queue,
        secret_phases: str = SECRET,
        temp_password: str = PASSWORD,
        auth_lock: Lock = Lock(),
        hide_warnings: bool = True,
        max_attempts: int = 5
) -> WebDriverParentClass:
    count = 0
    while max_attempts>count:
        try:
            driver_init_start_time = time.time()
            driver = driver_init(secret_phases, temp_password, auth_lock=auth_lock, hide_warnings=hide_warnings)
            driver_init_end_time = time.time()
            output_bus.put(EventHolder(ServerEvent.WORKER_READY, {"id": worker_id, "duration": driver_init_end_time-driver_init_start_time}))
            return driver
        except (MNUDriverInitError, TimeoutException) as e:
            output_bus.put(EventHolder(ServerEvent.WORKER_DRIVER_INITIALIZING_FAILURE, worker_id))
    output_bus.put(EventHolder(ServerEvent.WORKER_DRIVER_INIT_ATTEMPTS_EXCEEDED, worker_id))


def driver_upload_asset(
        asset_data: dict,
        asset_id: int,
        asset_abs_file_path: str,
        driver: WebDriverParentClass,
        wait_in_sec: Union[int, float] = CollectionConfig().max_upload_time,
        input_group_id: int = 0
) -> UploadResponseHolder:
    """
    Try upload asset and give result

    :param asset_data: See data_holders.SingleAssetData.as_upload_data_dict() for more information.
    :param asset_id: Inner asset id
    :param asset_abs_file_path: Absolute path to asset file
    :param driver: Instance of selenium webdriver returned by driver_init() func
    :param wait_in_sec: max time for waiting response
    :param input_group_id: id of input group (DEPRECATED)
    :return: Result of uploading(response)
    :raises: :exc:`selenium.common.exceptions.TimeoutException` if upload was unsuccessful or uploading timeout occurs
    """
    start_time = time.time()
    driver.find_element(By.ID, f'asset_data_json_{input_group_id}').send_keys(json.dumps(asset_data))
    driver.find_element(By.ID, f'media_{input_group_id}').send_keys(asset_abs_file_path)

    try:
        upload_response_form = WebDriverWait(driver, wait_in_sec).until(
            EC.presence_of_element_located(
                (By.XPATH, f'//*[@id="response_field_{input_group_id}" and @upload_complete="true"]')
            )
        )

        u_response = UploadResponseHolder(upload_response_form.get_attribute('value'), start_time, asset_id)
        upload_response_form.clear()
        return u_response
    except Exception as e:
        upload_response_form = WebDriverWait(driver, 2).until(
            EC.presence_of_element_located(
                (By.XPATH, f'//*[@id="response_field_{input_group_id}"]')
            )
        )
        upload_response_form.clear()
        upload_response_form.send_keys("error")
        raise e


if __name__ == "__main__":
    """
    run test:
    >py.test -s tests/driver_init
    """