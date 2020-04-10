import datetime
import os
import sys
from PlantStation.core import EnvironmentConfig, Plant
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

TIMEDELTA_SHORT = datetime.timedelta(seconds=5)
TIMEDELTA_LONG  = datetime.timedelta(seconds=15)

def create_config(tmp_path, n_plants):
    env_config = EnvironmentConfig('test_env', debug=True, dry_run=True)
    #todo gpioPinNumber from test_helpers
    assert 0 < n_plants < 37
    plants = []
    for pin in range(4, 4 + n_plants):
        plants.append(Plant('test_plant_' + str(pin) , envConfig=env_config, wateringDuration=TIMEDELTA_SHORT,
                            wateringInterval=TIMEDELTA_LONG, gpioPinNumber='GPIO' + str(pin)))
        env_config.add_plant(plants[-1])
    env_config.path(tmp_path)
    return env_config