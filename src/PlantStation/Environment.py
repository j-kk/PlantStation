import logging
from configparser import ConfigParser
from datetime import timedelta, datetime
from sched import scheduler
from typing import Callable

from PlantStation.Plant import Plant
from PlantStation.helpers import format_validators
from PlantStation.helpers.sched_states import SchedState, SchedPriorityTable

CONFIGFILE_DEFAULT_PATH = 'environment.cfg'


class Environment:
    """docstring for Environment."""
    name: str
    plants = [Plant]
    envScheduler = scheduler()
    envSchedulerState = SchedState.UNSET
    eventsOutOfQueue = []
    cfg_path: str
    envLogger: logging.Logger

    def __init__(self, name: str = "main"):
        self.cfg_path = CONFIGFILE_DEFAULT_PATH

        self.name = name
        self.read_config()
        self.envLogger = logging.getLogger(__package__ + "." + name)
        self.envLogger.info('Created %s environment')
        self.start()

    def read_config(self):
        config = ConfigParser()
        if not config.read(filenames=self.cfg_path):
            self.envLogger.critical('Config file %s not found', CONFIGFILE_DEFAULT_PATH)
            raise FileNotFoundError('Error: environment config file not found. Quitting!')

        # read global section
        self.envLogger.info('Reading config file: %s', CONFIGFILE_DEFAULT_PATH)
        global globalConfigSection
        globalConfigSection = config['GLOBAL']

        global DEFAULT_INTERVAL
        try:
            DEFAULT_INTERVAL = int(globalConfigSection['DEFAULT_INTERVAL'])
            self.envLogger.info('DEFAULT_INTERVAL set to %d s', DEFAULT_INTERVAL)
        except KeyError:
            self.envLogger.warning('Warning: DEFAULT_INTERVAL unset. Setting to 300s')
        except ValueError:
            self.envLogger.critical('Error: DEFAULT_INTERVAL value is not a number. Quitting!')
            raise ValueError('Error: DEFAULT_INTERVAL value is not a number. Quitting!')

        # read plants
        for section in config:
            if section != 'GLOBAL':
                section_name = section.name
                self.envLogger.debug('Found new section: %s', section_name)
                try:
                    format_validators.is_gpio(str(section_name['gpioPinNumber']))

                    params = {'plantName': str(section.name),
                              'wateringDuration': timedelta(seconds=int(section['wateringDuration'])),
                              'wateringInterval': format_validators.datetime_regex(
                                  time_str=section['wateringInterval']),
                              'lastTimeWatered': datetime.strptime(date_string=section['lastTimeWatered'],
                                                                   format='%Y-%m-%d %H:%M%:%S'),
                              'gpioPinNumber': str(section['gpioPinNumber'])}

                    new_plant = Plant(**params, env_name= self.name)
                    self.envLogger.info('Found new plant: %s, pin: %s', params['plantName'], params['gpioPinNumber'])
                    self.plants.append(new_plant)
                except KeyError as err:
                    self.envLogger.warning('%s: Failed to read %s section - option not found ', CONFIGFILE_DEFAULT_PATH,
                                           section_name, str(err))
                except ValueError:
                    self.envLogger.warning('%s: Failed to read %s section - wrong argument value',
                                           CONFIGFILE_DEFAULT_PATH, section_name)
                except Exception as err:
                    self.envLogger.warning('%s: Failed to read %s section %s', CONFIGFILE_DEFAULT_PATH, section_name,
                                           str(err))

    def schedule_monitoring(self):
        self.envLogger.debug('Scheduling monitoring')
        for plant in self.plants:
            self.__handle_sched_action(plant.should_water)
        self.envLogger.debug('Scheduler state : STOPPED')
        self.envSchedulerState = SchedState.STOPPED

    def start(self):
        self.envLogger.debug('Starting scheduler. State: %s', self.envSchedulerState)
        if self.envSchedulerState == SchedState.STOPPED:
            self.envLogger.info('Starting scheduler')
            self.__resume_scheduler()

    def stop(self):
        self.envLogger.debug('Stopping scheduler. State: %s', self.envSchedulerState)
        if self.envSchedulerState == SchedState.RUNNING:
            self.envSchedulerState = SchedState.PAUSED
            self.envLogger.info('Pausing scheduler.')
            self.envScheduler.enter(delay=0, priority=SchedPriorityTable.SCHED_STOP, action=self.__stop_scheduler())

    def __handle_sched_action(self, func: Callable[[None], any]) -> {}:
        try:
            self.envLogger.debug('Handling function')
            params: {} = func(None)

            self.envLogger.debug('Handler: Got params: %s', params)

            if 'config_params' in params:
                self.__update_config_section(**params['config_params'])

            if 'sched_params' in params:
                self.__add_to_scheduler(**params['sched_params'])

        except Exception as err:
            self.envLogger.critical('Handler received exception. Killing scheduler.')
            self.envScheduler.enter(delay=0, priority=SchedPriorityTable.SCHED_STOP,
                                    action=self.__kill_scheduler())
            raise err

    def __add_to_scheduler(self, params):
        if self.envSchedulerState in [SchedState.STOPPED, SchedState.PAUSED]:
            self.eventsOutOfQueue.append(params)
        elif self.envSchedulerState in [SchedState.UNSET, SchedState.RUNNING]:
            self.envScheduler.enter(**params)

    def __stop_scheduler(self):
        self.envLogger.info('Stopping scheduler. State: %s', self.envSchedulerState)
        for event in self.envScheduler.queue:
            if event.action == Plant.water_off:
                self.envLogger.info('Calling Plant.water_off forced')
                event.action()
            else:
                self.eventsOutOfQueue.append(event)
            self.envScheduler.cancel(event)
        self.envSchedulerState = SchedState.STOPPED

    def __kill_scheduler(self):
        self.envLogger.info('Killing scheduler. State: %s', self.envSchedulerState)
        self.envSchedulerState = SchedState.KILLED
        for event in self.envScheduler.queue:
            if event.action == Plant.water_off:
                event.action()
            self.envScheduler.cancel(event)

    def __resume_scheduler(self):
        self.envLogger.info('Resuming scheduler. State: %s', self.envSchedulerState)
        for event in self.eventsOutOfQueue:
            self.envScheduler.enter(**event)

        self.eventsOutOfQueue.clear()
        self.envSchedulerState = SchedState.RUNNING
        self.envScheduler.run()

    def __update_config_section(self, section_name: str, option: str, val):
        config = ConfigParser()
        self.envLogger.debug('Updating config section %s %s %s', section_name, option, val)

        if not config.read(filenames=self.cfg_path):
            self.envLogger.error('Environment config file not found')
            raise FileNotFoundError('Environment config file not found')

        config[section_name][option] = str(val)
        try:
            cfg_file = open(file=self.cfg_path, mode='w')
            config.write(fp=cfg_file)
            cfg_file.close()
        except IOError:
            self.envLogger.error('Couldn\'t write config to file')
            raise Exception('Couldn\'t write config to file')
