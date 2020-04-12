import datetime
import pathlib

import pytest

from PlantStation.core import Plant
from core import EnvironmentConfig

MIN_GPIO_NUMBER = 4
MAX_GPIO_NUMBER = 53

TIMEDELTA_SHORT = datetime.timedelta(seconds=5)
TIMEDELTA_LONG = datetime.timedelta(seconds=15)

plants = []


@pytest.fixture(autouse=True)
def cleanup(request):
    """Cleanup a testing directory once we are finished."""

    def clean_plants():
        for plant in plants:
            plant.isActive = False
            plant.delete()
        for plant in plants:
            plants.remove(plant)  # TODO how to make it cleaner?

    request.addfinalizer(clean_plants)


@pytest.fixture(params=[True, False])
def simple_env_config(request, tmp_path):
    if not request.param:
        tmp_path = None
    else:
        tmp_path = pathlib.Path(tmp_path).joinpath(pathlib.Path('test_env.cfg'))
    return EnvironmentConfig('test_env', path=tmp_path, debug=True, dry_run=True)


def create_plant(*args, **kwargs):
    plant = Plant(*args, **kwargs)
    plants.append(plant)
    return plant


def create_plant_simple(env_config, pin, *args, **kwargs):
    plant = create_plant(plantName='test_plant_' + str(pin), envConfig=env_config, wateringDuration=TIMEDELTA_SHORT,
                         wateringInterval=TIMEDELTA_LONG, gpioPinNumber='GPIO' + str(pin), *args, **kwargs)
    assert plant.isActive == kwargs.get('isActive', True)
    assert plant.plantName == 'test_plant_' + str(pin)
    assert plant.lastTimeWatered == datetime.datetime.min
    assert plant.wateringInterval == TIMEDELTA_LONG
    assert plant.wateringDuration == TIMEDELTA_SHORT
    assert plant.gpioPinNumber == 'GPIO' + str(pin)
    return plant
