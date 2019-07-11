from datetime import timedelta, datetime
from gpiozero import DigitalOutputDevice
from sched import scheduler
from configparser import ConfigParser
from helpers import strToTimedelta
from enum import Enum, auto


CONFIGFILE_DEFAULT_PATH='enviroment.cfg'

class SCHED_PRIORITY_TABLE(Enum):
    #priority low to high
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
    gpioPinNumber: int
    wateringDuration: timedelta
    wateringInterval: timedelta
    lastTimeWatered: datetime.min
    pumpSwitch: DigitalOutputDevice
    plantEnviroment: Enviroment


    def __init__ (self, plantName: str, gpioPinNumber: int, wateringDuration: timedelta, wateringInterval: timedelta, enviroment: Enviroment):
        self.plantName = plantName
        self.wateringDuration = wateringDuration
        self.wateringInterval = wateringInterval
        self.gpioPinNumber = gpioPinNumber
        self.plantEnviroment = enviroment
        try:
            self.pumpSwitch = DigitalOutputDevice("BOARD" + str(gpioPinNumber), active_high=False, initial_value=True)
        except:
            raise Exception("Couldn't set up gpio pin")

    def waterOff(self):
        self.pumpSwitch.off()
        self.lastTimeWatered = datetime.now()
        self.plantEnviroment.envScheduler.enter(delay= self.wateringInterval, priority= SCHED_PRIORITY_TABLE.isItRigthToWaterNow, action= self.isItRigthToWaterNow())

    def waterOn (self):
        self.pumpSwitch.on()
        self.plantEnviroment.envScheduler.enter(delay= self.wateringDuration, priority= SCHED_PRIORITY_TABLE.waterOff, action= self.waterOff())

    def isItRigthToWaterNow (self):
        if datetime.now() - self.lastTimeWatered >= self.wateringInterval:
            #sched water
            self.plantEnviroment.envScheduler.enter(delay= 0, priority= SCHED_PRIORITY_TABLE.waterOn, action= self.waterOn())
        else:
            self.plantEnviroment.envScheduler.enter(delay= DEFAULT_INTERVAL, priority= SCHED_PRIORITY_TABLE.isItRightToWaterNow, action= self.isItRigthToWaterNow())




class Enviroment:
    """docstring for Enviroment."""
    plants = []
    envScheduler = scheduler()
    envSchedulerState = SCHED_STATE.UNSET
    eventsOutOfQueue = []

    def __init__(self, cfg_path: str):
        self.readConfig(cfg_path)
        self.start()



    def readConfig(self, cfg_path= CONFIGFILE_DEFAULT_PATH):
        config = ConfigParser()
        config.read(filenames= cfg_path)

        #read global section
        global globalConfigSection
        globalConfigSection = config['GLOBAL']

        DEFAULT_INTERVAL = globalConfigSection['DEFAULT_INTERVAL']

        #read plants
        for section in config:
            if section != 'GLOBAL':

                newPlant: Plant

                params = {}

                uniqueName = str(section.name)
                params['plantName'] = str(section['plantName'])
                params['wateringDuration'] = timedelta(seconds= section['wateringDuration'])
                params['wateringInterval'] = strToTimedelta.parse(time_str= section['wateringInterval'])
                params['lastTimeWatered'] = datetime.strptime(date_string= section['lastTimeWatered'], format= '%Y-%m-%d %H:%M%:%S')
                params['gpioPinNumber'] = int(section['gpioPinNumber'])

                newPlant = Plant(**params)

                self.plants.append(newPlant)


    def scheduleMonitoring(self):
        for plant in self.plants:
            plant.isItRigthToWaterNow()
        self.envSchedulerState = SCHED_STATE.STOPPED

    def start(self):
        if self.envSchedulerState == SCHED_STATE.STOPPED:
            self.envScheduler.run()

    def stop(self):
        if self.envSchedulerState in [SCHED_STATE.RUNNING, SCHED_STATE.PAUSED]:
            self.envScheduler.enter(delay= 0, priority= SCHED_PRIORITY_TABLE.SCHED_STOP, action= self.__stopScheduler())

    #in development
    def __stopScheduler(self):
        for event in self.envScheduler.queue:
            if event.action == Plant.waterOff:
                event.action()
            self.eventsOutOfQueue.append(event)
            self.envScheduler.cancel(event)

    #in development
    def __resumeScheduler(self):
        for event in self.eventsOutOfQueue:
            self.envScheduler.enter(**event)

        self.eventsOutOfQueue.clear()



