import mock as mock

from PlantStation.configurer.Configure import EnvironmentCreator
from tests.configure.configure_ans import configureAnswers


@mock.patch('builtins.open')
@mock.patch('PlantStation.configurer.Configure.prompt')
def test_env_config(mock_input, mock_write):
    input_config = configureAnswers('test01', 'Current location', False, '1', True, 'Kwiatek 0123', '10',
                                    '10D 01:01:01', None, None)
    input_config_dict_with_none = input_config.__dict__
    input_config_dict = {k: v for k, v in input_config_dict_with_none.items() if v is not None}
    mock_input.return_value = input_config_dict
    expected_calls = input_config.expected_output01(last_time_watered='0001-01-01 00:00:00',
                                                    water_interval='10 days, 1:01:01', water_dur='0:00:10')
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
    print(calls_args)
    expected_calls = input_config.expected_output02(last_time_watered='0001-01-01 00:00:00',
                                                    water_interval='3:00:21', water_dur='0:00:15')
    for call, expected_call in zip(calls_args, expected_calls):
        assert call == expected_call
