import logging

from PlantStation.core import Environment, EnvironmentConfig
from .tasks import TaskPool, ShouldWaterTask


class Gardener(object):
    """Maintains plant and schedules watering

    Holds information about environment and uses task pool to schedule watering

    Parameters
    ----------

    environment : Environment
        Reference to monitored environment

    pool : TaskPool
        Related Task Pool


    """
    environment: Environment
    pool: TaskPool
    _logger: logging.Logger

    def __init__(self, env_config: EnvironmentConfig):
        self._logger = env_config.logger
        self._logger.setLevel(logging.DEBUG if env_config.debug else logging.INFO)
        self._logger.debug(f'Creating environment')
        self.environment = Environment(env_config)
        self._logger.debug(f'Creating task pool')
        self.pool = TaskPool(env_config)

    def schedule_monitoring(self) -> None:
        """Sets up event scheduler - Obligatory before starting event scheduler

        Schedules to check all plants
        """
        self._logger.debug('Scheduling monitoring')
        for plant in self.environment.plants:
            self.pool.add_task(ShouldWaterTask(plant=plant, env_config=self.environment.config))
        self._logger.debug(f'Scheduled monitoring - OK')

    def start(self) -> None:
        """Starts to look after plants
        Starts pool tasks
        """
        self._logger.info('Starting scheduler')
        self.pool.start()
