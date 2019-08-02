import logging
import datetime
from datetime import timedelta, datetime
from gpiozero import DigitalOutputDevice, GPIOZeroError
from PlantStation.helpers.sched_states import SchedPriorityTable
from PlantStation.helpers.format_validators import is_gpio
from PlantStation.Environment import DEFAULT_INTERVAL


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
    _wateringDuration: timedelta
    _wateringInterval: timedelta
    _lastTimeWatered: datetime
    _pumpSwitch: DigitalOutputDevice
    _plantLogger: logging.Logger
    __dryRun: bool

    def __init__(self, plant_name: str, env_name: str, gpio_pin_number: str, watering_duration: timedelta,
                 watering_interval: timedelta = DEFAULT_INTERVAL, last_time_watered: datetime = datetime.min,
                 dry_run: bool = False):
        """
        Args:
            plant_name (str): Plant name
            gpio_pin_number (str): GPIO number, either BOARDXX or GPIOXX where
                XX is a pin number
            last_time_watered (datetime): When plant was watered last time?
            watering_duration (timedelta): How long should the plant be watered?
            watering_interval (timedelta): Time between watering
            env_name (str): Environment name
            dry_run (bool): Dry run - don't interfere with GPIO pins etc.
        """
        if last_time_watered < datetime.now():
            raise ValueError('Last time watered is in future')
        if not datetime.timedelta() < watering_duration:
            raise ValueError("Watering duration is negative or equal to 0")
        if not datetime.timedelta() < watering_interval:
            raise ValueError("Watering interval is negative or equal to 0")
        if not is_gpio(gpio_pin_number):
            raise ValueError('Wrong GPIO value')

        self.plantName = plant_name
        self._lastTimeWatered = last_time_watered
        self._wateringDuration = watering_duration
        self._wateringInterval = watering_interval
        self._gpioPinNumber = gpio_pin_number
        self._plantLogger = logging.getLogger(__package__ + "." + env_name + "." + plant_name)
        self.__dryRun = dry_run
        if not dry_run:
            try:
                self.pumpSwitch = DigitalOutputDevice(gpio_pin_number, active_high=False, initial_value=True)
            except GPIOZeroError:
                self._plantLogger.error("Plant %s: Couldn't set up gpio pin: %s", self.plantName, self._gpioPinNumber)
                raise Exception("Couldn't set up gpio pin. Quitting!")

    def water_on(self):
        """Turns on pump and return Event kwargs

        Returns:
            {}: **kwargs** -- Event kwargs
        """
        try:
            self._plantLogger.info("%s: Started watering", self.plantName)
            if not self.__dryRun:
                self.pumpSwitch.on()
            params = {
                'sched_params': {
                    'delay': self._wateringDuration,
                    'priority': SchedPriorityTable.waterOff,
                    'action': self.water_off
                }
            }
            return params
        except GPIOZeroError:
            self._plantLogger.error("%s: GPIO error", self.plantName)
            raise Exception('GPIO error. Quitting!')

    def water_off(self):
        """Turns off pump, returns Event kwargs and config changes kwargs

        Returns:
            {}: **kwargs** -- Event kwargs and config changes kwargs
        """
        try:
            self._plantLogger.info("%s: Stopping watering", self.plantName)
            if not self.__dryRun:
                self.pumpSwitch.off()
            self._lastTimeWatered = datetime.now()
            params = {
                'sched_params': {
                    'delay': self._wateringInterval,
                    'priority': SchedPriorityTable.should_water,
                    'action': self.should_water
                },

                'config_params': {
                    'section_name': self.plantName,
                    'option': 'lastTimeWatered',
                    'val': self._lastTimeWatered
                }
            }
            return params
        except GPIOZeroError:
            self._plantLogger.error("%s: GPIO error", self.plantName)
            raise Exception('ERROR: GPIO error. Quitting!')
        except Exception as err:
            self._plantLogger.error("%s: Other error", self.plantName)
            raise err

    def should_water(self):
        """Checks if it is right to water plant now

        Returns:
            * *Returns appropriate Event kwargs if it is right to water now*
            * *Either returns water_on event or should_water after DEFAULT_INTERVAL*
        """
        if datetime.now() - self._lastTimeWatered >= self._wateringInterval:
            self._plantLogger.info("%s: It's right to water me now!", self.plantName)
            params = {
                'sched_params': {
                    'delay': 0,
                    'priority': SchedPriorityTable.waterOn,
                    'action': self.water_on
                }
            }
        else:
            self._plantLogger.info("%s: Give me some time, water me later", self.plantName)
            params = {
                'sched_params': {
                    'delay': DEFAULT_INTERVAL,
                    'priority': SchedPriorityTable.should_water,
                    'action': self.should_water
                }
            }
        return params
