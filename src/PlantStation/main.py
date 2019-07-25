from PlantStation.Environment import Environment

mainEnvironment: Environment


def setup_env():
    global mainEnvironment
    mainEnvironment = Environment()
    mainEnvironment.read_config()
    mainEnvironment.schedule_monitoring()


def run_env():
    global mainEnvironment
    mainEnvironment.start()


def stop_env():
    global mainEnvironment
    mainEnvironment.stop()
