import datetime
import logging
import threading
import time
from datetime import timedelta, datetime
from gpiozero import DigitalOutputDevice, GPIOZeroError

from .helpers.format_validators import is_gpio
from .config import EnvironmentConfig


class Plant:
    """Representation of a plant

    Stores basic information about plant.

    Attributes:
    -----------

    plantName  : str
        Name of the plant


    Methods:
    --------

    water()
        Waters plant. Obtains pump lock (EnvironmentConfig specifies max number of simultanously working pumps).
        Blocks thread until plant is watered

    should_water()
        Checks if it is right time to water now, returns appropriate actions to do in kwargs (new scheduler event)
    """
    _plantName: str
    _wateringDuration: timedelta
    _wateringInterval: timedelta
    _lastTimeWatered: datetime

    _envConfig: EnvironmentConfig
    _logger: logging.Logger
    _gpioPinNumber: str
    _pumpSwitch: DigitalOutputDevice
    _relatedTask = None

    _infoLock = threading.Lock()

    def __init__(self, plantName: str, envConfig: EnvironmentConfig, gpioPinNumber: str, wateringDuration: timedelta,
                 wateringInterval: timedelta, lastTimeWatered: datetime = datetime.min):
        """
        Args:
            plantName (str): Plant name
            envConfig (EnvironmentConfig): Environment configuration
            gpioPinNumber (str): GPIO number, either BOARDXX or GPIOXX where
                XX is a pin number
            wateringDuration (timedelta): How long should the plant be watered?
            wateringInterval (timedelta): Time between watering
            lastTimeWatered (datetime): When plant was watered last time?
        """
        # Check if data is correct
        if datetime.now() < lastTimeWatered:
            raise ValueError('Last time watered is in future')
        if not timedelta() < wateringDuration:
            raise ValueError("Watering duration is negative or equal to 0")
        if not is_gpio(gpioPinNumber):
            raise ValueError('Wrong GPIO value')

        # set all attributes
        self._envConfig = envConfig

        self._plantName = plantName
        self._lastTimeWatered: datetime.datetime = lastTimeWatered
        self._wateringDuration = wateringDuration
        self._wateringInterval = wateringInterval

        self._gpioPinNumber = gpioPinNumber
        self._logger = self._envConfig.logger.getChild(self._plantName)

        # define pump
        try:
            self._pumpSwitch = DigitalOutputDevice(gpioPinNumber, active_high=False,
                                                   pin_factory=self._envConfig.pin_factory)
        except GPIOZeroError as exc:
            self._envConfig.logger.error(f'Plant {plantName}: Couldn\'t set up gpio pin: {self._gpioPinNumber}')
            raise exc

        self._envConfig.logger.debug(
            f'{self._plantName}: Creating successful. Last time watered: {self._lastTimeWatered}. Interval: {self._wateringInterval}. Pin: {self._gpioPinNumber}')

    @property
    def plantName(self) -> str:
        """Plant's name

        """
        with self._infoLock:
            return self.plantName

    @plantName.setter
    def plantName(self, plantName: str) -> None:
        with self._infoLock:
            self.plantName = plantName

    @property
    def wateringDuration(self) -> timedelta:
        """Duration between waterings

        """
        with self._infoLock:
            return self.wateringDuration

    @wateringDuration.setter
    def wateringDuration(self, value: timedelta) -> None:
        with self._infoLock:
            self._wateringDuration = value

    @property
    def wateringInterval(self) -> timedelta:
        """Interval between waterings

        """
        with self._infoLock:
            return self._wateringInterval

    @wateringInterval.setter
    def wateringInterval(self, value: timedelta) -> None:
        with self._infoLock:
            self.wateringInterval = value

    @property
    def relatedTask(self):
        with self._infoLock:
            return self._relatedTask

    @relatedTask.setter
    def relatedTask(self, value):
        with self._infoLock:
            self._relatedTask = value

    def water(self) -> None:
        """
            Waters plant. Obtains pump lock (EnvironmentConfig specifies max number of simultanously working pumps).
            Blocks thread until plant is watered
        """
        try:
            self._logger.info(f'{self._plantName}: Started watering')
            self._envConfig.get_pump_lock()
            self._pumpSwitch.on()
            time.sleep(self.wateringDuration.total_seconds())
        except GPIOZeroError as exc:
            self._logger.error(f'{self._plantName}: GPIO error')
            raise exc
        finally:
            self._pumpSwitch.off()
            self._envConfig.release_pump_lock()
            self._lastTimeWatered = datetime.now()
            self._logger.info(f'{self._plantName}: Stopped watering')

    def should_water(self) -> bool:
        """Checks if it is right to water plant now

        """
        self._logger.debug(
            f'Time now: {datetime.now()}. Planned watering: {self._lastTimeWatered + self._wateringInterval}')
        if datetime.now() >= self._lastTimeWatered + self._wateringInterval:
            self._logger.info("%s: It's right to water me now!", self._plantName)
            return True
        else:
            self._logger.info("%s: Give me some time, water me later", self._plantName)
            return False

    def calc_next_watering(self) -> datetime:
        """Calculate next watering date

        :return: watering datetime
        """
        return self._lastTimeWatered + self._wateringInterval
