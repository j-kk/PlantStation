import datetime
import logging
from datetime import timedelta, datetime

from gpiozero import DigitalOutputDevice, GPIOZeroError
from gpiozero.pins import mock, native

from PlantStation.helpers.format_validators import is_gpio

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
    _pumpSwitch: DigitalOutputDevice
    _plantLogger: logging.Logger
    _dryRun: bool
    DEFAULT_INTERVAL: timedelta = DEFAULT_INTERVAL

    def __init__(self, plantName: str, envName: str, gpioPinNumber: str, wateringDuration: timedelta,
                 wateringInterval: timedelta, lastTimeWatered: datetime = datetime.min,
                 dry_run: bool = False):
        """
        Args:
            plantName (str): Plant name
            gpioPinNumber (str): GPIO number, either BOARDXX or GPIOXX where
                XX is a pin number
            lastTimeWatered (datetime): When plant was watered last time?
            wateringDuration (timedelta): How long should the plant be watered?
            wateringInterval (timedelta): Time between watering
            envName (str): Environment name
            dry_run (bool): Dry run - don't interfere with GPIO pins etc.
        """
        if datetime.now() < lastTimeWatered:
            raise ValueError('Last time watered is in future')
        if not timedelta() < wateringDuration:
            raise ValueError("Watering duration is negative or equal to 0")
        if not is_gpio(gpioPinNumber):
            raise ValueError('Wrong GPIO value')

        self.plantName = plantName
        self._lastTimeWatered: datetime.datetime = lastTimeWatered
        self.wateringDuration = wateringDuration
        self.wateringInterval = wateringInterval
        self._gpioPinNumber = gpioPinNumber
        self._plantLogger = logging.getLogger(__package__ + "." + envName + "." + plantName)
        self._dryRun = dry_run
        try:
            if dry_run:
                self._pumpSwitch = DigitalOutputDevice(gpioPinNumber, active_high=False,
                                                       pin_factory=mock.MockFactory())
            else:
                self._pumpSwitch = DigitalOutputDevice(gpioPinNumber, active_high=False,
                                                       pin_factory=native.NativeFactory())
        except GPIOZeroError as exc:
            self._plantLogger.error("Plant %s: Couldn't set up gpio pin: %s", self.plantName, self._gpioPinNumber)
            raise exc

        self._plantLogger.debug(
            f'Creating successful. Last time watered: {self._lastTimeWatered}. Interval: {self.wateringInterval}. Pin: {self._gpioPinNumber}')

    def water_on(self) -> None:
        """Turns on pump and return Event kwargs
        """
        try:
            self._plantLogger.info("%s: Started watering", self.plantName)
            if not self._dryRun:
                self._pumpSwitch.on()
        except GPIOZeroError as exc:
            self._plantLogger.error("%s: GPIO error", self.plantName)
            raise exc

    def water_off(self) -> None:
        """Turns off pump, returns Event kwargs and config changes kwargs
        """
        try:
            self._plantLogger.info("%s: Stopping watering", self.plantName)
            if not self._dryRun:
                self._pumpSwitch.off()
            self._lastTimeWatered = datetime.now()
        except GPIOZeroError as exc:
            self._plantLogger.error(f'{self.plantName}: GPIO error: {exc}')
            raise exc
        except Exception as exc:
            self._plantLogger.error(f'{self.plantName}: Other error: {exc}')
            raise exc

    def should_water(self):
        """Checks if it is right to water plant now

        Returns:
            * *Returns appropriate Event kwargs if it is right to water now*
            * *Either returns water_on event or should_water after DEFAULT_INTERVAL*
        """
        self._plantLogger.debug(
            f'Time now: {datetime.now()}. Planned watering: {self._lastTimeWatered + self.wateringInterval}')
        if datetime.now() >= self._lastTimeWatered + self.wateringInterval:
            self._plantLogger.info("%s: It's right to water me now!", self.plantName)
            return True
        else:
            self._plantLogger.info("%s: Give me some time, water me later", self.plantName)
            return False

    def calc_next_watering(self) -> datetime:
        """Calculate next watering date

        :return: watering datetime
        """
        return self._lastTimeWatered + self.wateringInterval
