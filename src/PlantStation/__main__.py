import argparse
import logging
import sys
from pathlib import Path

from PlantStation.App import App
from PlantStation.configurer.defaults import GLOBAL_CFG_PATH, USER_CFG_PATH
from PlantStation.core.helpers.logger import get_root_logger

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Plantstation daemon')
    parser.add_argument('-p', '--config-path', action='store', nargs=1, help='Path to config file')
    parser.add_argument('-d', '--debug', default=False, action='store_true', help='Print extra debug information')
    parser.add_argument('--dry-run', default=False, action='store_true', help='Do not work on pins, dry run only')

    args = parser.parse_args()

    logger = get_root_logger(args.debug)

    logger.debug(f'Path: {args.config_path}')

    if args.config_path is not None:
        if Path(args.config_path[0]).is_file():
            config_path = Path(args.config_path[0])
        else:
            logger.error(f'Given path is invalid!')
            sys.exit(1)
    elif USER_CFG_PATH.joinpath('environment.cfg').is_file():
        config_path = USER_CFG_PATH.joinpath('environment.cfg')
    elif GLOBAL_CFG_PATH.joinpath('environment.cfg').is_file():
        config_path = GLOBAL_CFG_PATH.joinpath('environment.cfg')
    else:
        logger.error(f'Config not found. Quitting')
        sys.exit(1)
    logger.info(f'Found config: {config_path}')

    # try:
    app = App(config_path=config_path, dry_run=args.dry_run)

    app.run()
    # except Exception as err:
    #     logger.error(f'Received exception: {err}')
    #     sys.exit(1)

