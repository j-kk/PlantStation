from datetime import timedelta, datetime
from gpiozero import DigitalOutputDevice, GPIOZeroError
from sched import scheduler
from configparser import ConfigParser
from helpers import strToTimedelta
from enum import Enum, auto

CONFIGFILE_DEFAULT_PATH = 'environment.cfg'


class SchedPriorityTable(Enum):
    # priority low to high
    waterOn = auto()
    isItRightToWaterNow = auto()
    SCHED_STOP = auto()
    waterOff = auto()


class SchedState(Enum):
    RUNNING = ()
    PAUSED = ()
    STOPPED = ()
    UNSET = ()


DEFAULT_INTERVAL = 300


class Plant:
    plantName = ''
    gpioPinNumber: str
    wateringDuration: timedelta
    wateringInterval: timedelta
    lastTimeWatered: datetime.min
    pumpSwitch: DigitalOutputDevice
    plantEnvironment: None  # TODO typing - Environment
    global DEFAULT_INTERVAL

    def __init__(self, plant_name: str, gpio_pin_number: str, watering_duration: timedelta,
                 watering_interval: timedelta,
                 environment: None):
        self.plantName = plant_name
        self.wateringDuration = watering_duration
        self.wateringInterval = watering_interval
        self.gpioPinNumber = gpio_pin_number
        self.plantEnvironment = environment
        try:
            self.pumpSwitch = DigitalOutputDevice(gpio_pin_number, active_high=False, initial_value=True)
        except GPIOZeroError:
            raise Exception("Error: Couldn't set up gpio pin. Quitting!")

    def water_off(self):
        try:
            self.pumpSwitch.off()
            self.lastTimeWatered = datetime.now()
            self.plantEnvironment.updateConfigSection(sectionName=self.plantName, option='lastTimeWatered',
                                                      val=self.lastTimeWatered)
            self.plantEnvironment.envScheduler.enter(delay=self.wateringInterval,
                                                     priority=SchedPriorityTable.isItRigthToWaterNow,
                                                     action=self.should_water())
        except GPIOZeroError:
            self.plantEnvironment.envScheduler.enter(delay=0, priority=SchedPriorityTable.SCHED_STOP,
                                                     action=self.plantEnvironment.killScheduler())
            raise Exception('ERROR: GPIO error. Quitting!')
        except Exception as err:
            self.plantEnvironment.envScheduler.enter(delay=0, priority=SchedPriorityTable.SCHED_STOP,
                                                     action=self.plantEnvironment.killScheduler())
            raise err

    def water_on(self):
        try:
            self.pumpSwitch.on()
            self.plantEnvironment.envScheduler.enter(delay=self.wateringDuration,
                                                     priority=SchedPriorityTable.waterOff,
                                                     action=self.water_off())
        except GPIOZeroError:
            self.plantEnvironment.envScheduler.enter(delay=0, priority=SchedPriorityTable.SCHED_STOP,
                                                     action=self.plantEnvironment.killScheduler())
            raise Exception('ERROR: GPIO error. Quitting!')

    def should_water(self):
        if datetime.now() - self.lastTimeWatered >= self.wateringInterval:
            # sched water
            self.plantEnvironment.envScheduler.enter(delay=0, priority=SchedPriorityTable.waterOn,
                                                     action=self.water_on())
        else:
            self.plantEnvironment.envScheduler.enter(delay=DEFAULT_INTERVAL,
                                                     priority=SchedPriorityTable.isItRightToWaterNow,
                                                     action=self.should_water())


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
            raise Exception('Error: environment.cfg file not found. Quitting!')

        # read global section
        global globalConfigSection
        globalConfigSection = config['GLOBAL']

        global DEFAULT_INTERVAL
        try:
            DEFAULT_INTERVAL = int(globalConfigSection['DEFAULT_INTERVAL'])
        except KeyError:
            print('Warning: DEFAULT_INTERVAL unset; setting to 300s')
        except ValueError:
            raise Exception('Error: DEFAULT_INTERVAL value is not a number. Quitting!')

        # read plants
        for section in config:
            if section != 'GLOBAL':
                section_name = section.name
                try:
                    params = {'plantName': str(section.name),
                              'wateringDuration': timedelta(seconds=int(section['wateringDuration'])),
                              'wateringInterval': strToTimedelta.parse(time_str=section['wateringInterval']),
                              'lastTimeWatered': datetime.strptime(date_string=section['lastTimeWatered'],
                                                                   format='%Y-%m-%d %H:%M%:%S'),
                              'gpioPinNumber': str(section['gpioPinNumber'])}  # TODO regex

                    new_plant = Plant(**params)

                    self.plants.append(new_plant)
                except KeyError as err:
                    print(
                        'Warning: environment.cfg: Failed to read ' + section_name + 'section - option not found ' + str(
                            err))
                except ValueError:
                    print('Warning: environment.cfg: Failed to read ' + section_name + 'section - wrong argument value')
                except Exception as err:
                    print('Warning: environment.cfg: Failed to read ' + section_name + 'section' + str(err))

    def schedule_monitoring(self):
        for plant in self.plants:
            plant.should_water()
        self.envSchedulerState = SchedState.STOPPED

    def start(self):
        if self.envSchedulerState == SchedState.STOPPED:
            self.__resume_scheduler()

    def stop(self):
        if self.envSchedulerState == SchedState.RUNNING:
            self.envSchedulerState = SchedState.PAUSED
            self.envScheduler.enter(delay=0, priority=SchedPriorityTable.SCHED_STOP, action=self.__stop_scheduler())

    def __stop_scheduler(self):
        for event in self.envScheduler.queue:
            if event.action == Plant.water_off:
                event.action()
            self.eventsOutOfQueue.append(event)
            self.envScheduler.cancel(event)

        self.envSchedulerState = SchedState.STOPPED

    def kill_scheduler(self):
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

    def update_config_section(self, section_name: str, option: str, val):
        config = ConfigParser()

        if not config.read(filenames=self.cfg_path):
            raise FileNotFoundError('Error: Environment config file not found')

        config[section_name][option] = str(val)
        try:
            cfg_file = open(file=self.cfg_path, mode='w')
            config.write(fp=cfg_file)
        except IOError:
            raise Exception('Error: Couldn\'t write config to file')


mainEnvironment: Environment


def setup_env():
    global mainEnvironment
    mainEnvironment = Environment()
    mainEnvironment.read_config()
    mainEnvironment.schedule_monitoring()


def run_env():
    global mainEnvironment
    mainEnvironment.start()


def stop_env():
    global mainEnvironment
    mainEnvironment.stop()
