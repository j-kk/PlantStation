import pytest
from PlantStation.core.helpers.format_validators import *
from random import Random

__author__ = "Jakub"
__copyright__ = "Jakub"
__license__ = "mit"

rand_seed = 1023


@pytest.mark.basic
def test_basic():
    assert parse_time('10D 09:09:09').total_seconds() == datetime.timedelta(days=10, hours=9, minutes=9,
                                                                            seconds=9).total_seconds()
    assert parse_time('0D 00:00:00').total_seconds() == datetime.timedelta(seconds=0).total_seconds()

    with pytest.raises(ValueError):
        parse_time('10D 9:09:09')


@pytest.mark.slow
def test_random():
    random = Random(rand_seed)

    for it in range(0, 10000):
        days = random.randint(0, 99)
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        sec = random.randint(0, 59)
        parsed = parse_time('{}D {}:{}:{}'.format(days, str(hour).zfill(2), str(minute).zfill(2), str(sec).zfill(2)))
        td = datetime.timedelta(days=days, hours=hour, minutes=minute, seconds=sec)
        assert parsed == td


@pytest.mark.extended
def test_value_error():
    with pytest.raises(ValueError):
        parse_time('0D 09:9:09')

    with pytest.raises(ValueError):
        parse_time('0D 09:911:11')

    with pytest.raises(ValueError):
        parse_time('0D -1:91:11')

    with pytest.raises(ValueError):
        parse_time('-1D 09:11:111')

    with pytest.raises(ValueError):
        parse_time('0D :09:11:81')

    with pytest.raises(ValueError):
        parse_time('0 D 09:11:81')

    with pytest.raises(ValueError):
        parse_time('0D 0:3:11:81')

    with pytest.raises(ValueError):
        parse_time('0D 93:11::81')

    with pytest.raises(ValueError):
        parse_time('0D 09:11   : 81')

    with pytest.raises(ValueError):
        parse_time('0D 03: 11:81')

    with pytest.raises(ValueError):
        parse_time('0D 23 :11:81')

    with pytest.raises(ValueError):
        parse_time('0D ::')


@pytest.mark.extended
def test_board():
    for i in range(1, 40):
        assert is_gpio(f'BOARD{i}')
        assert is_gpio(f'GPIO{i}')

    with pytest.raises(ValueError):
        assert is_gpio('BOARD 30')

    with pytest.raises(ValueError):
        assert is_gpio('BOARD 30 ')
    with pytest.raises(ValueError):
        assert is_gpio('BOARD 30')
    with pytest.raises(ValueError):
        assert is_gpio('GPIO30 ')
    with pytest.raises(ValueError):
        assert is_gpio('GPIO3 0')
