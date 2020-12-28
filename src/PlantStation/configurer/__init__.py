from .Configure import Configurer

def run():
    try:
        Configurer()
    except InterruptedError or KeyboardInterrupt:
        pass