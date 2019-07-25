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
    plants = []
    envScheduler = scheduler()
    envSchedulerState = SchedState.UNSET
    eventsOutOfQueue = []
    cfg_path: str

    def __init__(self):
        self.cfg_path = CONFIGFILE_DEFAULT_PATH

        self.read_config()
        self.start()

    def read_config(self):
        config = ConfigParser()
        if not config.read(filenames=self.cfg_path):
            raise FileNotFoundError('Error: environment.cfg file not found. Quitting!')

        # read global section
        global globalConfigSection
        globalConfigSection = config['GLOBAL']

        global DEFAULT_INTERVAL
        try:
            DEFAULT_INTERVAL = int(globalConfigSection['DEFAULT_INTERVAL'])
        except KeyError:
            print('Warning: DEFAULT_INTERVAL unset; setting to 300s')
        except ValueError:
            raise ValueError('Error: DEFAULT_INTERVAL value is not a number. Quitting!')

        # read plants
        for section in config:
            if section != 'GLOBAL':
                section_name = section.name
                try:
                    format_validators.is_gpio(str(section_name['gpioPinNumber']))

                    params = {'plantName': str(section.name),
                              'wateringDuration': timedelta(seconds=int(section['wateringDuration'])),
                              'wateringInterval': format_validators.datetime_regex(
                                  time_str=section['wateringInterval']),
                              'lastTimeWatered': datetime.strptime(date_string=section['lastTimeWatered'],
                                                                   format='%Y-%m-%d %H:%M%:%S'),
                              'gpioPinNumber': str(section['gpioPinNumber'])}

                    new_plant = Plant(**params)

                    self.plants.append(new_plant)
                except KeyError as err:
                    print(
                        'Warning: environment.cfg: Failed to read ' + section_name + 'section - option not found '
                        + str(err))
                except ValueError:
                    print('Warning: environment.cfg: Failed to read ' + section_name + 'section - wrong argument value')
                except Exception as err:
                    print('Warning: environment.cfg: Failed to read ' + section_name + 'section' + str(err))

    def schedule_monitoring(self):
        for plant in self.plants:
            self.__handle_sched_action(plant.should_water())
        self.envSchedulerState = SchedState.STOPPED

    def start(self):
        if self.envSchedulerState == SchedState.STOPPED:
            self.__resume_scheduler()

    def stop(self):
        if self.envSchedulerState == SchedState.RUNNING:
            self.envSchedulerState = SchedState.PAUSED
            self.envScheduler.enter(delay=0, priority=SchedPriorityTable.SCHED_STOP, action=self.__stop_scheduler())

    def __handle_sched_action(self, func: Callable[[None], any]) -> {}:
        try:

            params: {} = func(None)

            if 'config_params' in params:
                self.__update_config_section(**params['config_params'])

            if 'sched_params' in params:
                self.envScheduler.enter(**params['sched_params'])

        except Exception as err:
            self.envScheduler.enter(delay=0, priority=SchedPriorityTable.SCHED_STOP,
                                    action=self.__kill_scheduler())
            raise err

    def __stop_scheduler(self):
        for event in self.envScheduler.queue:
            if event.action == Plant.water_off:
                event.action()
            self.eventsOutOfQueue.append(event)
            self.envScheduler.cancel(event)

        self.envSchedulerState = SchedState.STOPPED

    def __kill_scheduler(self):
        for event in self.envScheduler.queue:
            if event.action == Plant.water_off:
                event.action()
            self.envScheduler.cancel(event)

    def __resume_scheduler(self):
        for event in self.eventsOutOfQueue:
            self.envScheduler.enter(**event)

        self.eventsOutOfQueue.clear()
        self.envSchedulerState = SchedState.RUNNING
        self.envScheduler.run()

    def __update_config_section(self, section_name: str, option: str, val):
        config = ConfigParser()

        if not config.read(filenames=self.cfg_path):
            raise FileNotFoundError('Error: Environment config file not found')

        config[section_name][option] = str(val)
        try:
            cfg_file = open(file=self.cfg_path, mode='w')
            config.write(fp=cfg_file)
            cfg_file.close()
        except IOError:
            raise Exception('Error: Couldn\'t write config to file')
