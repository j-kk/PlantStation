from datetime import timedelta, datetime
from gpiozero import DigitalOutputDevice, GPIOZeroError
from sched import scheduler
from configparser import ConfigParser
from helpers import strToTimedelta
from enum import Enum, auto

CONFIGFILE_DEFAULT_PATH = 'enviroment.cfg'


class SCHED_PRIORITY_TABLE(Enum):
    # priority low to high
    waterOn = auto()
    isItRightToWaterNow = auto()
    SCHED_STOP = auto()
    waterOff = auto()


class SCHED_STATE(Enum):
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
    plantEnviroment: None #TODO typing - Enviroment
    global DEFAULT_INTERVAL

    def __init__(self, plantName: str, gpioPinNumber: str, wateringDuration: timedelta, wateringInterval: timedelta,
                 enviroment: None):
        self.plantName = plantName
        self.wateringDuration = wateringDuration
        self.wateringInterval = wateringInterval
        self.gpioPinNumber = gpioPinNumber
        self.plantEnviroment = enviroment
        try:
            self.pumpSwitch = DigitalOutputDevice(gpioPinNumber, active_high=False, initial_value=True)
        except:
            raise Exception("Error: Couldn't set up gpio pin. Quitting!")

    def waterOff(self):
        try:
            self.pumpSwitch.off()
            self.lastTimeWatered = datetime.now()
            self.plantEnviroment.updateConfigSection(sectionName= self.plantName, option= 'lastTimeWatered', val= self.lastTimeWatered)
            self.plantEnviroment.envScheduler.enter(delay= self.wateringInterval,
                                                    priority= SCHED_PRIORITY_TABLE.isItRigthToWaterNow,
                                                    action= self.isItRigthToWaterNow())
        except GPIOZeroError:
            self.plantEnviroment.envScheduler.enter(delay= 0, priority= SCHED_PRIORITY_TABLE.SCHED_STOP, action= self.plantEnviroment.killScheduler())
            raise Exception('ERROR: GPIO error. Quitting!')
        except Exception as err:
            self.plantEnviroment.envScheduler.enter(delay= 0, priority= SCHED_PRIORITY_TABLE.SCHED_STOP, action= self.plantEnviroment.killScheduler())
            raise err


    def waterOn(self):
        try:
            self.pumpSwitch.on()
            self.plantEnviroment.envScheduler.enter(delay= self.wateringDuration, priority= SCHED_PRIORITY_TABLE.waterOff,
                                                    action= self.waterOff())
        except GPIOZeroError:
            self.plantEnviroment.envScheduler.enter(delay= 0, priority= SCHED_PRIORITY_TABLE.SCHED_STOP, action= self.plantEnviroment.killScheduler())
            raise Exception('ERROR: GPIO error. Quitting!')


    def isItRigthToWaterNow(self):
        if datetime.now() - self.lastTimeWatered >= self.wateringInterval:
            # sched water
            self.plantEnviroment.envScheduler.enter(delay=0, priority=SCHED_PRIORITY_TABLE.waterOn,
                                                    action=self.waterOn())
        else:
            self.plantEnviroment.envScheduler.enter(delay=DEFAULT_INTERVAL,
                                                    priority=SCHED_PRIORITY_TABLE.isItRightToWaterNow,
                                                    action=self.isItRigthToWaterNow())



class Enviroment:
    """docstring for Enviroment."""
    plants = []
    envScheduler = scheduler()
    envSchedulerState = SCHED_STATE.UNSET
    eventsOutOfQueue = []
    cfg_path: str

    def __init__(self, cfg_path = CONFIGFILE_DEFAULT_PATH):
        self.cfg_path = cfg_path

        self.readConfig()
        self.start()

    def readConfig(self):
        config = ConfigParser()
        if not config.read(filenames= self.cfg_path):
            raise Exception('Error: enviroment.cfg file not found. Quitting!')

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
                sectionName = section.name
                try:
                    params = {}

                    params['plantName'] = str(section.name)
                    params['wateringDuration'] = timedelta(seconds= int(section['wateringDuration']))
                    params['wateringInterval'] = strToTimedelta.parse(time_str= section['wateringInterval'])
                    params['lastTimeWatered'] = datetime.strptime(date_string=section['lastTimeWatered'],
                                                                  format='%Y-%m-%d %H:%M%:%S')
                    params['gpioPinNumber'] = str(section['gpioPinNumber'])

                    newPlant = Plant(**params)

                    self.plants.append(newPlant)
                except KeyError as err:
                    print('Warning: enviroment.cfg: Failed to read ' + sectionName + 'section - option not found ' + str(err))
                except ValueError:
                    print('Warning: enviroment.cfg: Failed to read ' + sectionName + 'section - wrong argument value' )
                except Exception as err:
                    print('Warning: enviroment.cfg: Failed to read ' + sectionName + 'section' + str(err))



    def schedule_monitoring(self):
        for plant in self.plants:
            plant.isItRigthToWaterNow()
        self.envSchedulerState = SCHED_STATE.STOPPED

    def start(self):
        if self.envSchedulerState == SCHED_STATE.STOPPED:
            self.__resumeScheduler()

    def stop(self):
        if self.envSchedulerState == SCHED_STATE.RUNNING:
            self.envSchedulerState = SCHED_STATE.PAUSED
            self.envScheduler.enter(delay=0, priority=SCHED_PRIORITY_TABLE.SCHED_STOP, action=self.__stopScheduler())

    def __stopScheduler(self):
        for event in self.envScheduler.queue:
            if event.action == Plant.waterOff:
                event.action()
            self.eventsOutOfQueue.append(event)
            self.envScheduler.cancel(event)

        self.envSchedulerState = SCHED_STATE.STOPPED

    def killScheduler(self):
        for event in self.envScheduler.queue:
            if event.action == Plant.waterOff:
                event.action()
            self.envScheduler.cancel(event)

    def __resumeScheduler(self):
        for event in self.eventsOutOfQueue:
            self.envScheduler.enter(**event)

        self.eventsOutOfQueue.clear()
        self.envSchedulerState = SCHED_STATE.RUNNING
        self.envScheduler.run()

    def updateConfigSection(self, sectionName: str, option: str, val):
        config = ConfigParser()

        if not config.read(filenames= self.cfg_path):
            raise FileNotFoundError('Error: Enviroment config file not found')

        config[sectionName][option] = str(val)
        try:
            cfg_file = open(file= self.cfg_path, mode= 'w')
            config.write(fp= cfg_file)
        except:

            raise Exception('Error: Couldn\'t write config to file')

