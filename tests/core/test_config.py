import datetime
import pathlib
import uuid

import gpiozero
import mock
import pytest

import PlantStation
from PlantStation.core.config import Config, EnvironmentConfig
# noinspection PyUnresolvedReferences
from .context import create_plant_simple, simple_env_config, add_plants_to_config, cleanup


class ConfigSchema:

    def config_creator(self, path=None) -> Config:
        pass

    def test_config_no_path(self):
        config = self.config_creator(path=None)
        with pytest.raises(ValueError):
            config.read()
        with pytest.raises(ValueError):
            config.write()

    def test_files_not_found(self, tmp_path):
        file = pathlib.Path(tmp_path).joinpath(pathlib.Path(uuid.uuid4().__str__() + '.cfg'))
        config = self.config_creator(path=file)
        with pytest.raises(FileNotFoundError):
            config.read()
        config.write()
        assert file.exists()

    def test_filepath_empty(self):
        file = pathlib.Path("")
        with pytest.raises(ValueError):
            config = self.config_creator(path=file)

    def test_permission_error(self):  # TODO
        pass

    def test_write_all_ok(self, tmp_path):
        path = pathlib.Path(tmp_path).joinpath(pathlib.Path('file.cfg'))
        config = self.config_creator(path=path)
        config.write()
        assert path.exists()

    def test_write_all_ok2(self, tmp_path):
        path = pathlib.Path(tmp_path).joinpath(pathlib.Path('file.cfg'))
        config = self.config_creator(path=None)
        config.path = path
        config.write()
        assert path.exists()

    def test_move_config(self, tmp_path):
        path1 = pathlib.Path(tmp_path).joinpath(pathlib.Path('file1.cfg'))
        path2 = pathlib.Path(tmp_path).joinpath(pathlib.Path('file2.cfg'))
        config = self.config_creator(path=path1)
        config.write()
        config.path = path2
        assert not path1.exists()
        assert path2.exists()


class TestConfig(ConfigSchema):

    @mock.patch("logging.Logger")
    def config_creator(self, mock_logger: mock.MagicMock, path) -> Config:
        return Config(logger=mock_logger, path=path, dry_run=True)


class TestEnvironmentConfig(ConfigSchema):

    def config_creator(self, path=None) -> Config:
        return EnvironmentConfig('test_env', path=path, debug=True, dry_run=True)


    def test_simple_config(self, simple_env_config):
        config = simple_env_config
        assert config.active_limit == config._pin_manager.active_limit
        assert config._pin_manager.active_limit == PlantStation.core.ext.pins.DEFAULT_ACTIVE_LIMIT
        assert config._pin_manager.working_pumps == 0
        assert isinstance(config._pin_manager.pin_factory, gpiozero.pins.mock.MockFactory)
        assert config.debug
        with pytest.raises(KeyError):
            r = config.silent_hours

        config.silent_hours = (datetime.time(22, 00), datetime.time(7, 00))
        assert isinstance(config.silent_hours[0], datetime.time)
        assert isinstance(config.silent_hours[1], datetime.time)
        config.active_limit = 2
        assert config.active_limit == 2

    def test_too_many_plants(self, simple_env_config):
        with pytest.raises(gpiozero.exc.PinInvalidPin):
            for i in range(100):
                create_plant_simple(simple_env_config, i)

    def test_the_same_pin(self, simple_env_config):
        config = simple_env_config
        with pytest.raises(gpiozero.exc.GPIOPinInUse):
            plant = create_plant_simple(config, 5)
            assert plant.gpioPinNumber == 'GPIO5'
            plant = create_plant_simple(config, 5)

    def test_config_with_plants(self, simple_env_config, add_plants_to_config):
        pass #fixtures tests everything