import datetime
import logging
import sched
from typing import Callable

from PlantStation.Plant import Plant
from PlantStation.helpers.sched_states import SchedPriorityTable


class TaskPool(object):
    """
        Pool of scheduled tasks
    """
    logger: logging.Logger
    _scheduler = sched.scheduler()
    _active_tasks = []

    def __init__(self, env_name: str):
        self.logger = logging.getLogger(__package__ + '.' + env_name + '.pool')
        self._scheduler.enterabs(time=datetime.timedelta.max.total_seconds(), priority=SchedPriorityTable.SCHED_STOP,
                                 action=lambda: None)

    def add_task(self, task) -> None:
        """Adds task to taskpool
        """
        self.logger.debug(f'Adding new task to pool: {task.priority}')
        self._active_tasks.append(task)
        self._scheduler.enter(delay=task.delay.total_seconds(), priority=task.priority, action=self._handle_action,
                              argument=[task])

    def start(self) -> None:
        """Starts scheduler
        """
        try:
            self.logger.debug(f'Starting pool')
            self._scheduler.run()
        except Exception:
            self.stop()

    def stop(self) -> None:
        """Stops to look after plants

        Stops environment's event scheduler
        """
        self.logger.debug('Stopping scheduler. State: %s')

        for event in self._active_tasks:
            if isinstance(event, WaterOffTask):
                event.run()

    def _handle_action(self, task):
        new_task = task.func()
        self._active_tasks.remove(task)
        self.add_task(new_task)


class Task(object):
    """
        Schedulable task
    """
    func: Callable
    delay: datetime.timedelta
    env: None
    priority: SchedPriorityTable

    def __init__(self, delay: datetime.timedelta, priority: SchedPriorityTable, action: Callable, env):
        self.func = action
        self.priority = priority
        self.delay = delay
        self.env = env

    def run(self):
        """
            Run task and generate new
        """
        pass


class ShouldWaterTask(Task):
    """
    Task for checking if plant needs to be watered
    """
    plant: Plant

    def __init__(self, plant: Plant, env, delay= datetime.timedelta(0)):
        self.plant = plant
        super().__init__(delay= delay, priority=SchedPriorityTable.should_water, action=self.run,
                         env=env)

    def run(self) -> Task:
        """Check if plants need to be watered

            if so -> create watering task
            else calculate time to next watering

        :return: new task
        """

        if self.plant.should_water():
            self.env.pool.logger.debug(f'ShouldWaterTask: Scheduling waterOnTask')
            return WaterOnTask(self.plant, self.env)
        else:
            self.env.pool.logger.debug(f'ShouldWaterTask: Postponing shouldWaterTask')
            delay = self.plant.calc_next_watering() - datetime.datetime.now()
            return ShouldWaterTask(self.plant, self.env, delay= delay)


class WaterOnTask(Task):
    """
    Task for turning on watering
    """
    plant: Plant

    def __init__(self, plant: Plant, env, delay=datetime.timedelta(0)):
        self.plant = plant
        super().__init__(delay=delay, priority=SchedPriorityTable.waterOn, action=self.run, env=env)

    def run(self) -> Task:
        """
            Waters plants if there are working hours
            otherwise postpones it
        :return: waterOff or postponed waterOn task
        """

        if len(self.env.working_hours) == 2:
            if self.env.working_hours[0] <= datetime.datetime.now().time() < self.env.working_hours[1]:
                self.env.pool.logger.debug(f'WaterOn: scheduling waterOff')
                self.plant.water_on()
                return WaterOffTask(self.plant, self.env)
            else:
                # postpone
                self.env.pool.logger.debug(f'WaterOn: Postponing waterOn')
                next_working_window = datetime.datetime.combine(datetime.datetime.now().date(), self.env.working_hours[0])
                if next_working_window < datetime.datetime.now():
                    next_working_window += datetime.timedelta(days=1)
                diff = next_working_window - datetime.datetime.now()
                return WaterOnTask(self.plant, self.env, diff)
        else:
            self.env.pool.logger.debug(f'WaterOn: scheduling waterOff')
            self.plant.water_on()
            return WaterOffTask(self.plant, self.env)


class WaterOffTask(Task):
    """
    Task for turning off watering
    """
    plant: Plant

    def __init__(self, plant: Plant, env):
        self.plant = plant
        super().__init__(delay=self.plant.wateringDuration, priority=SchedPriorityTable.waterOff, action=self.run,
                         env=env)

    def run(self) -> Task:
        """Turns of watering and updates config

        :return: next watering task (should water)
        """
        self.env.pool.logger.debug(f'WaterOff: Scheduling waterOff')
        self.plant.water_off()
        self.env.config.cfg_parser[self.plant.plantName]['lastTimeWatered'] = datetime.datetime.now().strftime(
            '%Y-%m-%d %X')
        self.env.config.write()
        return ShouldWaterTask(self.plant, self.env)
