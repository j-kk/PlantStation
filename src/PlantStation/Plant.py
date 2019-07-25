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
    global DEFAULT_INTERVAL

    def __init__(self, plant_name: str, gpio_pin_number: str, watering_duration: timedelta,
                 watering_interval: timedelta):
        self.plantName = plant_name
        self.wateringDuration = watering_duration
        self.wateringInterval = watering_interval
        self.gpioPinNumber = gpio_pin_number
        try:
            self.pumpSwitch = DigitalOutputDevice(gpio_pin_number, active_high=False, initial_value=True)
        except GPIOZeroError:
            raise Exception("Error: Couldn't set up gpio pin. Quitting!")

    def water_off(self, config_updater: Callable[[str, datetime], None]):
        try:
            self.pumpSwitch.off()
            self.lastTimeWatered = datetime.now()
            config_updater('lastTimeWatered', self.lastTimeWatered)  # TODO logs
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
            raise Exception('ERROR: GPIO error. Quitting!')
        except Exception as err:
            raise err

    def water_on(self):
        try:
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
            raise Exception('ERROR: GPIO error. Quitting!')

    def should_water(self):
        if datetime.now() - self.lastTimeWatered >= self.wateringInterval:
            # sched water
            params = {
                'sched_params': {
                    'delay': 0,
                    'priority': SchedPriorityTable.waterOn,
                    'action': self.water_on
                }
            }
        else:
            params = {
                'sched_params': {
                    'delay': self.DEFAULT_INTERVAL,
                    'priority': SchedPriorityTable.should_water,
                    'action': self.should_water
                }
            }
        return params
