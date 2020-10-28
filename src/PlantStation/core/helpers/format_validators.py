import re
import datetime
from typing import Union

gpio_regex = re.compile(r'((BOARD)|(GPIO))\d{1,2}$')

datetime_regex = re.compile(r'((?P<days>\d{1,2})D) ((?P<hours>\d{2}):)((?P<minutes>\d{2}):)(?P<seconds>\d{2})$')


def parse_time(time_str: str) -> Union[datetime.timedelta, None]:
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
        else:
            raise ValueError('String does not match proper pattern')
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
