import logging
from .plant import Plant
from .config import EnvironmentConfig


class Environment(object):
    """Environment gathers all information about plants.

    Class holds information about plants. It is responsible for scheduling
    all the actions, as based in environment.cfg file.

    Attributes:
    -----------

    config  : environment config
        Environment config

    po

    Methods:
    --------

    read_config()
        Reads environment config file

    schedule_monitoring()
        Sets up event scheduler - Obligatory before starting event scheduler

    start()
        Starts to look after plants - starting event scheduler

    """
    config: EnvironmentConfig
    plants: [Plant] = []
    _logger: logging.Logger

    def __init__(self, config: EnvironmentConfig):
        """
        Args:
            config_path: Config property (used to read values and update)

            env_name (str): name of the environment

            active_limit (int): max number of active pumps at once

            dry_run (boolean): should pumps be active?

        """
        self.config = config
        self.name = self.config.env_name
        self._logger = self.config.logger.getChild('Environment')
        self._logger.setLevel(logging.DEBUG if self.config.debug else logging.INFO)

        self._logger.info(f'Created {self.name} environment')
        for params in self.config.read_plants():
            self.plants.append(Plant(envConfig=self.config, **params))
