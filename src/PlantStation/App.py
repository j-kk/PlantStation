import argparse
import logging
import signal
import sys
import threading
from pathlib import Path

from PlantStation.configurer.defaults import GLOBAL_CFG_PATH, USER_CFG_PATH
from PlantStation.core.config import EnvironmentConfig
from PlantStation.core.environment import Environment


class App(object):
    _mainEnvironment: Environment
    _config_path: Path
    _debug: bool
    _logger = logging.getLogger(__package__)

    __event: threading.Event

    def __init__(self, config_path: Path, dry_run: bool = False, debug: bool = False):
        # get config
        self._config_path = config_path
        self._debug = debug

        env_config = EnvironmentConfig.create_from_file(self._config_path, debug, dry_run)

        self._mainEnvironment = Environment(env_config)

        self.__event = threading.Event()

        for sig in ('TERM', 'HUP', 'INT'):
            signal.signal(getattr(signal, 'SIG' + sig), self.__event.set)

    def run(self):
        try:
            self._mainEnvironment.start()
            self.__event.wait()
        finally:
            self._mainEnvironment.stop()

def run():
    parser = argparse.ArgumentParser(description='Plantstation daemon')
    parser.add_argument('-p', '--config-path', action='store', nargs=1, help='Path to config file')
    parser.add_argument('-d', '--debug', default=False, action='store_true', help='Print extra debug information')
    parser.add_argument('--dry-run', default=False, action='store_true', help='Do not work on pins, dry run only')

    args = parser.parse_args()

    logger = logging.getLogger(__package__)

    Formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    channel = logging.StreamHandler()
    channel.setFormatter(Formatter)
    logger.addHandler(channel)

    logger.setLevel(logging.DEBUG if args.debug else logging.INFO)

    logger.debug(f'Path: {args.config_path}')

    if args.config_path is not None:
        if Path(args.config_path[0]).is_file():
            config_path = Path(args.config_path[0])
        else:
            logger.error(f'Given path is invalid!')
            sys.exit(1)
    elif USER_CFG_PATH.joinpath('environment.cfg'):
        config_path = USER_CFG_PATH.joinpath('environment.cfg')
    elif GLOBAL_CFG_PATH.joinpath('environment.cfg'):
        config_path = GLOBAL_CFG_PATH.joinpath('environment.cfg')
    else:
        logger.error(f'Config not found. Quitting')
        sys.exit(1)
    logger.info(f'Found config: {config_path}')

    try:
        app = App(config_path=config_path, dry_run=args.dry_run, debug=args.debug)

        app.run()
    except Exception as err:
        logger.error(f'Received exception: {err}')
        sys.exit(1)
