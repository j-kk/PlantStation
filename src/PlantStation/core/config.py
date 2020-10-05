import configparser
import datetime
import logging
import shutil
from pathlib import Path
from threading import RLock
from typing import Tuple, List

from . import parse_time

DEFAULT_ACTIVE_LIMIT = 1


class Config(object):
    """
        Thrad safe config structure with logging
    """

    _path: Path = None
    _cfg_parser: configparser.RawConfigParser
    _cfg_lock: RLock
    _logger: logging.Logger

    def __init__(self, logger: logging.Logger, path: Path, dry_run=False):
        """
            Default constructor. Uses program's logger

        Parameters:
        -----------
        logger : logging.Logger
            program's logger
        path : pathlib.Path
            path to the config
        dry_run : boolean = False
            should all IO operations be mocked?
        """
        self._cfg_lock = RLock()
        self._cfg_parser = configparser.RawConfigParser()
        self._cfg_parser.optionxform = str
        self._logger = logger
        self._dry_run = dry_run
        if path:
            self.path = path

    def __getitem__(self, item):
        with self._cfg_lock:
            return self._cfg_parser[item]

    def __setitem__(self, key, value):
        with self._cfg_lock:
            self._cfg_parser[key] = value

    @property
    def cfg_parser(self):
        with self._cfg_lock:
            return self._cfg_parser

    @property
    def logger(self):
        """
            Returns global logger
        """
        return self._logger

    @property
    def path(self):
        """
            Config location's path
        """
        with self._cfg_lock:
            if not self._path:
                self.logger.critical(f'Config path was not set')
                raise ValueError(f'Config path is not set')
            else:
                return self._path

    @path.setter
    def path(self, value: Path):
        with self._cfg_lock:
            if value.suffix != '.cfg':
                raise ValueError(f'Specified path is not a .cfg')
            if value.is_dir():
                raise IsADirectoryError()
            if not self._dry_run:
                if not value.parent.is_dir():
                    self._path.parent.mkdir(parents=True)
            if self._path:
                shutil.move(self._path, value)
            self._path = value

    def read(self) -> None:
        """
            Reads content from config file. Thread safe
        """
        with self._cfg_lock:
            if not self._cfg_parser.read(self.path):
                self.logger.critical(f'Config file {self.path} not found')
                raise FileNotFoundError(f'Error: environment config file not found. Quitting!')
            else:
                self.logger.info(f'Config file {self._path} read succesfully!')

    def write(self) -> None:
        """
            Writes config to file. Thread safe
        """
        with self._cfg_lock:
            try:
                cfg_file = open(self.path, 'w')
                self._cfg_parser.write(cfg_file)
                self.logger.info(f'Created config file in {self._path}')
            except FileNotFoundError or IsADirectoryError as exc:
                self.logger.warning(f'Couldn\'t create file in given directory.')
                raise exc
            except PermissionError as exc:
                self.logger.error(
                    f'Couldn\'t create file in given directory. No permissions to create file in {self._path}')
                raise exc


class EnvironmentConfig(Config):
    """
        Configuration intended for general use. Stores information about GPIO,
        creates global logger

        Args:
            - env_name (str): Environment name
            - path (pathlib.Path): Path to the config file
            - debug (bool): Show debug data
            - dry_run (bool): Simulate operations on pins
    """
    _dry_run: bool
    _env_name: str
    _debug: bool

    def __init__(self,
                 env_name: str,
                 path: Path = None,
                 debug: bool = False,
                 dry_run: bool = False):
        # set env vars
        self._env_name = env_name
        self._debug = debug
        self._dry_run = dry_run

        # create global logger
        logger = logging.getLogger('PlantStation').getChild(self._env_name)
        Formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        channel = logging.StreamHandler()
        channel.setFormatter(Formatter)
        logger.addHandler(channel)
        logger.setLevel(logging.DEBUG if debug else logging.INFO)

        # initialize config
        super().__init__(logger, path)
        if path is None:
            self.cfg_parser['GLOBAL'] = {
                'env_name': self._env_name
            }

    @property
    def silent_hours(self) -> Tuple[datetime.time, datetime.time]:
        """Silent hours working hours in tuple: (end, begin)"""
        try:
            with self._cfg_lock:
                begin = datetime.time.fromisoformat(self.cfg_parser['GLOBAL']['workingHoursBegin'])
                end = datetime.time.fromisoformat(self.cfg_parser['GLOBAL']['workingHoursEnd'])
                return end, begin
        except KeyError as exc:
            self.logger.error(f'Silent hours not given!')
            raise exc
        except ValueError as exc:
            self.logger.fatal(f'Silent hours in wrong format {exc}!')
            raise exc

    @silent_hours.setter
    def silent_hours(self, value: Tuple[datetime.time, datetime.time]) -> None:
        value = list(map(lambda t: t.strftime('%H:%M'), value))
        with self._cfg_lock:
            if 'GLOBAL' not in self.cfg_parser:
                self.cfg_parser['GLOBAL'] = {}
            self.cfg_parser['GLOBAL']['workingHoursBegin'] = value[1]
            self.cfg_parser['GLOBAL']['workingHoursEnd'] = value[0]

    @property
    def debug(self) -> bool:
        """Is debug mode"""
        return self._debug

    @property
    def dry_run(self):
        """Is dry run"""
        return self._dry_run

    @property
    def env_name(self) -> str:
        """Env name"""
        with self._cfg_lock:
            return self._env_name

    @property
    def silent_hours_state(self) -> bool:
        """State of the silent hours (enabled/disabled)"""
        with self._cfg_lock:
            return self.cfg_parser['GLOBAL']['workingHours'] == 'True'

    @silent_hours_state.setter
    def silent_hours_state(self, value: bool) -> None:
        with self._cfg_lock:
            self.logger.info(f'Setting silent hours state to {str(value)}')
            self.cfg_parser['GLOBAL']['workingHours'] = str(value)

    @property
    def active_limit(self) -> int:
        """Limit of simulatanously working active pumps"""
        try:
            with self._cfg_lock:
                return int(self._cfg_parser['GLOBAL']['ActiveLimit'])
        except KeyError:
            self._cfg_parser['GLOBAL']['ActiveLimit'] = str(DEFAULT_ACTIVE_LIMIT)
            return DEFAULT_ACTIVE_LIMIT

    @active_limit.setter
    def active_limit(self, value: int) -> None:
        with self._cfg_lock:
            self.cfg_parser['GLOBAL']['ActiveLimit'] = str(value)
            self.logger.debug(f'Active limit set to {value}')

    def list_plants(self) -> List[str]:
        """Returns list of all plants' names specified in config"""
        with self._cfg_lock:
            sections = self.cfg_parser.sections()
            if 'GLOBAL' in sections:
                sections.remove('GLOBAL')
            return sections

    def update_plant_section(self, plant: "Plant") -> None:
        """Updates plant section of environment

        Args:
            - plant (Plant): plant object to update

        """
        section = dir(plant)

        with self._cfg_lock:
            self.cfg_parser[plant.plantName] = {}

            for key in section:
                self.cfg_parser[plant.plantName][key] = str(getattr(plant, key))

    def remove_plant_section(self, plant: "Plant") -> None:
        """Removes plant section from config

        Args:
            plant (Plant): plant to remove
        """
        with self._cfg_lock:
            self.cfg_parser.remove_section(plant.plantName)

    def parse_plants(self):
        """Reads environment config file - plant section

        Reads config file from location defined by self._cfg_paths
        and if provided data are correct, returns Plants with provided data
        """
        # read global section
        plant_params = []

        # read_plants
        for section in self._cfg_parser:
            if section == 'DEFAULT':
                continue
            if section != 'GLOBAL':
                self.logger.debug('Found new section: %s', section)
                try:  # TODO How about replacing params with Dataclass?
                    params = {
                        'plantName': str(section),
                        'wateringDuration': datetime.timedelta(
                            seconds=float(self._cfg_parser[section]['wateringDuration'])),
                        'wateringInterval': parse_time(self._cfg_parser[section]['wateringInterval']),
                        'gpioPinNumber': str(self._cfg_parser[section]['gpioPinNumber']),
                        'isActive': bool(self._cfg_parser[section]['isActive'])}
                    if self._cfg_parser[section]['lastTimeWatered'] != '':
                        time_str = self._cfg_parser[section]['lastTimeWatered']
                        params['lastTimeWatered'] = datetime.datetime.strptime(time_str, '%Y-%m-%d %X')
                    else:
                        params['lastTimeWatered'] = datetime.datetime.min
                    plant_params.append(params)
                    self.logger.info(
                        f'Found new plant: {params["plantName"]}, pin: {params["gpioPinNumber"]}')
                except KeyError as err:
                    self.logger.error(
                        f'{self._cfg_parser}: Failed to read {section} section - '
                        f'option not found {str(err)}')
                except Exception as err:
                    self.logger.error(
                        f'{self._path} Failed to read {section} section {err}')
        return plant_params

    @classmethod
    def create_from_file(cls, path: Path, debug: bool = False, dry_run: bool = False):
        """Builds env config from file"""
        if not path.exists() or not path.is_file():
            raise FileNotFoundError()
        if not path.name.endswith('.cfg'):
            raise FileExistsError('File has wrong suffix')

        env_name = path.name[:-4]
        env = cls(env_name, path, debug, dry_run)
        env.read()
        return env
