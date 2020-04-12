import argparse
import datetime
import getpass
import logging
import subprocess
import sys

from PyInquirer import prompt
from gpiozero import DigitalOutputDevice, GPIOZeroError, Device, pins

from PlantStation.configurer.defaults import *
from PlantStation.core import Config
from PlantStation.core.helpers import parse_time, does_throw
from core import EnvironmentConfig, Plant


class EnvironmentCreator(object):
    """
        Specification of environment file configuration creation
    """
    env_name: str
    dry_run: bool
    config: EnvironmentConfig

    def __init__(self, debug=False, dry_run=False):
        self.debug = debug
        self.dry_run = dry_run
        # Get general data like config name & location
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
            },
            {
                'type': 'input',
                'message': 'How many pumps should work simultanously?',
                'name': 'ActiveLimit',
                'default': '1',
                'validate': lambda t: does_throw(int, t)

            }
        ]
        answers = prompt(questions)
        self.env_name = answers['envName']
        self.workingHours = str(answers['workingHours'])
        self.config = EnvironmentConfig(self.env_name, debug=self.debug, dry_run=self.dry_run)
        self.config.active_limit = answers['ActiveLimit']

        # Generate paths to config destinations
        local_path = Path.cwd().joinpath(Path(self.env_name + '.cfg'))

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
            paths = [answers['cfg_path'].joinpath(Path(self.env_name + '.cfg')), local_path]
        elif answers['cfg_location'] == 'System location':
            paths = [GLOBAL_CFG_PATH.joinpath(Path(self.env_name + '.cfg')), local_path]
        elif answers['cfg_location'] == 'Default user location (recommended)':
            paths = [USER_CFG_PATH.joinpath(Path(self.env_name + '.cfg')), local_path]
        else:
            paths = [local_path]

        for path in paths:
            try:
                self.config.path = path
                break
            except ValueError or IsADirectoryError as exc:
                raise exc

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
            self.config['GLOBAL']['workingHoursBegin'] = (answers['workingHoursBegin'], answers['workingHoursEnd'])

        if self.mock:
            Device.pin_factory = pins.mock.MockFactory()
            self.dry_run = True
        else:
            Device.pin_factory = pins.native.NativeFactory()
        for pin_number in PI_GPIO:
            if self._check_pin(pin_number):
                self._create_plant(pin_number)

        self.config.write()

    def _create_plant(self, pin_number: int):
        # create new plant! :3
        questions = [
            {
                'type': 'input',
                'message': 'Enter plant\'s name:',
                'name': 'plantName',
                'validate': lambda name: name not in self.config.cfg_parser and name != ""
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
        plant = Plant(answers['plantName'], self.config, gpioPinNumber='GPIO' + str(pin_number),
                      wateringDuration=answers['wateringDuration'], wateringInterval=answers['wateringInterval'],
                      isActive=True)
        self.config.update_plant_section(plant)

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
            print(f'Couldn\'t set up gpio pin: {pin_number}')
            raise exc


class ServiceCreatorConfig(Config):
    """
        Creates service file
    """

    def __init__(self, service_path: Path, path_to_config: Path):
        super().__init__(logging.getLogger(__package__), path=service_path)
        self._cfg_parser['Unit'] = {
            'Description': 'PlantStation service',  # TODO subparser
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
            EnvironmentCreator(mock=mock)

            print(f'Created config')
        except Exception as exc:
            print(f'Couldn\'t create config file. Quitting! {exc}')
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
            ServiceCreatorConfig(service_path=destination_path, path_to_config=configuration_file_path)
            print(f'Created service')
        except Exception as exc:
            if args.debug:
                print(f'Couldn\'t create service files. Quitting! {exc}')
            else:
                print(f'Couldn\'t create service files. Quitting!')
            sys.exit(1)


if __name__ == '__main__':
    Configurer()
