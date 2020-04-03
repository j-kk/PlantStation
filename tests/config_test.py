import mock as mock

from PlantStation.configurer.Configure import EnvironmentCreator

input_config01 = {'envName': 'test01', 'cfg_location': 'Current location', 'workingHours': False, 'ActiveLimit': 1,
                  'working': True, 'plantName': 'Pan Aloes', 'wateringDuration': 10, 'wateringInterval': '10D 01:01:01'}


@mock.patch('builtins.open', create=True)
@mock.patch('PlantStation.configurer.Configure.prompt', return_value=input_config01)
def test_env_config(mock_input, mock_write):
    expected_config_file = ['/home/misia/Programowanie/PlantStation/tests/test01.cfg', '[GLOBAL]\n',
                            'env_name = test01\n', 'workingHours = False\n', 'ActiveLimit = 1\n', '\n', '[Pan Aloes]\n',
                            'plantName = Pan Aloes\n', 'wateringDuration = 10\n', 'wateringInterval = 10D 01:01:01\n',
                            'lastTimeWatered = \n', 'gpioPinNumber = GPIO27\n', 'isActive = True\n', '\n']
    EnvironmentCreator(mock=True, dry_run=True)
    for call, expected_call in zip(mock_write.mock_calls, expected_config_file):
        assert str(call.args[0]) == expected_call
