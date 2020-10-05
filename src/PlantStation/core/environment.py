import logging
from typing import List

from .config import EnvironmentConfig
from .ext import PinManager, EventLoop
from .plant import Plant


class Environment(object):
    """Environment gathers all information about plants.

    Class holds information about plants. It is responsible for scheduling
    all the actions, as based in environment.cfg file.

    Attributes:
        config (:obj:`EnvironmentConfig`): Environment config

    """
    _config: EnvironmentConfig
    _plants: [Plant]
    _logger: logging.Logger

    _env_loop: EventLoop
    _pin_manager: PinManager

    def __init__(self, config: EnvironmentConfig):
        self._config = config
        self._name = self.config.env_name
        self._plants = []
        self._logger = self.config.logger.getChild('Environment')

        # initialize pins
        self._pin_manager = PinManager(dry_run=self.config.dry_run, config=config)
        self._env_loop = EventLoop()

        self._logger.info(f'Created {self.name} environment')
        for params in self.config.parse_plants():
            self._plants.append(
                Plant(env_loop=self._env_loop, pin_manager=self._pin_manager, envConfig=self.config, **params))

    @property
    def name(self) -> str:
        """Environment name"""
        return self._name

    @property
    def plants(self) -> List[Plant]:
        """List of plants"""
        return self._plants

    @property
    def config(self) -> EnvironmentConfig:
        """Environment config"""
        return self._config

    @property
    def env_loop(self) -> EventLoop:
        """Environment task loop"""
        return self._env_loop

    @property
    def pin_manager(self) -> PinManager:
        """Local pin manager"""
        return self._pin_manager

    def start(self) -> None:
        self.env_loop.start()

    def stop(self) -> None:
        self.env_loop.stop()
