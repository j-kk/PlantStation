from pathlib import Path

PI_GPIO = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]  # TODO
WORKDIR = Path('/etc/plantstation')
GLOBAL_CFG_PATH = Path('/etc/')
USER_CFG_PATH = Path('~/.config/').expanduser()
CFG_FILENAME = Path('plantstation.cfg')
LOGFILE_PATH = Path('/var/log/plantstation.log')
