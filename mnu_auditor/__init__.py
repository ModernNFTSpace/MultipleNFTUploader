"""
The module is designed to collect environmental errors and explain them (solutions, or at least the cause).
Runs before starting work to check the environment.
"""
from config import search_mismatches, check_filenames_conflict, AuditorConfigMismatchesFound, AuditorConfigFilenamesConflict, ConfigClass
from glob import glob

from rich.console import Console

import os


def scan_env_errors() -> None:
    """
    Try to detect error, like configs or driver missing
    """
    console = Console()

    collected_errors = []

    configs_pattern = os.path.join(ConfigClass.configs_dir(), '*.conf')
    if len(glob(configs_pattern)) < 1:
        console.log("Looks like it's the first run. Execute '[green]python main.py --setup[/]' and then fill in the config files[[yellow]./configs/*.conf[/]]. After that -> restart. Look docs for details.")
        console.log("Exiting...")
        exit()

    configs_mismatches = search_mismatches()
    if sum(len(cm) for cm in configs_mismatches.values()) > 0:
        collected_errors.append(AuditorConfigMismatchesFound())

    if len(check_filenames_conflict()) > 0:
        collected_errors.append(AuditorConfigFilenamesConflict())

    from driver_init import check_webdriver_exists, MNUDriverBinaryNotFound

    if not check_webdriver_exists():
        collected_errors.append(MNUDriverBinaryNotFound())

    if len(collected_errors) > 0:
        from .error_interpreter import explain_errors
        console.log(explain_errors(collected_errors))
        exit()
