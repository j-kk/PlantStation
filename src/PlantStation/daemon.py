import signal
import daemon
import lockfile
import logging
from main import setup_env, run_env, stop_env

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


def setupLogger() -> None:
    """Sets up daemon logger

    """
    context.files_preserve = [LOGFILE_PATH]

    logger = logging.getLogger('PlantStation')
    logger.setLevel(logging.DEBUG)

    logger_file_handler = logging.FileHandler(LOGFILE_PATH)
    logger_file_handler.setLevel(logging.DEBUG)

    logger_console_handler = logging.StreamHandler()
    logger_console_handler.setLevel(logging.ERROR)

    logger_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger_file_handler.setFormatter(logger_formatter)
    logger_console_handler.setFormatter(logger_formatter)

    logger.addHandler(logger_file_handler)
    logger.addHandler(logger_console_handler)


setupLogger()
setup_env()

with context:
    run_env()
