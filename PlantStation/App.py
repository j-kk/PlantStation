import signal
import daemon
import lockfile
from PlantStation.Environment import Environment
from PlantStation.Configure import GLOBAL_CFG_PATH, LOGFILE_PATH


class App(object):
    _mainEnvironment: Environment
    _config_path: str
    _debug: bool

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

        # init daemon context, signal map
        self._context = daemon.DaemonContext(
            working_directory='/etc/plantstation',
            umask=0o022,
            pidfile=lockfile.FileLock('/var/run/plantstation'),
            stdout=self._logfile_path
        )

        self._context.signal_map = {
            signal.SIGTERM: self.stop_env,
            signal.SIGINT: self.stop_env,
            signal.SIGHUP: self.stop_env,
        }

    def run(self):
        with self._context:
            self.run_env()
