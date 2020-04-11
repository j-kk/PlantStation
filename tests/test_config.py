import PlantStation
import pathlib

import gpiozero
import pytest

from .context import create_config, create_plant, cleanup


def test_simple_config():
    config = create_config(0)
    assert config.active_limit == config.pin_manager.active_limit
    assert config.pin_manager.active_limit == PlantStation.core.ext.pins.DEFAULT_ACTIVE_LIMIT
    assert config.pin_manager.working_pumps == 0
    assert isinstance(config.pin_manager.pin_factory, gpiozero.pins.mock.MockFactory)
    assert config.debug
    assert len(config.list_plants()) == 0
    assert config.silent_hours == None


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
    config = create_config(10)
    assert len(config.list_plants()) == 10
    


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
