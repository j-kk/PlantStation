import uuid

import mock
import pytest
from mock import patch

from core.config import Config


@mock.patch("logging.Logger")
def test_read_files_empty(mock_logger):
    with pytest.raises(FileNotFoundError):
        config = Config(mock_logger, [])
        config.read()


@mock.patch("logging.Logger")
def test_read_files_not_found(mock_logger):
    file = uuid.uuid4().__str__()
    with pytest.raises(FileNotFoundError):
        config = Config(mock_logger, file)
        config.read()


@mock.patch("logging.Logger")
def test_write_all_ok(mock_logger: mock.MagicMock):
    with patch('config.Config._write_to_file') as mock_write:
        expected_res = ['test']
        mock_write.return_value = expected_res
        config = Config(mock_logger, [])
        res = config.write()
        assert res == expected_res


@mock.patch("logging.Logger")
def test__write_to_file_paths_empty(mock_logger: mock.MagicMock):
    with pytest.raises(FileNotFoundError):
        config = Config(mock_logger, [])
        config._write_to_file()


@mock.patch("builtins.open")
@mock.patch("logging.Logger")
def test__write_to_file_paths_empty(mock_logger: mock.MagicMock, mock_open_file):
    mock_open_file.side_effect = FileNotFoundError
    with pytest.raises(FileNotFoundError):
        config = Config(mock_logger, ['test_file_not_found'])
        config._write_to_file()


@mock.patch("builtins.open")
@mock.patch("logging.Logger")
def test__write_to_file_permission_error(mock_logger: mock.MagicMock, mock_open_file):
    mock_open_file.side_effect = PermissionError
    with pytest.raises(PermissionError):
        config = Config(mock_logger, ['test_permission'])
        config._write_to_file()
