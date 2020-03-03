import argparse
import configparser
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

PI_GPIO = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]  # TODO
WORKDIR = Path('/etc/plantstation')
GLOBAL_CFG_PATH = Path('/etc/')
USER_CFG_PATH = Path('~/.config/').expanduser()
CFG_FILENAME = Path('plantstation.cfg')
LOGFILE_PATH = Path('/var/log/plantstation.log')


class Config:
    """
        Specification of configuration with multiple saving destinations
        On write tries to save to first path in list. If it fails - tries next
    """
    _cfg_paths: [Path]
    _cfg_parser = configparser.ConfigParser()
    _logger = logging.getLogger('PlantSetup')

    def _write_to_file(self):
        try:
            cfg_file = open(self._cfg_paths[0], 'w')
            self._cfg_parser.write(cfg_file)
            self._logger.info(f'Created config file in {self._cfg_paths}')
            return self._cfg_paths
        except FileNotFoundError or IsADirectoryError as exc:

            if not self._cfg_paths[0].parent.is_dir():
                self._cfg_paths[0].parent.mkdir(parents=True)

            self._logger.warning(f'Couldn\'t create file in given directory. Creating in current directory')
            self._cfg_paths = self._cfg_paths[1:]
            if len(self._cfg_paths) == 0:
                raise exc
            else:
                self._write_to_file()
        except PermissionError as exc:
            self._logger.error(
                f'Couldn\'t create file in given directory. No permissions to create file in {self._cfg_paths}')
            raise exc


class EnvironmentConfig(Config):
    """
        Specification of environment file configuration creation
    """
    _env_name: str
    _dry_run: bool = False

    def __init__(self, mock=False):  # TODO logs
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
                'name': 'env_name',
                'validate': lambda name: name != ''
            },
            {
                'type': 'list',
                'message': 'Choose configuration location:',
                'name': 'cfg_location',
                'choices': ['Default user location (recommended)', 'Default system location', 'Current location',
                            'Specify']
            }
        ]
        answers = prompt(questions)
        self._env_name = answers['env_name']
        self._cfg_parser['GLOBAL'] = {
            'ENV_NAME': self._env_name,
            'DEFAULT_INTERVAL': Plant.DEFAULT_INTERVAL
        }
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

        return self._write_to_file()


class ServiceCreator(Config):
    """
        Creates service file
    """

    def __init__(self, service_path: Path, path_to_config: Path):
        self._cfg_paths = [service_path]
        self._cfg_parser['Unit'] = {
            'Description': 'PlantStation service',
            'After': 'network.target',
            'StartLimitIntervalSec': 0
        }
        ScriptPath = subprocess.Popen('which PlantStation', shell=True, stdout=subprocess.PIPE).stdout.read().decode(
            'ascii').replace('\n', '')
        ExecStart = ScriptPath + ' -p ' + str(path_to_config)
        self._cfg_parser['Service'] = {
            'Type': 'simple',
            'Restart': 'always',
            'RestartSec': '3',
            'User': getpass.getuser(),
            'ExecStart': ExecStart
        }
        self._cfg_parser['Install'] = {
            'WantedBy': 'multi-user.target'
        }
        self._write_to_file()


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
        # parser.add_argument('-d', '--debug', default=False, action='store_true', help='Print extra debug information')
        parser.add_argument('-m', '--mock', default=False, action='store_true',
                            help='Do not perform operations on pins. (Mock pins)')

        args = parser.parse_args(sys.argv[2:])

        # debug = vars(args)['debug']
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
        # parser.add_argument('-d', '--debug', default=False, action='store_true', help='Print extra debug information')
        parser.add_argument('-g', '--global', default=False, action='store_true',
                            help='Perform operation on global directories (requires sudo)')

        args = parser.parse_args(sys.argv[2:])

        destination_path: Path

        destination_path: Path
        if vars(args)['global']:
            destination_path = Path('/etc/systemd/system/')
        else:
            destination_path = Path('~/.config/systemd/user/').expanduser()

        # debug = vars(args)['debug']

        try:
            ServiceCreator(service_path=destination_path, path_to_config=Path(args.environment_path).absolute())
            print(f'Created service')
        except Exception:
            print(f'Couldn\'t create service files. Quitting!')
            sys.exit(1)


def run():
    Configurer()


if __name__ == '__main__':
    run()
