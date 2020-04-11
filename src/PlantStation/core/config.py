import configparser
import datetime
import logging
import shutil
from pathlib import Path
from threading import RLock

from .ext.pins import PinManager
from .helpers.format_validators import parse_time

DEFAULT_ACTIVE_LIMIT = 1


class Config(object):
    """
        Thrad safe config structure with logging
    """

    _path: Path = None
    _cfg_parser : configparser.RawConfigParser
    _cfg_lock : RLock
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
    """
    _dry_run = False
    _env_name: str
    debug: bool
    pin_manager: PinManager

    def __init__(self, env_name: str, path=None, debug=False, dry_run: bool = False):
        """
        Default constructor. Uses program's logger

        Parameters:
        -----------

        path : pathlib.Path
            path to config
        debug : bool = False
            print extra debug information
        dry_run : bool = False
            should pins be mocked?
        """
        # set env vars
        self.env_name = env_name
        self.debug = debug
        self.dry_run = dry_run

        # create global logger
        logger = logging.getLogger('PlantStation').getChild(self.env_name)
        Formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        channel = logging.StreamHandler()
        channel.setFormatter(Formatter)
        logger.addHandler(channel)
        logger.setLevel(logging.DEBUG if debug else logging.INFO)

        # initialize config
        super().__init__(logger, path)
        if path is None:
            self.cfg_parser['GLOBAL'] = {}
        # initialize pins
        self.pin_manager = PinManager(dry_run=dry_run)

    @property
    def silent_hours(self):
        try:
            if self.cfg_parser['GLOBAL']['workingHours'] == 'True':
                begin = datetime.datetime.strptime(self.cfg_parser['GLOBAL']['workingHoursBegin'], '%H:%M').time()
                end = datetime.datetime.strptime(self.cfg_parser['GLOBAL']['workingHoursEnd'], '%H:%M').time()
                return [begin, end]
            else:
                return None
        except KeyError as exc:
            self.logger.error(f'Silent hours not given!')
            raise exc
        except ValueError as exc:
            self.logger.fatal(f'Silent hours in wrong format {exc}!')
            raise exc

    @silent_hours.setter
    def silent_hours(self, value: (datetime.time, datetime.time)):
        value = list(map(lambda t: t.strftime('%H:%M'), value))
        with self._cfg_lock:
            self.cfg_parser['GLOBAL']['workingHours'] = str(True)
            self.cfg_parser['GLOBAL']['workingHoursBegin'] = value[1]
            self.cfg_parser['GLOBAL']['workingHoursEnd'] = value[0]

    @property
    def active_limit(self):
        try:
            return int(self._cfg_parser['GLOBAL']['ActiveLimit'])
        except KeyError:
            return DEFAULT_ACTIVE_LIMIT

    @active_limit.setter
    def active_limit(self, value: int):
        self.pin_manager.active_limit = value
        self.cfg_parser['GLOBAL']['ActiveLimit'] = str(value)
        self.logger.debug(f'Active limit set to {value}')

    def list_plants(self):
        """
        Returns list of all plants' names specified in config
        """
        sections = self.cfg_parser.sections()
        if 'GLOBAL' in sections:
            sections.remove('GLOBAL')
        return sections

    def add_plant(self, plant):
        section = dir(plant)

        with self._cfg_lock:
            self.cfg_parser[plant.plantName] = {}

            for key in section:
                self.cfg_parser[plant.plantName][key] = str(getattr(plant, key))

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
                            seconds=int(self._cfg_parser[section]['wateringDuration'])),
                        'wateringInterval': parse_time(time_str=self._cfg_parser[section]['wateringInterval']),
                        'gpioPinNumber': str(self._cfg_parser[section]['gpioPinNumber'])}
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

    @staticmethod
    def create_from_file(path: Path, debug: bool = False, dry_run: bool = False):
        # check path
        if not path.exists() or not path.is_file():
            raise FileNotFoundError()
        if not path.name.endswith('.cfg'):
            raise FileExistsError('File has wrong suffix')

        env_name = path.name[:-4]
        env = EnvironmentConfig(env_name, path, debug, dry_run)
        env.read()
        env.pin_manager.active_limit = env.active_limit #TODO in future
        return env

