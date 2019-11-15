import signal
import daemon
import lockfile
import logging
from os import getcwd
from . import Environment


class App(object):
    _mainEnvironment: Environment.Environment
    _config_path: str

    def __init__(self, config_path: str = '/etc/plantstation/enviroment.cfg'):
        self._config_path = config_path
        self.setupLogger()
        self._mainEnvironment = Environment.Environment(self._config_path)
        self._mainEnvironment.schedule_monitoring()

    def run_env(self):
        self._mainEnvironment.start()

    def stop_env(self):
        self._mainEnvironment.stop()

    def setupLogger(self) -> None:
        logger = logging.getLogger('PlantStation')
        logger.setLevel(logging.DEBUG)

        logger_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        logger_console_handler = logging.StreamHandler()
        logger_console_handler.setFormatter(logger_formatter)

        logger.addHandler(logger_console_handler)

    def run(self):
        self.run_env()



class StandaloneApp(App):

    def __init__(self, config_path: str = '/etc/plantstation/enviroment.cfg',
                 logfile_path: str = '/var/log/plantstation.log'):
        super(config_path)
        self._context = daemon.DaemonContext(
            working_directory='/etc/plantstation',
            umask=0o022,
            pidfile=lockfile.FileLock('/var/run/plantstation'),
            stdout=self._logfile_path
        )

        self._context.signal_map = {
            signal.SIGTERM: self.stop_env,
            signal.SIGHUP: 'terminate'
        }
        self.setupLogger() #TODO check

    def setupLogger(self) -> None:
        """Sets up daemon logger

        """
        self._context.files_preserve = [self._logfile_path]

        logger = logging.getLogger('PlantStation')
        logger.setLevel(logging.INFO)

        logger_file_handler = logging.FileHandler(self._logfile_path)
        logger_file_handler.setLevel(logging.INFO)

        logger_console_handler = logging.StreamHandler()
        logger_console_handler.setLevel(logging.ERROR)

        logger_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logger_file_handler.setFormatter(logger_formatter)
        logger_console_handler.setFormatter(logger_formatter)

        logger.addHandler(logger_file_handler)
        logger.addHandler(logger_console_handler)

    def run(self):
        with self._context:
            self.run_env()


if __name__ == '__main__':
    app = App(getcwd() + '/environment.cfg')
    signal.signal(signal.SIGHUP, app.stop_env)
    signal.signal(signal.SIGQUIT, app.stop_env)
    signal.signal(signal.SIGINT, app.stop_env)
    app.run()


