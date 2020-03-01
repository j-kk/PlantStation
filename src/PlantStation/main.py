import argparse
import os
import logging

from PlantStation.App import App, StandaloneApp
from PlantStation.Configure import GLOBAL_CFG_PATH, USER_CFG_PATH, ConstructConfig

parser = argparse.ArgumentParser(description='Plantstation daemon')
parser.add_argument('-s', '--standalone', default=False, action='store_true',
                    help='Run standalone [path]')
parser.add_argument('-p', '--config-path', action='store', help='Path to config file')
parser.add_argument('-d', '--debug', default=False, action='store_true', help='Print extra debug information')
parser.add_argument('--dry-run', default=False, action='store_true', help='Do not work on pins, dry run only')


def run():
    config_path = None
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

    if args.config_path != None:
        if os.path.isfile(args.config_path):
            config_path = args.config_path
        else:
            logger.error(f'Given path is invalid!')
            return
    elif os.path.isfile(USER_CFG_PATH):
        config_path = USER_CFG_PATH
    elif os.path.isfile(GLOBAL_CFG_PATH):
        config_path = GLOBAL_CFG_PATH
    else:
        logger.info(f'Config not given in path. Checking user location.')
        configurer = ConstructConfig(mock=args.dry_run)
        config_path = configurer.setup()
        if config_path == None:
            logger.error(f'Failed to create config file')
            return
        logger.debug(f'Created config at {config_path}')
    logger.info(f'Found config: {config_path}')

    try:
        if args.standalone:
            app = StandaloneApp(config_path=config_path, dry_run=args.dry_run, debug=args.debug)
        else:
            app = App(config_path=config_path, dry_run=args.dry_run, debug=args.debug)

        app.run()
    except Exception as err:
        logger.error(f'Received exception: {err}')

