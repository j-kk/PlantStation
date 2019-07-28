import signal
import daemon
import lockfile
import logging
from PlantStation.main import setup_env, run_env, stop_env

CONFIG_PATH = 'enviroment.cfg'
LOGFILE_PATH = '/var/log/plantstation.log'

context = daemon.DaemonContext(
    working_directory='/etc/plantstation',
    umask=0o022,
    pidfile=lockfile.FileLock('/var/run/plantstation'),
    stdout='LOGFI'
    )

context.signal_map = {
    signal.SIGTERM: stop_env(),
    signal.SIGHUP: 'terminate'
    }


def setupLogger():
    context.files_preserve = [LOGFILE_PATH]

    logger = logging.getLogger('PlantStation')
    logger.setLevel(logging.DEBUG)

    loggerFileHandler = logging.FileHandler(LOGFILE_PATH)
    loggerFileHandler.setLevel(logging.DEBUG)

    loggerConsoleHandler = logging.StreamHandler()
    loggerConsoleHandler.setLevel(logging.ERROR)

    loggerFormatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    loggerFileHandler.setFormatter(loggerFormatter)
    loggerConsoleHandler.setFormatter(loggerFormatter)

    logger.addHandler(loggerFileHandler)
    logger.addHandler(loggerConsoleHandler)

setupLogger()
setup_env()

with context:
    run_env()
