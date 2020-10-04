import logging
from .plant import Plant
from .config import EnvironmentConfig


class Environment(object):
    """Environment gathers all information about plants.

    Class holds information about plants. It is responsible for scheduling
    all the actions, as based in environment.cfg file.

    Attributes:
        config (:obj:`EnvironmentConfig`): Environment config

    """
    config: EnvironmentConfig
    _plants: [Plant]
    _logger: logging.Logger

    @property
    def plants(self) -> [Plant]:
        """List of plants"""
        return self._plants

    def __init__(self, config: EnvironmentConfig):
        self.config = config
        self.name = self.config.env_name
        self._plants = []
        self._logger = self.config.logger.getChild('Environment')
        self._logger.setLevel(logging.DEBUG if self.config.debug else logging.INFO)

        self._logger.info(f'Created {self.name} environment')
        for params in self.config.parse_plants():
            self._plants.append(Plant(envConfig=self.config, **params))

