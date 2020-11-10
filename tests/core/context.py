import datetime
import pathlib

import pytest

from PlantStation.core import EnvironmentConfig, Environment, Plant

MIN_GPIO_NUMBER = 4
MAX_GPIO_NUMBER = 53

PLANT_SET_COUNT = 10

TIMEDELTA_SHORT = datetime.timedelta(seconds=1)
TIMEDELTA_LONG = datetime.timedelta(seconds=20)

MORNING = datetime.time(7, 0)
EVENING = datetime.time(22, 0)
MIDNIGHT = datetime.time(0, 0)

plants = []


@pytest.fixture(autouse=True)
def cleanup(request):
    """Cleanup a testing directory once we are finished."""

    def clean_plants():
        for plant in plants:
            del plant
        plants.clear()

    request.addfinalizer(clean_plants)


@pytest.fixture()
def silent_hour_now(monkeypatch):
    class mydatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=1), MIDNIGHT)

    monkeypatch.setattr(datetime, 'datetime', mydatetime)


@pytest.fixture(params=[True, False])
def simple_env_config(request, tmp_path):
    if not request.param:
        tmp_path = None
    else:
        tmp_path = pathlib.Path(tmp_path).joinpath(pathlib.Path('test_env.cfg'))
    return EnvironmentConfig('test_env', path=tmp_path, debug=True, dry_run=True)


@pytest.fixture()
def complete_env_config(request, simple_env_config):
    env = simple_env_config
    env.silent_hours = (EVENING, MORNING)
    assert env.silent_hours[0] == EVENING
    assert env.silent_hours[1] == MORNING
    return env


def create_plant_simple(env_config, pin, *args, **kwargs):
    plant = Plant(plantName='test_plant_' + str(pin), envConfig=env_config, wateringDuration=TIMEDELTA_SHORT,
                  wateringInterval=TIMEDELTA_LONG, gpioPinNumber='GPIO' + str(pin), *args, **kwargs)
    plants.append(plant)
    assert plant.isActive == kwargs.get('isActive', True)
    assert plant.plantName == 'test_plant_' + str(pin)
    assert plant.lastTimeWatered == datetime.datetime.min
    assert plant.wateringInterval.total_seconds() == TIMEDELTA_LONG.total_seconds()
    assert plant.wateringDuration.total_seconds() == TIMEDELTA_SHORT.total_seconds()
    assert plant.gpioPinNumber == 'GPIO' + str(pin)
    return plant


@pytest.fixture(params=list(range(PLANT_SET_COUNT)))
def add_plants_to_config(request, simple_env_config):
    plants = []
    for pin in range(MIN_GPIO_NUMBER, MIN_GPIO_NUMBER + request.param):
        plant = Plant(plantName='test_plant_' + str(pin), envConfig=simple_env_config,
                      wateringDuration=TIMEDELTA_SHORT, wateringInterval=TIMEDELTA_LONG,
                      gpioPinNumber='GPIO' + str(pin))
        del plant
    assert len(simple_env_config.list_plants()) == request.param


@pytest.yield_fixture()
def create_env(request, complete_env_config, add_plants_to_config):
    env = Environment(complete_env_config)
    assert len(env.config.list_plants()) == len(env.plants)
    yield env
    del env
