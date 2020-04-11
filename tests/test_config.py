import pathlib

import gpiozero
import pytest

from .context import create_config, create_plant, cleanup


def test_simple_config():
    create_config(0)

def test_too_many_plants():
    with pytest.raises(gpiozero.exc.PinInvalidPin):
        create_config(100)

def test_the_same_pin():
    config = create_config(0)
    with pytest.raises(gpiozero.exc.GPIOPinInUse):
        plant = create_plant(config, 5)
        config.add_plant(plant)
        plant = create_plant(config, 5)
        config.add_plant(plant)



def test_config_with_plants():
    create_config(10)

def test_config_and_save(tmp_path):
    path = pathlib.Path(tmp_path).joinpath(pathlib.Path('file.cfg'))
    config = create_config(10)
    config.path = path
    config.write()
    assert path.exists()

def test_config_and_save_wrong_filename(tmp_path):
    path = pathlib.Path(tmp_path).joinpath(pathlib.Path('file.fg'))
    config = create_config(10)
    with pytest.raises(ValueError):
        config.path = path

def test_config_and_save_directory(tmp_path):
    path = pathlib.Path(tmp_path)
    config = create_config(10)
    with pytest.raises(IsADirectoryError):
        config.path = path
