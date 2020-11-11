import configparser
import datetime
import logging
import shutil
import threading
from pathlib import Path
from threading import RLock
from typing import Tuple, List, Optional

DEFAULT_ACTIVE_LIMIT = 1


class Config(object):
    """
        Thrad safe config structure with logging
    """

    _path: Optional[Path] = None
    _cfg_parser: configparser.ConfigParser
    _cfg_lock: RLock
    _logger: logging.Logger

    def __init__(self, path: Path, logger_suffix: Optional[str] = None):
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
        self._cfg_lock = threading.RLock()
        self._cfg_parser = configparser.RawConfigParser()
        self._cfg_parser.optionxform = str
        self._logger = logging.getLogger(f'{__name__}:{logger_suffix}')
        self._path = path

    def update_section(self, section: str, key: str, value) -> None:
        if not self._cfg_parser.has_section(section):
            self._cfg_parser.add_section(section)
        self._cfg_parser[section][key] = value
        self.write()

    @property
    def path(self) -> Path:
        """Config location's path"""
        with self._cfg_lock:
            if not self._path:
                self._logger.critical(f'Config path was not set')
                raise ValueError(f'Config path is not set')
            else:
                return self._path

    @path.setter
    def path(self, value: Optional[Path]):
        assert isinstance(value, Path) or value is None
        with self._cfg_lock:
            if value is not None:
                if value.is_dir():
                    raise IsADirectoryError()
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
                self._logger.critical(f'Config file {self.path} not found')
                raise FileNotFoundError(f'Error: environment config file not found. Quitting!')
            else:
                self._logger.info(f'Config file {self._path} read succesfully!')

    def write(self) -> None:
        """Writes config to file. Thread safe"""
        with self._cfg_lock:
            try:
                cfg_file = open(self.path, 'w')
                self._cfg_parser.write(cfg_file)
                self._logger.debug(f'Saved config file in {self._path}')
            except FileNotFoundError or IsADirectoryError as exc:
                self._logger.warning(f'Couldn\'t create file in given directory.')
                raise exc
            except PermissionError as exc:
                self._logger.error(
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
    _env_name: str

    def __init__(self,
                 env_name: str,
                 path: Optional[Path] = None):
        # set env vars
        self._env_name = env_name

        # initialize config
        super().__init__(path, logger_suffix=env_name)
        if path is None:
            self._cfg_parser['GLOBAL'] = {
                'env_name': self._env_name
            }

    @property
    def silent_hours(self) -> Tuple[datetime.time, datetime.time]:
        """Silent hours working hours in tuple: (end, begin)"""
        try:
            with self._cfg_lock:
                begin = datetime.time.fromisoformat(self._cfg_parser['GLOBAL']['workingHoursBegin'])
                end = datetime.time.fromisoformat(self._cfg_parser['GLOBAL']['workingHoursEnd'])
                return end, begin
        except KeyError as exc:
            self._logger.error(f'Silent hours not given!')
            raise exc
        except ValueError as exc:
            self._logger.fatal(f'Silent hours in wrong format {exc}!')
            raise exc

    @silent_hours.setter
    def silent_hours(self, value: Tuple[datetime.time, datetime.time]) -> None:
        value = list(map(lambda t: t.strftime('%H:%M'), value))
        with self._cfg_lock:
            if 'GLOBAL' not in self._cfg_parser:
                self._cfg_parser['GLOBAL'] = {}
            self._cfg_parser['GLOBAL']['workingHoursBegin'] = value[1]
            self._cfg_parser['GLOBAL']['workingHoursEnd'] = value[0]

    @property
    def env_name(self) -> str:
        """Env name"""
        with self._cfg_lock:
            return self._env_name

    @property
    def silent_hours_state(self) -> bool:
        """State of the silent hours (enabled/disabled)"""
        with self._cfg_lock:
            return self._cfg_parser['GLOBAL']['workingHours'] == 'True'

    @silent_hours_state.setter
    def silent_hours_state(self, value: bool) -> None:
        with self._cfg_lock:
            self._logger.info(f'Setting silent hours state to {str(value)}')
            self._cfg_parser['GLOBAL']['workingHours'] = str(value)

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
            self._cfg_parser['GLOBAL']['ActiveLimit'] = str(value)
            self._logger.debug(f'Active limit set to {value}')

    def list_plants(self) -> List[str]:
        """Returns list of all plants' names specified in config"""
        with self._cfg_lock:
            sections = self._cfg_parser.sections()
            if 'GLOBAL' in sections:
                sections.remove('GLOBAL')
            return sections

    def remove_plant_section(self, plant: "Plant") -> None:
        """Removes plant section from config

        Args:
            plant (Plant): plant to remove
        """
        with self._cfg_lock:
            self._cfg_parser.remove_section(plant.plantName)

    def parse_plants(self) -> List[configparser.SectionProxy]:
        """Reads environment config file - plant section

        Reads config file from location defined by self._cfg_paths
        and if provided data are correct, returns Plants with provided data
        """

        # read_plants
        for section_name in self._cfg_parser.sections():
            if section_name not in ['GLOBAL']:
                yield self._cfg_parser[section_name]

    def calc_working_hours(self) -> datetime.timedelta:
        """Calculates time to next watering

        Returns:
            (timedelta): time to next watering
        """
        silent_hours = self.silent_hours

        if silent_hours is not None:
            now = datetime.datetime.now()
            today = now.date()

            prev_day = today - datetime.timedelta(days=1)
            for day in [today, prev_day]:
                window = datetime.datetime.combine(day, silent_hours[0]), datetime.datetime.combine(day,
                                                                                                    silent_hours[1])
                if window[0] > window[1]:
                    window = window[0], window[1] + datetime.timedelta(days=1)

                if window[0] <= now < window[1]:
                    return window[1] - now

        return datetime.timedelta(0)

    @classmethod
    def create_from_file(cls, path: Path):
        """Builds env config from file"""
        if not path.exists() or not path.is_file():
            raise FileNotFoundError()
        if not path.name.endswith('.cfg'):
            raise FileExistsError('File has wrong suffix')

        env_name = path.name[:-4]
        env = cls(env_name, path)
        env.read()
        return env
