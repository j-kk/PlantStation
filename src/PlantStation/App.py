import argparse
import logging
import os
import signal
import sys

import daemon
import lockfile

from PlantStation.Configure import GLOBAL_CFG_PATH, LOGFILE_PATH, WORKDIR, USER_CFG_PATH
from PlantStation.Environment import Environment


class App(object):
    _mainEnvironment: Environment
    _config_path: str
    _debug: bool
    _logger = logging.getLogger(__package__)

    def __init__(self, config_path: str, dry_run: bool = False, debug: bool = False):
        # get config
        self._config_path = config_path
        self._debug = debug
        self._mainEnvironment = Environment(config_path=self._config_path, dry_run=dry_run)

        self._mainEnvironment.schedule_monitoring()

    def run_env(self):
        self._mainEnvironment.start()

    def stop_env(self):
        self._mainEnvironment.stop()

    def run(self):
        self.run_env()


class StandaloneApp(App):
    _logfile_path: str = LOGFILE_PATH

    def __init__(self, config_path: str = GLOBAL_CFG_PATH, dry_run: bool = False, debug: bool = False):
        # init normal App
        super().__init__(config_path=config_path, dry_run=dry_run, debug=debug)

        if not os.path.isdir(WORKDIR):
            self._logger.critical(f'Workdir not found. Quitting!')
            raise Exception(f'Workdir not found. Quitting!')

        # init daemon context, signal map
        self._context = daemon.DaemonContext(
            working_directory=WORKDIR,
            umask=0o022,
            pidfile=lockfile.FileLock('/var/run/plantstation')
        )

        self._context.signal_map = {
            signal.SIGTERM: self.stop_env,
            signal.SIGINT: self.stop_env,
            signal.SIGHUP: self.stop_env,
        }

    def run(self):
        with self._context:
            try:
                self.run_env()
            except Exception:
                sys.exit(1)


def run():
    parser = argparse.ArgumentParser(description='Plantstation daemon')
    parser.add_argument('-s', '--standalone', default=False, action='store_true',
                        help='Run standalone [path]')
    parser.add_argument('-p', '--config-path', action='store', nargs=1, help='Path to config file')
    parser.add_argument('-d', '--debug', default=False, action='store_true', help='Print extra debug information')
    parser.add_argument('--dry-run', default=False, action='store_true', help='Do not work on pins, dry run only')

    parser.add_argument('setup')

    args = parser.parse_args()

    logger = logging.getLogger(__package__)

    Formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    channel = logging.StreamHandler()
    channel.setFormatter(Formatter)
    logger.addHandler(channel)

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.debug(f'Path: {args.config_path}')

    if args.config_path is not None:
        if os.path.isfile(args.config_path):
            config_path = args.config_path
        else:
            logger.error(f'Given path is invalid!')
            sys.exit(1)
    elif os.path.isfile(USER_CFG_PATH):
        config_path = USER_CFG_PATH
    elif os.path.isfile(GLOBAL_CFG_PATH):
        config_path = GLOBAL_CFG_PATH
    else:
        logger.error(f'Config not found. Quitting')
        sys.exit(1)
    logger.info(f'Found config: {config_path}')

    try:
        if args.standalone:
            app = StandaloneApp(config_path=config_path, dry_run=args.dry_run, debug=args.debug)
        else:
            app = App(config_path=config_path, dry_run=args.dry_run, debug=args.debug)

        app.run()
    except Exception as err:
        logger.error(f'Received exception: {err}')
        sys.exit(1)
