import signal
import daemon
import lockfile
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

context.files_preserve = [LOGFILE_PATH]

setup_env()

with context:
    run_env()
