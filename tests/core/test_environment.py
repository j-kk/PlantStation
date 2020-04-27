import datetime
import threading
import time

from PlantStation.core import Environment

# noinspection PyUnresolvedReferences
from .context import create_env, complete_env_config, simple_env_config, add_plants_to_config, silent_hour_now

def test_env(create_env: Environment):
    env = create_env
    for plant in env.plants:
        assert plant.should_water()


def test_water(create_env: Environment):
    env = create_env
    if len(env.plants) > 3:
        return  # TODO skip big tests
    threads = []
    for plant in env.plants:
        thread = threading.Thread(target=plant.water)
        threads.append(thread)

    assert env.config.pin_manager.working_pumps == 0
    for thread in threads:
        thread.start()
    time.sleep(0.5)
    if len(threads) > 0:
        assert env.config.pin_manager.working_pumps == 1
    else:
        assert env.config.pin_manager.working_pumps == 0

    for thread in threads:
        thread.join()
    assert env.config.pin_manager.working_pumps == 0

    for plant in env.plants:
        assert not plant.should_water()


def test_start(create_env: Environment, silent_hour_now):
    env = create_env

    print(datetime.datetime.now())


def test_stop():
    pass
