import logging
from datetime import timedelta, datetime
from typing import Callable
from gpiozero import DigitalOutputDevice, GPIOZeroError
from PlantStation.helpers.sched_states import SchedPriorityTable



DEFAULT_INTERVAL = 300


class Plant:
    plantName = ''
    gpioPinNumber: str
    wateringDuration: timedelta
    wateringInterval: timedelta
    lastTimeWatered: datetime.min
    pumpSwitch: DigitalOutputDevice
    plantLogger: logging.Logger
    global DEFAULT_INTERVAL

    def __init__(self, plant_name: str, gpio_pin_number: str, watering_duration: timedelta,
                 watering_interval: timedelta, env_name: str):
        self.plantName = plant_name
        self.wateringDuration = watering_duration
        self.wateringInterval = watering_interval
        self.gpioPinNumber = gpio_pin_number
        self.plantLogger = logging.getLogger(__package__ + "." + env_name + "." + plant_name)
        try:
            self.pumpSwitch = DigitalOutputDevice(gpio_pin_number, active_high=False, initial_value=True)
        except GPIOZeroError:
            self.plantLogger.error("Plant %s: Couldn't set up gpio pin: %s", self.plantName, self.gpioPinNumber)
            raise Exception("Couldn't set up gpio pin. Quitting!")

    def water_on(self):
        try:
            self.plantLogger.info("%s: Started watering", self.plantName)
            self.pumpSwitch.on()
            params = {
                'sched_params': {
                    'delay': self.wateringDuration,
                    'priority': SchedPriorityTable.waterOff,
                    'action': self.water_off
                }
            }
            return params
        except GPIOZeroError:
            self.plantLogger.error("%s: GPIO error", self.plantName)
            raise Exception('GPIO error. Quitting!')

    def water_off(self, config_updater: Callable[[str, datetime], None]):
        try:
            self.plantLogger.info("%s: Stopping watering", self.plantName)
            self.pumpSwitch.off()
            self.lastTimeWatered = datetime.now()
            config_updater('lastTimeWatered', self.lastTimeWatered)
            params = {
                'sched_params': {
                    'delay': self.DEFAULT_INTERVAL,
                    'priority': SchedPriorityTable.should_water,
                    'action': self.should_water
                },

                'config_params': {
                    'section_name': self.plantName,
                    'option': 'lastTimeWatered',
                    'val': self.lastTimeWatered
                }
            }
            return params
        except GPIOZeroError:
            self.plantLogger.error("%s: GPIO error", self.plantName)
            raise Exception('ERROR: GPIO error. Quitting!')
        except Exception as err:
            self.plantLogger.error("%s: Other error", self.plantName)
            raise err

    def should_water(self):
        if datetime.now() - self.lastTimeWatered >= self.wateringInterval:
            self.plantLogger.info("%s: It's right to water me now!", self.plantName)
            params = {
                'sched_params': {
                    'delay': 0,
                    'priority': SchedPriorityTable.waterOn,
                    'action': self.water_on
                }
            }
        else:
            self.plantLogger.info("%s: Give me some time, water me later", self.plantName)
            params = {
                'sched_params': {
                    'delay': self.DEFAULT_INTERVAL,
                    'priority': SchedPriorityTable.should_water,
                    'action': self.should_water
                }
            }
        return params
