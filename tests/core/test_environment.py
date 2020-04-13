import pytest
from PlantStation.core import Environment

from .context import create_env, complete_env_config, simple_env_config, add_plants_to_config


def test_read_config(create_env: Environment):
    env = create_env
    print(len(env.plants))


def test_schedule_monitoring():
    pass


def test_start():
    pass


def test_stop():
    pass
