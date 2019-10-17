import logging
from configparser import ConfigParser
from datetime import timedelta, datetime
from sched import scheduler
from typing import Callable

from Plant import Plant
from helpers import format_validators
from helpers.sched_states import SchedState, SchedPriorityTable

CONFIGFILE_DEFAULT_PATH = 'environment.cfg'


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
    __cfg_path: str
    _plants: [Plant] = []
    _envScheduler = scheduler()  # TODO create class - advanced scheduler
    _envSchedulerState = SchedState.UNSET
    _eventsOutOfQueue = []
    _envLogger: logging.Logger

    def __init__(self, name: str = "main", cfg_path: str = CONFIGFILE_DEFAULT_PATH):
        """
        Args:
            name (str): Plant name
        """
        self.__cfg_path = cfg_path

        self.name = name
        self.read_config()
        self._envLogger = logging.getLogger(__package__ + "." + name)
        self._envLogger.info('Created %s environment')
        self.start()

    def read_config(self):
        """Reads environment config file

        Reads config file from location defined by CONFIGFILE_DEFAULT_PATH
        and if provided data are correct, creates Plants with provided data
        """
        config = ConfigParser()
        if not config.read(filenames=self.__cfg_path):
            self._envLogger.critical('Config file %s not found', CONFIGFILE_DEFAULT_PATH)
            raise FileNotFoundError('Error: environment config file not found. Quitting!')

        # read global section
        self._envLogger.info('Reading config file: %s', CONFIGFILE_DEFAULT_PATH)

        # Left for future - to be implemented
        # global_config_section = config['GLOBAL']

        # read _plants
        for section in config:
            if section != 'GLOBAL':
                section_name = section.name
                self._envLogger.debug('Found new section: %s', section_name)
                try:
                    params = {'plantName': str(section.name),
                              'wateringDuration': timedelta(seconds=int(section['wateringDuration'])),
                              'wateringInterval': format_validators.parse_time(
                                  time_str=section['wateringInterval']),
                              'lastTimeWatered': datetime.strptime(date_string=section['lastTimeWatered'],
                                                                   format='%Y-%m-%d %H:%M%:%S'),
                              'gpioPinNumber': str(section['gpioPinNumber'])}

                    new_plant = Plant(**params, env_name=self.name)
                    self._envLogger.info('Found new plant: %s, pin: %s', params['plantName'], params['gpioPinNumber'])
                    self._plants.append(new_plant)
                except KeyError as err:
                    self._envLogger.warning(f'{CONFIGFILE_DEFAULT_PATH}: Failed to read {section_name} section - '
                                            f'option not found {str(err)}')
                except ValueError as err:
                    self._envLogger.warning(
                        f'{CONFIGFILE_DEFAULT_PATH}: Failed to read {section_name} section {str(err)}')
                except Exception as err:
                    self._envLogger.warning(
                        f'{CONFIGFILE_DEFAULT_PATH} Failed to read {section_name} section {str(err)}')

    def schedule_monitoring(self) -> None:
        """Sets up event scheduler - Obligatory before starting event scheduler

        Schedules to check all plants
        """
        self._envLogger.debug('Scheduling monitoring')
        for plant in self._plants:
            self.__handle_sched_action(plant.should_water)
        self._envLogger.debug('Scheduler state : STOPPED')
        self._envSchedulerState = SchedState.STOPPED

    def start(self) -> None:
        """Starts to look after plants

        Starts environment's event scheduler
        """
        self._envLogger.debug('Starting scheduler. State: %s', self._envSchedulerState)
        if self._envSchedulerState == SchedState.STOPPED:
            self._envLogger.info('Starting scheduler')
            self.__resume_scheduler()
        else:
            self._envLogger.warning('Can\'t start up scheduler - wrong scheduler state')

    def stop(self) -> None:
        """Stops to look after plants

        Stops environment's event scheduler
        """
        self._envLogger.debug('Stopping scheduler. State: %s', self._envSchedulerState)
        if self._envSchedulerState == SchedState.RUNNING:
            self._envSchedulerState = SchedState.PAUSED
            self._envLogger.info('Pausing scheduler.')
            self._envScheduler.enter(delay=0, priority=SchedPriorityTable.SCHED_STOP, action=self.__stop_scheduler())

    def __handle_sched_action(self, func: Callable[[None], any]) -> {}:
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
            params: {} = func(None)

            self._envLogger.debug('Handler: Got params: %s', params)

            if 'config_params' in params:
                self.__update_config_section(**params['config_params'])

            if 'sched_params' in params:
                self.__add_to_scheduler(**params['sched_params'])

        except Exception as err:
            self._envLogger.critical('Handler received exception. Killing scheduler.')
            self._envScheduler.enter(delay=0, priority=SchedPriorityTable.SCHED_STOP,
                                     action=self.__kill_scheduler())
            raise err

    def __add_to_scheduler(self, params):
        """Adds event to scheduler in controlled way

        Args:
            params: Scheduler's Event to be added
        """
        if self._envSchedulerState in [SchedState.STOPPED, SchedState.PAUSED]:
            self._eventsOutOfQueue.append(params)
        elif self._envSchedulerState in [SchedState.UNSET, SchedState.RUNNING]:
            self._envScheduler.enter(**params)
        else:
            pass

    def __stop_scheduler(self) -> None:
        """Stops scheduler

        Stops all watering tasks and empties scheduler. All tasks are
        awaiting for resuming scheduler.
        """
        self._envLogger.info('Stopping scheduler. State: %s', self._envSchedulerState)
        for event in self._envScheduler.queue:
            if event.action == Plant.water_off:
                self._envLogger.info('Calling Plant.water_off forced')
                event.action()
            else:
                self._eventsOutOfQueue.append(event)
            self._envScheduler.cancel(event)
        self._envSchedulerState = SchedState.STOPPED

    def __kill_scheduler(self) -> None:
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

    def __resume_scheduler(self) -> None:
        """Resumes scheduler

        Resumes scheduler if stopped. Otherwise does nothing.
        """
        self._envLogger.debug('Resuming scheduler. State: %s', self._envSchedulerState)
        if self._envSchedulerState == SchedState.STOPPED:
            for event in self._eventsOutOfQueue:
                self._envScheduler.enter(**event)

            self._eventsOutOfQueue.clear()
            self._envSchedulerState = SchedState.RUNNING
            self._envScheduler.run()
            self._envLogger.info('Scheduler resumed')
        else:
            self._envLogger.warning('Scheduler is not paused. Can\'t resume')

    def __update_config_section(self, section_name: str, option: str, val: any) -> None:
        """Updates selected environment config section

        Args:
            section_name (str): Config section name
            option (str): Option name to be updated
            val (any): New value
        """
        config = ConfigParser()
        self._envLogger.debug('Updating config section %s %s %s', section_name, option, val)

        if not config.read(filenames=self.__cfg_path):
            self._envLogger.error('Environment config file not found')
            raise FileNotFoundError('Environment config file not found')

        config[section_name][option] = str(val)
        try:
            cfg_file = open(file=self.__cfg_path, mode='w')
            config.write(fp=cfg_file)
            cfg_file.close()
        except IOError:
            self._envLogger.error('Couldn\'t write config to file')
            raise Exception('Couldn\'t write config to file')
