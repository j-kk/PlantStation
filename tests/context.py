import datetime
import os
import sys

import pytest

from PlantStation.core import EnvironmentConfig, Plant
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

TIMEDELTA_SHORT = datetime.timedelta(seconds=5)
TIMEDELTA_LONG  = datetime.timedelta(seconds=15)

plants = []

@pytest.fixture(autouse=True)
def cleanup(request):
    """Cleanup a testing directory once we are finished."""
    def clean_plants():
        for plant in plants:
            plant._pumpSwitch.close() #TODO
    request.addfinalizer(clean_plants)

def create_plant(env_config, pin):
    plant= Plant('test_plant_' + str(pin) , envConfig=env_config, wateringDuration=TIMEDELTA_SHORT,
          wateringInterval=TIMEDELTA_LONG, gpioPinNumber='GPIO' + str(pin))
    plants.append(plant)
    return plant


def create_config(n_plants):
    env_config = EnvironmentConfig('test_env', debug=True, dry_run=True)
    #todo gpioPinNumber from test_helpers
    assert 0 <= n_plants
    plants = []
    for pin in range(4, 4 + n_plants):
        plants.append(create_plant(env_config, pin))
        env_config.add_plant(plants[-1])
    return env_config