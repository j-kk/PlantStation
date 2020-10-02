import abc
import asyncio
import datetime
import logging
import threading
from threading import Lock
from typing import Callable

from PlantStation.core.ext import MultithreadSched, SilentHoursException
from PlantStation.core import plant, EnvironmentConfig


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
            self._scheduler.enter(delay=task.delay, action=self._run_task, args=[task])

    def start(self) -> None:
        """
            Starts scheduler
        """
        try:
            self.logger.debug(f'Starting pool')
            self._scheduler.run()
        except KeyboardInterrupt as exc:
            self.logger.info(f'Received SIGING. Turning off scheduler')
            self._scheduler.stop()

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
            # self._scheduler.cancel(event)
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


class Task(abc.ABC):
    """
        Schedulable task

    Attributes:
    -----------

    func  : str
        function to be executed

    """
    delay: datetime.timedelta
    env_config: EnvironmentConfig
    logger: logging.Logger

    def __init__(self, delay: datetime.timedelta, action: Callable, env_config: EnvironmentConfig):
        self.func = action
        self.delay = delay
        self.env_config = env_config
        self.logger = self.env_config.logger.getChild('Task')

    async def wait(self):
        await asyncio.sleep(self.delay.total_seconds())

    @abc.abstractmethod
    async def run(self):
        raise NotImplementedError()


class ShouldWaterTask(Task):
    """
    Task for checking if plant needs to be watered
    """
    plant: plant

    def __init__(self, plant: plant, env_config: EnvironmentConfig, delay=datetime.timedelta(0)):
        self.plant = plant
        super().__init__(delay=delay, action=self.run, env_config=env_config)

    async def run(self) -> Task:
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
        super().__init__(delay=delay, action=self.run, env_config=env_config)

    async def run(self) :
        """
            Waters plants if there are working hours
            otherwise postpones it
        :return: ShouldWaterTask or postponed waterOn task
        """
        self.logger.info(f'Starting to water plant {self.plant.plantName}')
        dt = self.env_config.pin_manager.calc_working_hours()
        await asyncio
        if dt is not None:
            self.logger.info(f'Water: postponing watering {datetime.datetime.now()}')
            return ShouldWaterTask(self.plant, env_config=self.env_config, delay=dt)
        else:
            self.logger.debug(f'Watering plant')
            try:
                self.plant.water()
                return ShouldWaterTask(self.plant, env_config=self.env_config)
            except SilentHoursException:
                dt = self.env_config.pin_manager.calc_working_hours()
                self.logger.info(f'Water: postponing watering {datetime.datetime.now()}')
                return ShouldWaterTask(self.plant, env_config=self.env_config, delay=dt)
                