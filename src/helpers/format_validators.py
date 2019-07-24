import re
from datetime import timedelta

gpio_regex = re.compile(r'((BOARD)|(GPIO))\d{1,2}')

datetime_regex = re.compile(r'((?P<days>\d+?)D)?((?P<hours>\d+?):)?((?P<minutes>\d+?):)?(?P<seconds>\d+?)?')


def parse_time(time_str: str):
    parts = datetime_regex.match(time_str)
    if not parts:
        raise ValueError('String does not match proper pattern')
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts:
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)


def is_gpio(gpio_str: str) -> bool:
    parts = gpio_regex.match(gpio_str)
    if not parts:
        raise ValueError('Wrong GPIO pin name.')
    return True
