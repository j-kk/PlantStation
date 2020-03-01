import os

from PlantStation.Plant import Plant
from PlantStation.helpers.format_validators import parse_time
from gpiozero import DigitalOutputDevice, GPIOZeroError, Device
from gpiozero.pins.native import NativeFactory
from gpiozero.pins.mock import MockFactory
from PyInquirer import prompt
import configparser

import logging

PI_GPIO = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
WORKDIR='/etc/plantstation'
GLOBAL_CFG_PATH = '/etc/' #TODO pathlib
USER_CFG_PATH = os.path.expanduser("~") + '/.config/'
CFG_FILENAME = 'plantstation.cfg'
LOGFILE_PATH='/var/log/plantstation.log'

class ConstructConfig():
    _env_name: str
    _dry_run: bool = False
    _logger: logging
    _cfg_path: str = None
    _cfg_parser = configparser.ConfigParser()

    def __init__(self, mock=False): #TODO logs
        self._logger = logging.getLogger(__package__ + '.configurer')
        if mock:
            Device.pin_factory = MockFactory()
            self._dry_run = True
        else:
            Device.pin_factory = NativeFactory()



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
            device = DigitalOutputDevice("GPIO" + str(pin_number), active_high=False)
            print(f'Found GPIO{pin_number} Pin. Turning on!')
            device.on()
            confirm = [
                {
                    'type': 'confirm',
                    'message': 'Is any device working right now?',
                    'name': 'working',
                    'default': False,
                }
            ]
            answer = prompt(confirm)
            device.off()
            if answer['working']:  # TODO double declaration of pin
                self.create_plant(pin_number)
        except GPIOZeroError as exc:
            self._logger.error(f'Couldn\'t set up gpio pin: {pin_number}')
            raise exc

    def setup(self):
        try:
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
                    'choices': ['Default user location (recommended)','Default system location', 'Current location',  'Specify']
                }
            ]
            answers = prompt(questions)
            self._env_name = answers['env_name']
            self._cfg_parser['GLOBAL'] = {
                'ENV_NAME': self._env_name,
                'DEFAULT_INTERVAL': Plant.DEFAULT_INTERVAL
            }
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
                self._cfg_path = answers['cfg_path']
            elif answers['cfg_location'] == 'System location':
                self._cfg_path = GLOBAL_CFG_PATH
            elif answers['cfg_location'] == 'Default user location (recommended)':
                self._cfg_path = USER_CFG_PATH
            else:
                self._cfg_path = os.getcwd() + '/' + self._env_name + '.cfg'

            for pin_number in PI_GPIO:
                self.setup_pin(pin_number)

            if not os.path.isdir(self._cfg_path):
                os.mkdir(self._cfg_path)

            self._cfg_path += CFG_FILENAME

            try:
                cfg_file = open(self._cfg_path, 'w')
                self._cfg_parser.write(cfg_file)
                self._logger.info(f'Created config file in {self._cfg_path}')
                return self._cfg_path
            except FileNotFoundError or IsADirectoryError:
                self._logger.warning(f'Couldn\'t create file in given directory. Creating in current directory')
                cfg_file = open(os.getcwd() + '/' + self._env_name + '.cfg' , 'w')
                self._cfg_parser.write(cfg_file)
                return self._cfg_path
            except PermissionError:
                self._logger.error(f'Couldn\'t create file in given directory. No permissions to create file in {self._cfg_path}')
                return None

        except Exception as exc:
            return None



