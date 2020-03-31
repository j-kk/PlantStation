import configparser
import datetime
import logging
from pathlib import Path
from threading import Semaphore, RLock

from gpiozero.pins import mock, native

from .helpers.format_validators import parse_time

DEFAULT_ACTIVE_LIMIT = 1


class Config(object):
    """
        Thrad safe config structure with logging
    """

    _path: Path
    _cfg_parser = configparser.RawConfigParser()
    _cfg_lock = RLock()
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
        self._cfg_parser.optionxform = str
        self._logger = logger
        self._path = path

        if not dry_run:
            if not self._path.parent.is_dir():
                self._path.parent.mkdir(parents=True)

    def __getitem__(self, item):
        with self._cfg_lock:
            return self._cfg_parser[item]

    def __setitem__(self, key, value):
        with self._cfg_lock:
            self._cfg_parser[key] = value

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
            return self._path

    def read(self) -> None:
        """
            Reads content from config file. Thread safe
        """
        with self._cfg_lock:
            if not self._cfg_parser.read(self._path):
                self.logger.critical(f'Config file {self._path} not found')
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
    _silent_hours = False
    _dry_run = False
    _pin_factory = None
    _env_name: str
    _active_limit = DEFAULT_ACTIVE_LIMIT
    _pump_lock: Semaphore = None
    _debug: bool

    def __init__(self, path: Path, debug=False, dry_run: bool = False):
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
        # check path
        if not path.exists() or not path.is_file():
            raise FileNotFoundError()
        if not path.name.endswith('.cfg'):
            raise FileExistsError('File has wrong suffix')

        # set env vars
        self.env_name = path.name[:-4]
        self.debug = debug
        self.dry_run = dry_run

        # create global logger
        logger = logging.getLogger('PlantStation').getChild(self.env_name)
        Formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        channel = logging.StreamHandler()
        channel.setFormatter(Formatter)
        logger.addHandler(channel)
        logger.setLevel(logging.DEBUG if debug else logging.INFO)

        #initialize config
        super().__init__(logger, path)

        # read config file
        self.logger.info(f'Using config file: {self._path}')
        self.read()

        # create pin factory
        self._pin_factory = native.NativeFactory() if not dry_run else mock.MockFactory()

        # check working hours
        if 'workingHours' in self._cfg_parser['GLOBAL']:
            if self._cfg_parser['GLOBAL']['workingHours'] == 'True':
                if 'silent_hours_begin' in self._cfg_parser['GLOBAL'] and 'silent_hours_end' in self._cfg_parser[
                    'GLOBAL']:
                    try:
                        datetime.datetime.strptime(self._cfg_parser['GLOBAL']['workingHoursBegin'], '%H:%M')
                        datetime.datetime.strptime(self._cfg_parser['GLOBAL']['workingHoursEnd'], '%H:%M')
                    except ValueError as exc:
                        self.logger.error(f'Silent hours in wrong format!')
                        raise exc
                else:
                    self.logger.info(f'No silent hours schedule')
            else:
                self._cfg_parser['GLOBAL']['workingHours'] = 'False'

        # set limit of active pumps
        if 'ActiveLimit' in self._cfg_parser['GLOBAL']:
            try:
                self.active_limit = int(self._cfg_parser['GLOBAL']['ActiveLimit'])
                self.logger.debug(f'Active limit set to {self.active_limit}')
            except ValueError as exc:
                self.logger.error(f'ActiveLimit is not a number!')
                raise exc

            if self.active_limit > 0:
                self._pump_lock = Semaphore(self.active_limit)

    @property
    def pin_factory(self):
        """
            Returns pin factory
        """
        return self._pin_factory

    def get_pump_lock(self):
        """
            Acquires permission to turn water pump
        """
        if self._pump_lock is not None:
            self._pump_lock.acquire()

    def release_pump_lock(self):
        """
            Releases permission
        """
        if self._pump_lock is not None:
            self._pump_lock.release()

    def read_plants(self):
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
