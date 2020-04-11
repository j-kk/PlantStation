import datetime

import pytest

from PlantStation.core import Plant

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

