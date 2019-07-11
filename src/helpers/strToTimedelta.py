import re
from datetime import timedelta


regex = re.compile(r'((?P<days>\d+?)D)?((?P<hours>\d+?):)?((?P<minutes>\d+?):)?(?P<seconds>\d+?)?')


def parse(time_str: str):
    parts = regex.match(time_str)
    if not parts:
        raise ValueError('String does not match proper pattern')
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts:
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)
