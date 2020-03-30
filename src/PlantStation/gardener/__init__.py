import argparse
import logging
import sys
from pathlib import Path

from PlantStation.configurer import USER_CFG_PATH, GLOBAL_CFG_PATH
from .App import App


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

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    logger.debug(f'Path: {args.config_path}')

    if args.config_path[0] is not None:
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
