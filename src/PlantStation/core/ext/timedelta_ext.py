import datetime


class Interval(datetime.timedelta):

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __str__(self):
        mm, ss = divmod(self.seconds, 60)
        hh, mm = divmod(mm, 60)
        dd = self.days if self.days else 0
        s = "%dD %02d:%02d:%02d" % (dd, hh, mm, ss)
        return s

    @classmethod
    def convert_to_interval(cls, obj):
        args = list(filter(lambda x: not x.startswith('_'), dir(obj)))
        kwargs = {}
        for arg in args:
            if arg not in ['max', 'min', 'resolution', 'total_seconds']:
                kwargs[arg] = getattr(obj, arg)
        return cls(**kwargs)


class Duration(datetime.timedelta):

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, *args, **kwargs)

    def __str__(self):
        return str(int(self.total_seconds()))

    @classmethod
    def convert_to_duration(cls, obj):
        args = list(filter(lambda x: not x.startswith('_'), dir(obj)))
        kwargs = {}
        for arg in args:
            if arg not in ['max', 'min', 'resolution', 'total_seconds']:
                kwargs[arg] = getattr(obj, arg)
        return cls(**kwargs)
