import os
import mock as mock

from PlantStation.configurer.Configure import EnvironmentCreator

input_config01 = {'envName': 'test01', 'cfg_location': 'Current location', 'workingHours': False, 'ActiveLimit': 1,
                  'working': True, 'plantName': 'Pan Aloes', 'wateringDuration': 10, 'wateringInterval': '10D 01:01:01'}

input_config02 = {'envName': 'test02', 'cfg_location': 'Current location', 'workingHours': True, 'ActiveLimit': 2,
                  'working': True, 'plantName': 'Grubson', 'wateringDuration': 15, 'wateringInterval': ' 03:00:21',
                  'workingHoursBegin': "10:22", "workingHoursEnd": "15:33"}

# input_config03 = {'envName': 'test03', 'cfg_location': 'Current location', 'workingHours': True, 'ActiveLimit': 2,
#                   'working': True}
#
# input_config03a = {'envName': 'test03', 'cfg_location': 'Current location', 'workingHours': True, 'ActiveLimit': 2,
#                    'plantName': 'plantA', 'wateringDuration': 2, 'wateringInterval': '5D 03:00:21', 'working': True}
#
# input_config03b = {'envName': 'test03', 'cfg_location': 'Current location', 'workingHours': True, 'ActiveLimit': 2,
#                    'plantName': 'plantB', 'wateringDuration': 1.5, 'wateringInterval': '3D 03:03:03', 'working': True}


@mock.patch('builtins.open', create=True)
@mock.patch('PlantStation.configurer.Configure.prompt', return_value=input_config01)
def test_env_config(mock_input, mock_write):
    cwd = os.getcwd()
    expected_config_file = [cwd + '/test01.cfg', '[GLOBAL]\n',
                            'env_name = test01\n', 'workingHours = False\n', 'ActiveLimit = 1\n', '\n', '[Pan Aloes]\n',
                            'plantName = Pan Aloes\n', 'wateringDuration = 10\n', 'wateringInterval = 10D 01:01:01\n',
                            'lastTimeWatered = \n', 'gpioPinNumber = GPIO27\n', 'isActive = True\n', '\n']
    EnvironmentCreator(mock=True, dry_run=True)
    for call, expected_call in zip(mock_write.mock_calls, expected_config_file):
        assert str(call.args[0]) == expected_call


@mock.patch('builtins.open', create=True)
@mock.patch('PlantStation.configurer.Configure.prompt', return_value=input_config02)
def test_env_config_with_working_hours(mock_input, mock_write):
    cwd = os.getcwd()
    expected_config_file = [cwd + '/test02.cfg', '[GLOBAL]\n',
                            'env_name = test02\n', 'workingHours = True\n', 'ActiveLimit = 2\n',
                            'workingHoursBegin = 10:22\n', 'workingHoursEnd = 15:33\n', '\n', '[Grubson]\n',
                            'plantName = Grubson\n', 'wateringDuration = 15\n', 'wateringInterval =  03:00:21\n',
                            'lastTimeWatered = \n', 'gpioPinNumber = GPIO27\n', 'isActive = True\n', '\n']
    EnvironmentCreator(mock=True, dry_run=True)
    for call, expected_call in zip(mock_write.mock_calls, expected_config_file):
        assert str(call.args[0]) == expected_call

#
# @mock.patch('builtins.open', create=True)
# @mock.patch('PlantStation.configurer.Configure.prompt', side_effect=[input_config03, input_config03a, input_config03b])
# def test_env_config_with_two_plants(mock_input, mock_write):
#     cwd = os.getcwd()
#     expected_config_file = [cwd + '/test03.cfg', '[GLOBAL]\n',
#                             'env_name = test03\n', 'workingHours = True\n', 'ActiveLimit = 2\n',
#                             'workingHoursBegin = 08:00\n', 'workingHoursEnd = 16:45\n', '\n', '[plantA]\n',
#                             'plantName = plantA\n', 'wateringDuration = 2\n', 'wateringInterval =  5D 03:00:21\n',
#                             'lastTimeWatered = \n', 'gpioPinNumber = GPIO27\n', 'isActive = True\n', '\n',
#                             'plantName = plantB\n', 'wateringDuration = 1.5\n', 'wateringInterval =  3D 03:03:03\n',
#                             'lastTimeWatered = \n', 'gpioPinNumber = GPIO28\n', 'isActive = True\n', '\n'
#                             ]
#     EnvironmentCreator(mock=True, dry_run=True)
#     for call, expected_call in zip(mock_write.mock_calls, expected_config_file):
#         assert str(call.args[0]) == expected_call
