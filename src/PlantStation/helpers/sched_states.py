from enum import Enum, auto


class SchedPriorityTable(Enum):
    # priority low to high
    waterOn = auto()
    should_water = auto()
    SCHED_STOP = auto()
    waterOff = auto()


class SchedState(Enum):
    RUNNING = ()
    PAUSED = ()
    STOPPED = ()
    UNSET = ()
