import logging
import datetime
from PlantStation.Plant import Plant
from PlantStation.helpers.format_validators import parse_time
from PlantStation.helpers.config import Config
from PlantStation.Tasks import ShouldWaterTask
from PlantStation.Tasks import TaskPool


class Environment(object):
    """Environment is a set of plants.

    Class holds information about plants. It is responsible for scheduling
    all the actions, as based in environment.cfg file.

    Attributes:
    -----------

    name  : str
        Name of the environment (default main)

    Methods:
    --------

    read_config()
        Reads environment config file

    schedule_monitoring()
        Sets up event scheduler - Obligatory before starting event scheduler

    start()
        Starts to look after plants - starting event scheduler

    """
    name: str
    config: Config
    pool: TaskPool
    _plants: [Plant] = []
    _logger: logging.Logger
    _dry_run: bool
    working_hours: [datetime.time]

    def __init__(self, config_path: str, env_name: str = "main", dry_run: bool = False):
        """
        Args:
            name (str): Env name
        """
        self._cfg_path = config_path
        self._dry_run = dry_run
        self.name = env_name
        self.pool = TaskPool(env_name)
        self._logger = logging.getLogger(__package__ + "." + self.name)

        self._logger.info(f'Created {self.name} environment')
        self.config = Config(self._logger, cfg_paths=[self._cfg_path])
        self.config.read()
        self._read_config()

    def _read_config(self):
        """Reads environment config file

        Reads config file from location defined by self._cfg_paths
        and if provided data are correct, creates Plants with provided data
        """
        # read global section
        self._logger.info('Reading config file: %s', self._cfg_path)

        if self.config.cfg_parser['GLOBAL']['workingHours'] == 'True':
            if 'silent_hours_begin' in self.config.cfg_parser['GLOBAL'] and 'silent_hours_end' in self.config.cfg_parser['GLOBAL']:
                self.working_hours = []
                self.working_hours.append(datetime.datetime.strptime(self.config.cfg_parser['GLOBAL']['workingHoursBegin'], '%H:%M'))
                self.working_hours.append(datetime.datetime.strptime(self.config.cfg_parser['GLOBAL']['workingHoursEnd'], '%H:%M'))
            else:
                self._logger.error(f'No silent hours schedule')
        else:
            self.working_hours = []

        # read_plants
        for section in self.config.cfg_parser:
            if section == 'DEFAULT':
                continue
            if section != 'GLOBAL':
                self._logger.debug('Found new section: %s', section)
                try:
                    params = {
                        'plantName': str(section),
                        'wateringDuration': datetime.timedelta(seconds=int(self.config.cfg_parser[section]['wateringDuration'])),
                        'wateringInterval': parse_time(time_str=self.config.cfg_parser[section]['wateringInterval']),
                        'gpioPinNumber': str(self.config.cfg_parser[section]['gpioPinNumber'])}
                    if self.config.cfg_parser[section]['lastTimeWatered'] != '':
                        time_str = self.config.cfg_parser[section]['lastTimeWatered']
                        params['lastTimeWatered'] = datetime.datetime.strptime(time_str, '%Y-%m-%d %X')
                    else:
                        params['lastTimeWatered'] = datetime.datetime.min
                    new_plant = Plant(**params, envName=self.name, dry_run=self._dry_run)
                    self._logger.info(
                        f'Found new plant: {params["plantName"]}, pin: {params["gpioPinNumber"]}')
                    self._plants.append(new_plant)
                except KeyError as err:
                    self._logger.error(
                        f'{self._cfg_path}: Failed to read {section} section - '
                        f'option not found {str(err)}')
                except ValueError as err:
                    self._logger.error(
                        f'{self._cfg_path}: Failed to read {section} section {err}')
                except Exception as err:
                    self._logger.error(
                        f'{self._cfg_path} Failed to read {section} section {str(err)}')
    
    def schedule_monitoring(self) -> None:
        """Sets up event scheduler - Obligatory before starting event scheduler

        Schedules to check all plants
        """
        self._logger.debug('Scheduling monitoring')
        for plant in self._plants:
            self.pool.add_task(ShouldWaterTask(plant, self))
        self._logger.debug(f'Scheduled monitoring - OK')

    def start(self) -> None:
        """Starts to look after plants
        Starts pool tasks
        """
        self._logger.info('Starting scheduler')
        self.pool.start()


