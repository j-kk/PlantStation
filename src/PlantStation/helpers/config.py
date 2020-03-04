import configparser
import logging
from pathlib import Path
from threading import Lock


class Config(object):
    """
        Specification of configuration with multiple saving destinations
        On write tries to save to first path in list. If it fails - tries next
    """
    _cfg_paths: [Path]
    cfg_parser= configparser.RawConfigParser()
    _cfg_lock = Lock()
    _logger: logging.Logger

    def __init__(self, logger: logging.Logger, cfg_paths: [Path] = []):
        self.cfg_parser.optionxform = str
        self._logger = logger
        self._cfg_paths = cfg_paths

    def read(self):
        """
            Reads content from 1st path
        """
        if not self.cfg_parser.read(self._cfg_paths[0]):
            self._logger.critical(f'Config file {self._cfg_paths[0]} not found')
            raise FileNotFoundError(f'Error: environment config file not found. Quitting!')

    def write(self) -> Path:
        """
            Saves config to given directory. Thread safe
        :return: Path to file
        """
        ret: Path
        self._cfg_lock.acquire()
        ret = self._write_to_file()
        self._cfg_lock.release()
        return ret

    def _write_to_file(self) -> Path:
        try:
            cfg_file = open(self._cfg_paths[0], 'w')
            self.cfg_parser.write(cfg_file)
            self._logger.info(f'Created config file in {self._cfg_paths}')
            return self._cfg_paths[0]
        except FileNotFoundError or IsADirectoryError as exc:

            if not self._cfg_paths[0].parent.is_dir():
                self._cfg_paths[0].parent.mkdir(parents=True)
                self._write_to_file()
            else:
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

