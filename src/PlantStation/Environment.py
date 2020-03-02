import logging
from configparser import ConfigParser
from sched import scheduler
from typing import Callable

from PlantStation.Plant import Plant
from PlantStation.helpers.format_validators import *
from PlantStation.helpers.sched_states import SchedState, SchedPriorityTable


class Environment:
    """Environment is a set of plants.

    Class holds information about plants. It is responsible for scheduling
    all the actions, as based in environment.cfg file.

    Attributes:
    -----------

    name  : str
        Name of the environment (default main)

    Methods:
    --------

    read_config()
        Reads environment config file

    schedule_monitoring()
        Sets up event scheduler - Obligatory before starting event scheduler

    start()
        Starts to look after plants - starting event scheduler

    stop()
        Stops to look after plants - stopping event scheduler
    """
    name: str
    _cfg_path: str
    _plants: [Plant] = []
    _envScheduler = scheduler()
    _envSchedulerState = SchedState.UNSET
    _eventsOutOfQueue = []
    _envLogger: logging.Logger
    _dry_run: bool

    def __init__(self, config_path: str, env_name: str = "main", dry_run: bool = False):
        """
        Args:
            name (str): Env name
        """
        self._cfg_path = config_path
        self._dry_run = dry_run
        self.name = env_name
        self._envLogger = logging.getLogger(__package__ + "." + self.name)

        self._envLogger.info(f'Created {self.name} environment')
        self._read_config()

    def _read_config(self):
        """Reads environment config file

        Reads config file from location defined by self._cfg_paths
        and if provided data are correct, creates Plants with provided data
        """
        config = ConfigParser()
        if not config.read(filenames=self._cfg_path):
            self._envLogger.critical(
                'Config file %s not found', self._cfg_path)
            raise FileNotFoundError(
                'Error: environment config file not found. Quitting!')

        # read global section
        self._envLogger.info('Reading config file: %s', self._cfg_path)

        # Left for future - to be implemented
        # global_config_section = config['GLOBAL']

        # read_plants
        for section in config:
            if section == 'DEFAULT':
                continue
            if section != 'GLOBAL':
                self._envLogger.debug('Found new section: %s', section)
                try:
                    params = {
                        'plant_name': str(section),
                        'watering_duration': datetime.timedelta(seconds=int(config[section]['wateringDuration'])),
                        'watering_interval': parse_time(time_str=config[section]['wateringInterval']),
                        'gpio_pin_number': str(config[section]['gpioPinNumber'])}
                    if config[section]['lastTimeWatered'] != '':
                        time_str = config[section]['lastTimeWatered']
                        params['last_time_watered'] = datetime.datetime.strptime(time_str, '%Y-%m-%d %X')
                    else:
                        params['last_time_watered'] = datetime.datetime.min
                    new_plant = Plant(**params, env_name=self.name, dry_run=self._dry_run)
                    self._envLogger.info(
                        f'Found new plant: {params["plant_name"]}, pin: {params["gpio_pin_number"]}')
                    self._plants.append(new_plant)
                except KeyError as err:
                    self._envLogger.error(
                        f'{self._cfg_path}: Failed to read {section} section - '
                        f'option not found {str(err)}')
                except ValueError as err:
                    self._envLogger.error(
                        f'{self._cfg_path}: Failed to read {section} section {err}')
                except Exception as err:
                    self._envLogger.error(
                        f'{self._cfg_path} Failed to read {section} section {str(err)}')

    def schedule_monitoring(self) -> None:
        """Sets up event scheduler - Obligatory before starting event scheduler

        Schedules to check all plants
        """
        self._envLogger.debug('Scheduling monitoring')
        for plant in self._plants:
            self._handle_sched_action(plant.should_water)
        self._envLogger.debug('Scheduler state : STOPPED')
        self._envSchedulerState = SchedState.STOPPED
        self._envLogger.debug(f'Scheduled monitoring - OK')

    def start(self) -> None:
        """Starts to look after plants

        Starts environment's event scheduler
        """
        self._envLogger.debug(
            'Starting scheduler. State: %s',
            self._envSchedulerState)
        if self._envSchedulerState == SchedState.STOPPED:
            self._envLogger.info('Starting scheduler')
            self._resume_scheduler()
        else:
            self._envLogger.warning(
                'Can\'t start up scheduler - wrong scheduler state')

    def stop(self) -> None:
        """Stops to look after plants

        Stops environment's event scheduler
        """
        self._envLogger.debug(
            'Stopping scheduler. State: %s',
            self._envSchedulerState)
        if self._envSchedulerState == SchedState.RUNNING:
            self._envSchedulerState = SchedState.PAUSED
            self._envLogger.info('Pausing scheduler.')
            self._envScheduler.enter(
                delay=0,
                priority=SchedPriorityTable.SCHED_STOP,
                action=self._stop_scheduler())

    def _handle_sched_action(self, func: Callable[[any], any]) -> {}:  # todo decorator
        """Wrapper for all actions in scheduler

        Handles all functions in scheduler to give them access to modify
        environment's state Function can return:

            'config_params' dict - allows changing option's value in config file
            'sched_params' dict - allows adding event to scheduler

        Args:
            func: Function to be handled
        """
        try:
            self._envLogger.debug('Handling function')

            params = func()

            self._envLogger.debug('Handler: Got params: %s', params)

            if 'config_params' in params:
                self._update_config_section(**params['config_params'])

            if 'sched_params' in params:
                params['sched_params']['argument'] = [
                    params['sched_params']['action']]
                params['sched_params']['action'] = self._handle_sched_action
                self._add_to_scheduler(params['sched_params'])
                self._envLogger.debug(f'''Added new event to logger: {params['sched_params']}''')

        except Exception as err:
            self._envLogger.critical(
                'Handler received exception. Killing scheduler.')
            self._envScheduler.enter(
                delay=0,
                priority=SchedPriorityTable.SCHED_STOP,
                action=self._kill_scheduler())
            raise err

    def _add_to_scheduler(self, event):
        """Adds event to scheduler in controlled way

        Args:
            event: Scheduler's Event to be added
        """
        if self._envSchedulerState in (SchedState.STOPPED, SchedState.PAUSED):
            self._eventsOutOfQueue.append(event)
        elif self._envSchedulerState in (SchedState.UNSET, SchedState.RUNNING):
            self._envScheduler.enter(**event)
        else:
            pass

    def _stop_scheduler(self) -> None:
        """Stops scheduler

        Stops all watering tasks and empties scheduler. All tasks are
        awaiting for resuming scheduler.
        """
        self._envLogger.info(
            'Stopping scheduler. State: %s',
            self._envSchedulerState)
        for event in self._envScheduler.queue:
            if event.action == Plant.water_off:
                self._envLogger.info('Calling Plant.water_off forced')
                event.action()
            else:
                self._eventsOutOfQueue.append(event)
            self._envScheduler.cancel(event)
        self._envSchedulerState = SchedState.STOPPED

    def _kill_scheduler(self) -> None:
        """Forces scheduler to stop

        Stops all watering tasks and empties scheduler. Can't be resumed
        after that
        """
        self._envLogger.debug('Killing scheduler. State: %s', self._envSchedulerState)
        self._envSchedulerState = SchedState.KILLED
        for event in self._envScheduler.queue:
            if event.action == Plant.water_off:
                event.action()
            self._envScheduler.cancel(event)
        self._envLogger.info('Scheduler killed.')

    def _resume_scheduler(self) -> None:
        """Resumes scheduler

        Resumes scheduler if stopped. Otherwise does nothing.
        """
        self._envLogger.debug('Resuming scheduler. State: %s', self._envSchedulerState)
        if self._envSchedulerState == SchedState.STOPPED:
            for event in self._eventsOutOfQueue:
                self._envScheduler.enter(**event)

            self._eventsOutOfQueue.clear()
            self._envSchedulerState = SchedState.RUNNING
            try:
                self._envScheduler.run()
            except TypeError or KeyboardInterrupt:
                self._envLogger.info(f'SIGINT received. Quitting!')

        else:
            self._envLogger.warning('Scheduler is not paused. Can\'t resume')

    def _update_config_section(
            self,
            section_name: str,
            option: str,
            val: any) -> None:
        """Updates selected environment config section

        Args:
            section_name (str): Config section name
            option (str): Option name to be updated
            val (any): New value
        """
        config = ConfigParser()
        self._envLogger.debug(
            f'Updating config section {section_name} {option} {val}')

        if not config.read(filenames=self._cfg_path):
            self._envLogger.error('Environment config file not found')
            raise FileNotFoundError('Environment config file not found')

        config[section_name][option] = str(val)
        try:
            cfg_file = open(file=self._cfg_path, mode='w')
            config.write(fp=cfg_file)
            cfg_file.close()
        except IOError:
            self._envLogger.error('Couldn\'t write config to file')
            raise Exception('Couldn\'t write config to file')
