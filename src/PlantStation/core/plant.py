import datetime
import time
from datetime import timedelta, datetime

from gpiozero import DigitalOutputDevice, GPIOZeroError

from .helpers.format_validators import is_gpio
from .config import EnvironmentConfig

DEFAULT_INTERVAL = timedelta(seconds=300)


class Plant:
    """Representation of a plant

    Allows to water on/off plant or check is it right moment to water plant

    Attributes:
    -----------

    plantName  : str
        Name of the plant

    Methods:
    --------

    water_on()
        Turns on pump and returns Event kwargs

    water_off()
        Turns off pump, returns Event kwargs and config changes kwargs

    should_water()
        Checks if it is right time to water now, returns appropriate actions to do in kwargs (new scheduler event)
    """
    plantName: str
    _gpioPinNumber: str
    wateringDuration: timedelta
    wateringInterval: timedelta
    _lastTimeWatered: datetime
    envConfig: EnvironmentConfig
    _pumpSwitch: DigitalOutputDevice
    DEFAULT_INTERVAL: timedelta = DEFAULT_INTERVAL

    def __init__(self, plantName: str, envConfig: EnvironmentConfig, gpioPinNumber: str, wateringDuration: timedelta,
                 wateringInterval: timedelta, lastTimeWatered: datetime = datetime.min):
        """
        Args:
            plantName (str): Plant name
            gpioPinNumber (str): GPIO number, either BOARDXX or GPIOXX where
                XX is a pin number
            lastTimeWatered (datetime): When plant was watered last time?
            wateringDuration (timedelta): How long should the plant be watered?
            wateringInterval (timedelta): Time between watering
        """
        if datetime.now() < lastTimeWatered:
            raise ValueError('Last time watered is in future')
        if not timedelta() < wateringDuration:
            raise ValueError("Watering duration is negative or equal to 0")
        if not is_gpio(gpioPinNumber):
            raise ValueError('Wrong GPIO value')

        self.plantName = plantName
        self.envConfig = envConfig
        self._lastTimeWatered: datetime.datetime = lastTimeWatered
        self.wateringDuration = wateringDuration
        self.wateringInterval = wateringInterval
        self._gpioPinNumber = gpioPinNumber

        try:
            self._pumpSwitch = DigitalOutputDevice(gpioPinNumber, active_high=False,
                                                   pin_factory=self.envConfig.pin_factory)
        except GPIOZeroError as exc:
            self.envConfig.logger.error(f'Plant {plantName}: Couldn\'t set up gpio pin: {self._gpioPinNumber}')
            raise exc

        self.envConfig.logger.debug(
            f'{self.plantName}: Creating successful. Last time watered: {self._lastTimeWatered}. Interval: {self.wateringInterval}. Pin: {self._gpioPinNumber}')

    def water(self):
        """
            Waters plant
        """
        try:
            self.envConfig.logger.info(f'{self.plantName}: Started watering')
            self.envConfig.pump_lock.acquire()
            self._pumpSwitch.on()
            time.sleep(self.wateringDuration.total_seconds())
        except GPIOZeroError as exc:
            self.envConfig.logger.error(f'{self.plantName}: GPIO error')
            raise exc
        finally:
            self._pumpSwitch.off()
            self._lastTimeWatered = datetime.now()
            self.envConfig.logger.info(f'{self.plantName}: Stopped watering')

    def should_water(self):
        """Checks if it is right to water plant now

        Returns:
            * *Returns appropriate Event kwargs if it is right to water now*
            * *Either returns water_on event or should_water after DEFAULT_INTERVAL*
        """
        self.envConfig.logger.debug(
            f'Time now: {datetime.now()}. Planned watering: {self._lastTimeWatered + self.wateringInterval}')
        if datetime.now() >= self._lastTimeWatered + self.wateringInterval:
            self.envConfig.logger.info("%s: It's right to water me now!", self.plantName)
            return True
        else:
            self.envConfig.logger.info("%s: Give me some time, water me later", self.plantName)
            return False

    def calc_next_watering(self) -> datetime:
        """Calculate next watering date

        :return: watering datetime
        """
        return self._lastTimeWatered + self.wateringInterval
