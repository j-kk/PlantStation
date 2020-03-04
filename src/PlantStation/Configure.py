import argparse
import datetime
import getpass
import logging
import subprocess
import sys
from pathlib import Path

from PyInquirer import prompt
from gpiozero import DigitalOutputDevice, GPIOZeroError, Device
from gpiozero.pins.mock import MockFactory
from gpiozero.pins.native import NativeFactory


from PlantStation.Plant import Plant
from PlantStation.helpers.format_validators import parse_time
from PlantStation.helpers.config import Config
from helpers import does_throw

PI_GPIO = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]  # TODO
WORKDIR = Path('/etc/plantstation')
GLOBAL_CFG_PATH = Path('/etc/')
USER_CFG_PATH = Path('~/.config/').expanduser()
CFG_FILENAME = Path('plantstation.cfg')
LOGFILE_PATH = Path('/var/log/plantstation.log')


class EnvironmentConfig(Config):
    """
        Specification of environment file configuration creation
    """
    _env_name: str
    _dry_run: bool = False

    def __init__(self, mock=False):  # TODO logs
        super().__init__(logging.getLogger(__package__))
        if mock:
            Device.pin_factory = MockFactory()
            self._dry_run = True
        else:
            Device.pin_factory = NativeFactory()

    def _create_plant(self, pin_number: int):
        # create new plant! :3
        questions = [
            {
                'type': 'input',
                'message': 'Enter plant\'s name:',
                'name': 'plantName',
                'validate': lambda name: name not in self.cfg_parser and name != ""
            },
            {
                'type': 'input',
                'message': 'Enter watering duration (in seconds):',
                'name': 'wateringDuration',
                'validate': lambda t: t.isdigit()
            },
            {
                'type': 'input',
                'message': 'Enter interval between waterings (example: 10D 10:10:10):',
                'name': 'wateringInterval',
                'validate': lambda t: does_throw(parse_time, [t])
            }
        ]

        answers = prompt(questions)

        self.cfg_parser[answers['plantName']] = {
            'plantName': answers['plantName'],
            'wateringDuration': answers['wateringDuration'],
            'wateringInterval': answers['wateringInterval'],
            'lastTimeWatered': '',
            'gpioPinNumber': 'GPIO' + str(pin_number),
            'isActive': 'True'
        }

    def _check_pin(self, pin_number: int) -> bool:
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
            return answer['working']
        except GPIOZeroError as exc:
            self._logger.error(f'Couldn\'t set up gpio pin: {pin_number}')
            raise exc

    def _general_data(self):
        questions = [
            {
                'type': 'input',
                'message': 'Enter environment name:',
                'name': 'envName',
                'validate': lambda name: name != ''
            },
            {
                'type': 'list',
                'message': 'Choose configuration location:',
                'name': 'cfg_location',
                'choices': ['Default user location (recommended)', 'Default system location', 'Current location',
                            'Specify']
            },
            {
                'type': 'confirm',
                'message': 'Specify working hours? (who wants burping at the midnight?)',
                'name': 'workingHours',
                'default': False
            }
        ]
        answers = prompt(questions)
        local_path = Path.cwd().joinpath(Path(self._env_name + '.cfg'))
        if answers['cfg_location'] == 'Specify':
            questions = [
                {
                    'type': 'input',
                    'message': 'Enter path',
                    'name': 'cfg_path',
                    'validate': lambda p: Path(p).is_dir()
                }
            ]
            answers = prompt(questions)
            self._cfg_paths = [answers['cfg_path'].joinpath(Path(self._env_name + '.cfg')), local_path]
        elif answers['cfg_location'] == 'System location':
            self._cfg_paths = [GLOBAL_CFG_PATH.joinpath(Path(self._env_name + '.cfg')), local_path]
        elif answers['cfg_location'] == 'Default user location (recommended)':
            self._cfg_paths = [USER_CFG_PATH.joinpath(Path(self._env_name + '.cfg')), local_path]
        else:
            self._cfg_paths = [local_path]

        self._env_name = answers['envName']
        self.cfg_parser['GLOBAL'] = {
            'env_name': self._env_name,
            'workingHours': str(answers['workingHours'])
        }
        if answers['workingHours']:
            questions = [
                {
                    'type': 'input',
                    'message': 'Enter begin of the working hours (HH:MM)',
                    'name': 'workingHoursBegin',
                    'validate': lambda t: does_throw(datetime.time.fromisoformat, [t])
                },
                {
                    'type': 'input',
                    'message': 'Enter end of the working hours (HH:MM)',
                    'name': 'workingHoursEnd',
                    'validate': lambda t: does_throw(datetime.time.fromisoformat, [t])
                }
            ]
            answers = prompt(questions)
            self.cfg_parser['GLOBAL']['workingHoursBegin'] = answers['workingHoursBegin']
            self.cfg_parser['GLOBAL']['workingHoursEnd'] = answers['workingHoursEnd']

    def setup(self):
        """
            Asks user for data about environment
            Iterates over every pin and asks user if anything happens
            Then saves file to given location
        """
        self._general_data()

        for pin_number in PI_GPIO:
            if self._check_pin(pin_number):
                self._create_plant(pin_number)

        return str(self.write())


class ServiceCreator(Config):
    """
        Creates service file
    """

    def __init__(self, service_path: Path, path_to_config: Path):
        super().__init__(logging.getLogger(__package__))
        self._cfg_paths = [service_path]
        self.cfg_parser['Unit'] = {
            'Description': 'PlantStation service',  # TODO subparser
            'After': 'network.target',
            'StartLimitIntervalSec': 0
        }
        ScriptPath = subprocess.Popen('which PlantStation', shell=True, stdout=subprocess.PIPE).stdout.read().decode(
            'ascii').replace('\n', '')
        ExecStart = ScriptPath + ' -p ' + str(path_to_config)
        self.cfg_parser['Service'] = {
            'Type': 'simple',
            'Restart': 'always',
            'RestartSec': '3',
            'User': getpass.getuser(),
            'ExecStart': ExecStart
        }
        self.cfg_parser['Install'] = {
            'WantedBy': 'multi-user.target'
        }
        self.write()


class Configurer():
    def __init__(self):
        parser = argparse.ArgumentParser(
            description='PlantStation configurator',
            usage='''PlantSetup cmd [<args>]
        
        Available commands
           config     Create environment config file 
           service    Create service file to allow run daemon as systemd service
        ''')
        parser.add_argument('command', help='Subcommand to run')

        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            print('Unrecognized command')
            parser.print_help()
            exit(1)

        getattr(self, args.command)()

    def config(self):
        parser = argparse.ArgumentParser(description='Create new environment configuration file')
        parser.add_argument('-m', '--mock', default=False, action='store_true',
                            help='Do not perform operations on pins. (Mock pins)')

        args = parser.parse_args(sys.argv[2:])

        mock = vars(args)['mock']

        try:
            creator = EnvironmentConfig(mock=mock)
            config_path = creator.setup()
            print(f'Created config in {config_path}')
        except Exception:
            print(f'Couldn\'t create config file. Quitting!')
            sys.exit(1)

    def service(self):
        parser = argparse.ArgumentParser(description='Create service file for systemd')
        parser.add_argument('-p', '--config-path', action='store', nargs=1, required=True, help='Path to config file')
        parser.add_argument('-d', '--debug', action='store_true', default=False, help='Print extra debug info')
        parser.add_argument('-g', '--global', default=False, action='store_true',
                            help='Perform priority on global directories (requires sudo)')

        args = parser.parse_args(sys.argv[2:])

        destination_path: Path
        if vars(args)['global']:
            destination_path = Path('/etc/systemd/system/')
        else:
            destination_path = Path('~/.config/systemd/user/').expanduser()

        destination_path = destination_path.joinpath('PlantStation.service')

        configuration_file_path = Path(args.config_path[0]).absolute()

        if not configuration_file_path.is_file():
            print(f'Config file not found. Quitting!')
            sys.exit(1)
        else:
            print(f'Creating systemd service at {destination_path} with config {configuration_file_path}')

        try:
            ServiceCreator(service_path=destination_path, path_to_config=configuration_file_path)
            print(f'Created service')
        except Exception as exc:
            if args.debug:
                print(f'Couldn\'t create service files. Quitting! {exc}')
            else:
                print(f'Couldn\'t create service files. Quitting!')
            sys.exit(1)


def run():
    Configurer()


if __name__ == '__main__':
    run()
