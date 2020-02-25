import os

from PlantStation import Plant
from PlantStation.helpers.format_validators import parse_time
from gpiozero import DigitalOutputDevice, GPIOZeroError, Device
from gpiozero.pins.mock import MockFactory
from PyInquirer import prompt
from datetime import timedelta
import configparser

import logging

PI_GPIO = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
GLOBAL_CFG_PATH = '/etc/plantstation/env.cfg'
LOGFILE_PATH='/var/log/plantstation.log'

class ConstructConfig():
    _env_name: str
    _dry_run: bool = False
    _logger: logging
    cfg_path: str
    _cfg_parser = configparser.ConfigParser()

    def __init__(self, mock=False): #TODO logs
        questions = [
            {
                'type': 'input',
                'message': 'Enter environment name:',
                'name': 'env_name',
                'validate': lambda name: name != ''
            },
            {
                'type': 'list',
                'message': 'Choose configuration location:',
                'name': 'cfg_location',
                'choices': ['Current location', 'System location', 'Specify']
            }
        ]
        answers = prompt(questions)
        self._env_name = answers['env_name']
        self._cfg_parser['GLOBAL'] = {
            'ENV_NAME': self._env_name,
            'DEFAULT_INTERVAL': Plant.DEFAULT_INTERVAL
        }
        _logger = logging.getLogger(__package__ + '.configurer')
        if mock:
            Device.pin_factory = MockFactory()
            self._dry_run = True

        if answers['cfg_location'] == 'Specify':
            questions = [
                {
                    'type': 'input',
                    'message': 'Enter path',
                    'name': 'cfg_path',
                    'validate': lambda p: os.path.isdir(p)
                }
            ]
            answers = prompt(questions)
            self.cfg_path = answers['cfg_path']
        elif answers['cfg_location'] == 'System location':
            self.cfg_path = GLOBAL_CFG_PATH
        else:
            self.cfg_path = os.getcwd() + '/' + self._env_name + '.cfg'

    def create_plant(self, pin_number: int):
        # create new plant! :3
        questions = [
            {
                'type': 'input',
                'message': 'Enter plant\'s name:',
                'name': 'plant_name',
                'validate': lambda name: name not in self._cfg_parser and name != ""
            },
            {
                'type': 'input',
                'message': 'Enter watering duration (in seconds):',
                'name': 'watering_duration',
                'validate': lambda t: t.isdigit()
            },
            {
                'type': 'input',
                'message': 'Enter interval between waterings (example: 10D 10:10:10):',
                'name': 'watering_interval',
                'validate': lambda t: parse_time(t, quiet=True) != None
            }
        ]

        answers = prompt(questions)

        self._cfg_parser[answers['plant_name']] = {
            'plantName': answers['plant_name'],
            'wateringDuration': answers['watering_duration'],
            'wateringInterval': answers['watering_interval'],
            'lastTimeWatered': '',
            'gpioPinNumber': 'GPIO' + str(pin_number),
            'isActive': 'True'
        }

    def setup_pin(self, pin_number: int):
        try:
            pin = DigitalOutputDevice("GPIO" + str(pin_number), active_high=False, initial_value=True)
            print(f'Found GPIO{pin_number} Pin. Turning on!')
            pin.on()
            confirm = [
                {
                    'type': 'confirm',
                    'message': 'Is any device working right now?',
                    'name': 'working',
                    'default': False,
                }
            ]
            answer = prompt(confirm)
            if answer['working']:  # TODO double declaration of pin
                self.create_plant(pin_number)
        except GPIOZeroError as exc:
            self._logger.error(f'Couldn\'t set up gpio pin: {pin_number}')
            raise exc

    def setup(self):

        for pin_number in PI_GPIO:
            self.setup_pin(pin_number)

        with open(self.cfg_path, 'w') as cfg_file:
            self._cfg_parser.write(cfg_file)


