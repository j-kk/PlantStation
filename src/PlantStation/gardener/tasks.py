import datetime
import logging
import threading
from threading import Lock
from typing import Callable

from PlantStation.core.ext import MultithreadSched
from PlantStation.core import plant, EnvironmentConfig
from .helpers import SchedPriorityTable


class TaskPool(object):
    """
        Pool of scheduled tasks
    """
    logger: logging.Logger
    env_config: EnvironmentConfig
    _scheduler = MultithreadSched()
    _active_tasks = []
    lock = Lock()

    def __init__(self, env_config: EnvironmentConfig):
        self.logger = env_config.logger.getChild('TaskPool')
        self.env_config = env_config

    def add_task(self, task) -> None:
        """
            Adds task to taskpool
        """
        with self.lock:
            self.logger.debug(f'Adding new task to pool: {task}. Delay: {task.delay.total_seconds()}')
            self._active_tasks.append(task)
            self._scheduler.enter(delay=task.delay.total_seconds(), priority=task.priority, action=self._run_task,
                                  argument=[task])

    def start(self) -> None:
        """
            Starts scheduler
        """
        try:
            self.logger.debug(f'Starting pool')
            self._scheduler.run()
        except Exception as exc:
            self.logger.warning(f'Received exception {exc}')
            self.stop()

    def stop(self) -> None:
        """Stops to look after plants

        Stops environment's event scheduler
        """
        self.logger.debug(f'Stopping scheduler.')
        # temporary
        for event in self._active_tasks:
            self._scheduler.cancel(event)
            if event.task is not None:
                event.task.cancel()

    @property
    def active_tasks(self):
        """Returns all tasks to be executed/already working

        Returns
        -------

        """
        with self.lock:
            return self._active_tasks

    def _run_task(self, task):
        self.logger.debug(f'Running taskthread {task}')
        new_task = task.run()
        self.active_tasks.remove(task)
        self.logger.debug(f'Adding new task {new_task}')
        self.add_task(new_task)


class Task(object):
    """
        Schedulable task

    Attributes:
    -----------

    func  : str
        function to be executed

    """
    func: Callable
    delay: datetime.timedelta
    env_config: EnvironmentConfig
    priority: SchedPriorityTable
    logger: logging.Logger

    def __init__(self, delay: datetime.timedelta, priority: SchedPriorityTable, action: Callable,
                 env_config: EnvironmentConfig):
        self.func = action
        self.priority = priority
        self.delay = delay
        self.env_config = env_config
        self.logger = self.env_config.logger.getChild('Task')

    def run(self):
        pass


class ShouldWaterTask(Task):
    """
    Task for checking if plant needs to be watered
    """
    plant: plant

    def __init__(self, plant: plant, env_config: EnvironmentConfig, delay=datetime.timedelta(0)):
        self.plant = plant
        super().__init__(delay=delay, priority=SchedPriorityTable.should_water, action=self.run,
                         env_config=env_config)

    def run(self) -> Task:
        """Check if plants need to be watered

            if so -> create watering task
            else calculate time to next watering

        :return: new task
        """

        if self.plant.should_water():
            self.logger.debug(f'ShouldWaterTask: Scheduling waterOnTask')
            return WaterTask(self.plant, env_config=self.env_config)
        else:
            self.logger.debug(f'ShouldWaterTask: Postponing shouldWaterTask')
            delay = self.plant.calc_next_watering() - datetime.datetime.now()
            return ShouldWaterTask(self.plant, env_config=self.env_config, delay=delay)


class WaterTask(Task):
    """
    Task for turning on watering
    """
    plant: plant

    def __init__(self, plant: plant, env_config: EnvironmentConfig, delay=datetime.timedelta(0)):
        self.plant = plant
        super().__init__(delay=delay, priority=SchedPriorityTable.water, action=self.run, env_config=env_config)

    def run(self) -> Task:
        """
            Waters plants if there are working hours
            otherwise postpones it
        :return: ShouldWaterTask or postponed waterOn task
        """
        self.logger.info(f'Starting to water plant {self.plant.plantName}')
        if self.env_config.silent_hours:
            if self.env_config['workingHoursBegin'] <= datetime.datetime.now().time() < self.env_config[
                'workingHoursEnd']:
                self.logger.debug(f'WaterOn: watering plant')
                self.plant.water()
                self.env_config[self.plant.plantName]['lastTimeWatered'] = datetime.datetime.now().strftime(
                    '%Y-%m-%d %X')
                self.env_config.write()
                return ShouldWaterTask(self.plant, env_config=self.env_config)
            else:
                # postpone
                self.logger.debug(f'WaterOn: Postponing waterOn')
                next_working_window = datetime.datetime.combine(datetime.datetime.now().date(),
                                                                self.env_config['workingHoursBegin'])
                if next_working_window < datetime.datetime.now():
                    next_working_window += datetime.timedelta(days=1)
                diff = next_working_window - datetime.datetime.now()
                return WaterTask(self.plant, env_config=self.env_config, delay=diff)
        else:
            self.logger.debug(f'WaterOn: watering plant')
            self.plant.water()
            self.env_config[self.plant.plantName]['lastTimeWatered'] = datetime.datetime.now().strftime(
                '%Y-%m-%d %X')
            self.env_config.write()
            return ShouldWaterTask(self.plant, env_config=self.env_config)
