import os
import sys

import mock as mock
import pytest
from gpiozero import GPIOZeroError

from PlantStation.configurer.Configure import EnvironmentCreator, Configurer
from tests.configure.configure_ans import configureAnswers


########################## EnvironmentCreator test


@mock.patch('builtins.open')
@mock.patch('PlantStation.configurer.Configure.prompt')
def test_env_config(mock_input, mock_write):
    input_config = configureAnswers('test01', 'Current location', False, '1', True, 'Kwiatek 0123', '10',
                                    '10D 01:01:01', None, None)
    input_config_dict_with_none = input_config.__dict__
    input_config_dict = {k: v for k, v in input_config_dict_with_none.items() if v is not None}
    mock_input.return_value = input_config_dict
    expected_calls = input_config.expected_output01(last_time_watered='0001-01-01 00:00:00',
                                                    water_interval='10D 01:01:01', water_dur='10')
    EnvironmentCreator(dry_run=True)
    calls_args = [str(call.args[0]).strip('\n') for call in mock_write.mock_calls if call.args[0] != '\n']
    for call, expected_call in zip(calls_args, expected_calls):
        assert call == expected_call


@mock.patch('builtins.open', create=True)
@mock.patch('PlantStation.configurer.Configure.prompt')
def test_env_config_with_working_hours(mock_input, mock_write):
    input_config = configureAnswers('test02', 'Current location', True, '2', True, 'Pan Aloes', '15',
                                    '0D 03:00:21', '10:22', '15:33')
    mock_input.return_value = input_config.__dict__
    EnvironmentCreator(dry_run=True)
    calls_args = [str(call.args[0]).strip('\n') for call in mock_write.mock_calls if call.args[0] != '\n']
    expected_calls = input_config.expected_output02(last_time_watered='0001-01-01 00:00:00',
                                                    water_interval='0D 03:00:21', water_dur='15')
    for call, expected_call in zip(calls_args, expected_calls):
        assert call == expected_call


@mock.patch('PlantStation.configurer.Configure.DigitalOutputDevice')
@mock.patch('builtins.open', create=True)
@mock.patch('PlantStation.configurer.Configure.prompt')
def test_configure_pin_error(mock_input, mock_write, mock_pin_error):
    mock_pin_error.side_effect = GPIOZeroError
    input_config = configureAnswers('test03', 'System location', True, '5', True, 'Plant :)', '15',
                                    '0D 03:00:21', '10:22', '15:33')
    mock_input.return_value = input_config.__dict__
    with pytest.raises(GPIOZeroError):
        EnvironmentCreator(dry_run=True)


@mock.patch('builtins.open', create=True)
@mock.patch('PlantStation.configurer.Configure.prompt')
def test_configure_path_specify(mock_input, mock_write):
    input_config = configureAnswers('test04', 'Specify', True, '5', True, 'Rose', '4',
                                    '5D 00:00:00', '10:00', '18:35')
    input_config_dict = input_config.__dict__
    input_config_dict['cfg_path'] = os.getcwd()
    mock_input.return_value = input_config.__dict__
    calls_args = [str(call.args[0]).strip('\n') for call in mock_write.mock_calls if call.args[0] != '\n']
    expected_calls = input_config.expected_output02(last_time_watered='0001-01-01 00:00:00',
                                                    water_interval='5D 0:00:00', water_dur='4')
    for call, expected_call in zip(calls_args, expected_calls):
        assert call == expected_call
    EnvironmentCreator(dry_run=True)


########################## ServiceCreatorConfig test
# TODO


########################## Configurer test

def test_configurer_wrong_command():
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        Configurer()
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 1


@mock.patch("PlantStation.configurer.Configure.EnvironmentCreator")
def test_configurer_config_with_error(mock_env_creator):
    testargs = ["PlantSetup", "config", "-m"]
    with mock.patch.object(sys, 'argv', testargs):
        mock_env_creator.side_effect = GPIOZeroError
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            Configurer()
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1


@mock.patch('builtins.open', create=True)
@mock.patch('PlantStation.configurer.Configure.prompt')
def test_configurer_config_ok(mock_input, mock_write):
    testargs = ["PlantSetup", "config", "-m"]
    with mock.patch.object(sys, 'argv', testargs):
        input_config = configureAnswers('test05', 'System location', True, '2', True, 'Plant12345', '3',
                                        '7D 00:00:00', '08:30', '16:00')
        mock_input.return_value = input_config.__dict__
        expected_calls = input_config.expected_output02(last_time_watered='0001-01-01 00:00:00',
                                                        water_interval='7D 00:00:00', water_dur='3',
                                                        file='System location')
        Configurer()
        calls_args = [str(call.args[0]).strip('\n') for call in mock_write.mock_calls if call.args[0] != '\n']
        for call, expected_call in zip(calls_args, expected_calls):
            assert call == expected_call
