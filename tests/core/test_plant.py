import string
import datetime
from random import Random

import pytest

from core import EnvironmentConfig
from .context import MAX_GPIO_NUMBER, simple_env_config, create_plant_simple, MIN_GPIO_NUMBER
from PlantStation.core import Plant


@pytest.fixture(params=[(pin, typ) for pin in range(MIN_GPIO_NUMBER, MAX_GPIO_NUMBER) for typ in range(2)])
def GPIOnumber(request):
    if request.param[1]:
        return 'GPIO' + str(request.param[0])
    else:
        return 'BOARD' + str(request.param[0])


def test_invalid_plants(simple_env_config, GPIOnumber):
    NEG_DT = datetime.timedelta(seconds=-1)
    ZERO_DT = datetime.timedelta(seconds=0)
    TIMEDELTA_SHORT = datetime.timedelta(seconds=5)
    TIMEDELTA_LONG = datetime.timedelta(seconds=15)
    FUTURE = datetime.datetime.now() + datetime.timedelta(days=1)
    with pytest.raises(ValueError):
        plant = Plant(plantName='', envConfig= simple_env_config, gpioPinNumber=GPIOnumber,
                             wateringDuration=TIMEDELTA_SHORT, wateringInterval=TIMEDELTA_LONG, isActive=True)
    with pytest.raises(KeyError):
        plant = Plant(plantName='test', envConfig= None, gpioPinNumber=GPIOnumber,
                             wateringDuration=TIMEDELTA_SHORT, wateringInterval=TIMEDELTA_LONG, isActive=True)
    with pytest.raises(ValueError):
        plant = Plant(plantName='test', envConfig= simple_env_config, gpioPinNumber='aaa',
                             wateringDuration=TIMEDELTA_SHORT, wateringInterval=TIMEDELTA_LONG, isActive=True)

    with pytest.raises(ValueError):
        plant = Plant(plantName='test', envConfig= simple_env_config, gpioPinNumber=GPIOnumber,
                             wateringDuration=ZERO_DT, wateringInterval=TIMEDELTA_LONG, isActive=True)
    with pytest.raises(ValueError):
        plant = Plant(plantName='test', envConfig= simple_env_config, gpioPinNumber=GPIOnumber,
                             wateringDuration=NEG_DT, wateringInterval=TIMEDELTA_LONG, isActive=True)
    with pytest.raises(ValueError):
        plant = Plant(plantName='test', envConfig= simple_env_config, gpioPinNumber=GPIOnumber,
                             wateringDuration=TIMEDELTA_SHORT, wateringInterval=ZERO_DT, isActive=True)
    with pytest.raises(ValueError):
        plant = Plant(plantName='test', envConfig= simple_env_config, gpioPinNumber=GPIOnumber,
                             wateringDuration=TIMEDELTA_SHORT, wateringInterval=NEG_DT, isActive=True)
    with pytest.raises(ValueError):
        plant = Plant(plantName='test', envConfig= simple_env_config, gpioPinNumber=GPIOnumber,
                             wateringDuration=TIMEDELTA_SHORT, wateringInterval=TIMEDELTA_LONG,
                             lastTimeWatered=FUTURE, isActive=True)
