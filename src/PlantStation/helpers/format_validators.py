import re
import datetime

gpio_regex = re.compile(r'((BOARD)|(GPIO))\d{1,2}')

datetime_regex = re.compile(r'((?P<days>\d+?)D)?((?P<hours>\d+?):)?((?P<minutes>\d+?):)?(?P<seconds>\d+?)?')


def parse_time(time_str: str) -> datetime.timedelta:
    """Parses time to project's time format

    Args:
        time_str (str): Datetime in string format: DD HH:MM:SS

    Returns:
        datetime.timedelta: converted result
    """
    parts = datetime_regex.match(time_str)
    if not parts:
        raise ValueError('String does not match proper pattern')
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts.items():
        if param:
            time_params[name] = int(param)
    return datetime.timedelta(**time_params)


def is_gpio(gpio_str: str) -> bool:
    """Checks if gpio_str correctly describes GPIO pin

    Args:
        gpio_str (str): GPIO pin coded in string
    """
    parts = gpio_regex.match(gpio_str)
    if not parts:
        raise ValueError('Wrong GPIO pin name.')
    return True
