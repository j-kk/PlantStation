import datetime
import string
from random import Random

import pytest

from PlantStation.core import Plant


def _random_string(stringLength=10):
    """Generate a random string of fixed length """
    rnd = Random(1023)
    letters = string.ascii_uppercase
    digits = string.digits
    return ''.join(rnd.choice(letters + digits) for _ in range(stringLength))


def _generate_GPIO(is_correct: bool = True):
    random = Random(1023)
    if is_correct:
        if random.getrandbits(1):
            return 'GPIO01'
        else:
            return 'BOARD01'
    else:
        return _random_string(5)


@pytest.mark.parametrize("seed", [x for x in range(0, 100)])
def test_plants(seed: int):
    dt_s = datetime.timedelta(seconds=15)

    rnd = Random(seed)
    for x in range(10):
        pp = Plant(plantName='P' + str(x),
                   gpioPinNumber=_generate_GPIO(True),
                   wateringDuration=dt_s * rnd.randint(1, 2),
                   wateringInterval=dt_s * rnd.randint(1, 2),
                   lastTimeWatered=datetime.datetime.now() + dt_s * rnd.randint(-1, 0))


@pytest.mark.parametrize("seed", [x for x in range(0, 100)])
def test_invalid_arguments(seed: int):
    rnd = Random(seed)

    for x in range(0, 10):
        params = {
            "plantName": ("Plant " + str(x)),
            "envName": "test",
            "gpioPinNumber": _generate_GPIO(True),
            "wateringDuration": datetime.timedelta(seconds=rnd.randint(1, 100)),
            "wateringInterval": datetime.timedelta(seconds=rnd.randint(1, 100)),
            "dry_run": True
        }
        opt = rnd.randint(0, 3)
        if opt == 0:
            params["gpioPinNumber"] = _generate_GPIO(False)
        elif opt == 1:
            params["wateringDuration"] = datetime.timedelta(seconds=-rnd.randint(0, 100000))
        elif opt == 2:
            params["wateringInterval"] = datetime.timedelta(seconds=-rnd.randint(0, 100000))
        else:
            params["lastTimeWatered"] = datetime.datetime.now() + datetime.timedelta(seconds=rnd.randint(1, 100))

        with pytest.raises(ValueError):
            Plant(**params)

    for x in range(0, 10):
        params = {
            "plantName": ("Plant " + str(x)),
            "envName": "test",
            "gpioPinNumber": _generate_GPIO(True),
            "wateringDuration": datetime.timedelta(seconds=rnd.randint(1, 100)),
            "wateringInterval": datetime.timedelta(seconds=rnd.randint(1, 100)),
            "dry_run": False
        }
        from gpiozero import GPIOZeroError
        with pytest.raises(GPIOZeroError):
            Plant(**params)

