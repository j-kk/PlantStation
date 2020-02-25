import argparse
import os
import signal
import logging

from PlantStation.App import App, StandaloneApp
from PlantStation.Configure import GLOBAL_CFG_PATH, LOGFILE_PATH, ConstructConfig

parser = argparse.ArgumentParser(description='Plantstation daemon')
parser.add_argument('-s', '--standalone', default=False, action='store_true',
                    help='Run standalone [path]')
parser.add_argument('-p', '--config-path', default=GLOBAL_CFG_PATH, action='store', help='Path to config file')
parser.add_argument('-d', '--debug', default=False, action='store_true', help='Print extra debug information')
parser.add_argument('--dry-run', default=False, action='store_true', help='Do not work on pins, dry run only')


if __name__ == '__main__':
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

    if not os.path.isfile(args.config_path):
        logger.debug(f'Config not found. Creating new')
        configurer = ConstructConfig(mock=args.dry_run)
        configurer.setup()
        args.config_path = configurer.cfg_path
        logger.debug(f'Created config at{configurer.cfg_path}')

    if args.standalone:
        app = StandaloneApp(config_path=args.config_path, dry_run=args.dry_run, debug=args.debug)
    else:
        app = App(config_path=args.config_path, dry_run=args.dry_run, debug=args.debug)
    signal.signal(signal.SIGHUP, app.stop_env)
    signal.signal(signal.SIGQUIT, app.stop_env)
    signal.signal(signal.SIGINT, app.stop_env)
    app.run()
