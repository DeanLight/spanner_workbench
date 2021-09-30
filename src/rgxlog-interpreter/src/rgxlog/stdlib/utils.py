import shlex

import logging
import time

import psutil
import requests
from pathlib import Path
from subprocess import Popen, PIPE
from sys import platform
from threading import Timer
from typing import Iterable, no_type_check

logger = logging.getLogger(__name__)

WINDOWS_OS = "win32"
IS_POSIX = (platform != WINDOWS_OS)

# google drive
GOOGLE_DRIVE_URL = "https://docs.google.com/uc?export=download"
GOOGLE_DRIVE_CHUNK_SIZE = 32768


def kill_process_and_children(process: Popen):
    logger.info("~~~~ process timed out ~~~~")
    if process.poll() is not None:
        ps_process = psutil.Process(process.pid)
        for child in ps_process.children(recursive=True):  # first, kill the children :)
            child.kill()  # not recommended in real life
        process.kill()  # lastly, kill the process


@no_type_check
def run_cli_command(command: str, stderr: bool = False, shell: bool = False, timeout: float = -1) -> Iterable[str]:
    """
    This utility can be used to run any cli command, and iterate over the output.

    @param timeout: if positive, kill the process after `timeout` seconds. default: `-1`.
    @param stderr: if true, suppress stderr output. default: `False`.
    @param shell: if true, spawn shell process (e.g. /bin/sh), which allows using system variables (e.g. $HOME),
        but is considered a security risk (see:
        https://docs.python.org/3/library/subprocess.html#security-considerations).
    @param command: a single command string.
    @return: string iterator.
    """
    # `shlex.split` just splits the command into a list properly
    command_list = shlex.split(command, posix=IS_POSIX)
    stdout = PIPE  # we always use stdout
    stderr_channel = PIPE if stderr else None

    # TODO@niv: this is temporary until the rgx issue is solved
    time.sleep(2)
    process = Popen(command_list, stdout=stdout, stderr=stderr_channel, shell=shell)

    # set timer
    process_timer = None
    if timeout > 0:
        # set timer to kill the process
        process_timer = Timer(timeout, kill_process_and_children, [process])
        process_timer.start()

    # get output
    process.stdout.flush()
    for output in process.stdout:
        # convert to `str` and remove the `\n` at the end of every line
        output = output.decode("utf-8").strip()
        # TODO@niv: change the logging back to debug once the error is found
        logger.info(f"output from {command_list[0]}: {output}")
        if output:
            yield output
            process.stdout.flush()
        elif process.poll() is not None:  # process died
            if process_timer is not None:
                process_timer.cancel()
            break

    extra_stdout, extra_stderr = process.communicate()
    logger.info(f"stdout after the process ended: {extra_stdout}")
    logger.info(f"stderr after the process ended: {extra_stderr}")


def download_file_from_google_drive(file_id: str, destination: Path) -> None:
    """
    Downloads a file from google drive.
    Taken from https://stackoverflow.com/questions/25010369/wget-curl-large-file-from-google-drive/39225039#39225039.

    @param file_id: the id of the file to download.
    @param destination: the path to which the file will be downloaded.
    """
    requests_session = requests.Session()
    response = requests_session.get(GOOGLE_DRIVE_URL, params={'id': file_id}, stream=True)

    def get_confirm_token():
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                return value

        return None

    def save_response_content():
        with open(destination, "wb") as f:
            for chunk in response.iter_content(GOOGLE_DRIVE_CHUNK_SIZE):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)

    token = get_confirm_token()
    logger.debug(f"got token from google: {token}")

    if token:
        params = {'id': file_id, 'confirm': token}
        response = requests_session.get(GOOGLE_DRIVE_URL, params=params, stream=True)

    save_response_content()
