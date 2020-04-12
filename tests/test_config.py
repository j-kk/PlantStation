import datetime
import pathlib
import uuid

import gpiozero
import mock
import pytest

import PlantStation
from core.config import Config, EnvironmentConfig
# noinspection PyUnresolvedReferences
from .context import create_plant_simple, cleanup


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

    @pytest.fixture(params=[0, 1, 10, 20])
    def multiple_config_creator(self, request):
        env_config = EnvironmentConfig('test_env', path=None, debug=True, dry_run=True)
        assert 0 <= request.param
        for pin in range(4, 4 + request.param):
            plant = create_plant_simple(env_config, pin)
            env_config.update_plant_section(plant)

        assert len(env_config.list_plants()) == request.param
        return env_config

    def config_creator_plants(self, n_plants, path=None):
        env_config = EnvironmentConfig('test_env', path=path, debug=True, dry_run=True)
        assert 0 <= n_plants
        for pin in range(4, 4 + n_plants):
            plant = create_plant_simple(env_config, pin)
        return env_config

    def test_simple_config(self, multiple_config_creator):
        config = multiple_config_creator
        assert config.active_limit == config.pin_manager.active_limit
        assert config.pin_manager.active_limit == PlantStation.core.ext.pins.DEFAULT_ACTIVE_LIMIT
        assert config.pin_manager.working_pumps == 0
        assert isinstance(config.pin_manager.pin_factory, gpiozero.pins.mock.MockFactory)
        assert config.debug
        with pytest.raises(KeyError):
            r = config.silent_hours

        config.silent_hours = (datetime.time(22, 00), datetime.time(7, 00))
        assert isinstance(config.silent_hours[0], datetime.time)
        assert isinstance(config.silent_hours[1], datetime.time)

    def test_too_many_plants(self):
        with pytest.raises(gpiozero.exc.PinInvalidPin):
            self.config_creator_plants(100)

    def test_the_same_pin(self):
        config = self.config_creator_plants(0)
        with pytest.raises(gpiozero.exc.GPIOPinInUse):
            plant = create_plant_simple(config, 5)
            assert plant.gpioPinNumber == 'GPIO5'
            plant = create_plant_simple(config, 5)

    def test_config_with_plants(self):
        config = self.config_creator_plants(10)
        assert len(config.list_plants()) == 10
