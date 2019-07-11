import re
from datetime import timedelta


regex = re.compile(r'((?P<days>\d+?)D)?((?P<hours>\d+?):)?((?P<minutes>\d+?):)?(?P<seconds>\d+?)?')


def parse(time_str: str):
    parts = regex.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for (name, param) in parts.iteritems():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)
