import logging
from pathlib import Path

from .gardener import Gardener
from PlantStation.core import EnvironmentConfig


class App(object):
    env_config: EnvironmentConfig
    gardener: Gardener
    debug: bool
    logger = logging.getLogger(__package__)

    def __init__(self, config_path: Path, dry_run: bool = False, debug: bool = False):
        # get config
        self.debug = debug
        self.env_config = EnvironmentConfig(config_path, debug=self.debug, dry_run=dry_run)
        self.gardener = Gardener(env_config=self.env_config)

        self.gardener.schedule_monitoring()

    def run(self):
        self.gardener.start()

