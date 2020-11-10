import logging
import signal
import threading
from pathlib import Path

from PlantStation.core.config import EnvironmentConfig
from PlantStation.core.environment import Environment


def __sighandler(event: threading.Event, *args):
    event.set()


class App(object):
    _mainEnvironment: Environment
    _config_path: Path

    __event: threading.Event

    def __init__(self, config_path: Path, dry_run: bool = False):
        # get config
        self._config_path = config_path

        self._logger = logging.getLogger(__package__)

        env_config = EnvironmentConfig.create_from_file(self._config_path)

        self._mainEnvironment = Environment(env_config, dry_run)

        self.__event = threading.Event()

        for sig in [signal.SIGINT, signal.SIGHUP, signal.SIGTERM]:
            signal.signal(sig, lambda *_: self.__event.set())

    def run(self):
        try:
            self._mainEnvironment.start()
            self.__event.wait()
        finally:
            self._mainEnvironment.stop()
