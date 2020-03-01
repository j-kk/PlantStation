from enum import Enum, auto


class SchedPriorityTable(Enum):
    """Priority table for tasks in scheduler"""
    waterOn = auto()
    should_water = auto()
    SCHED_STOP = auto()
    waterOff = auto()


class SchedState(Enum):
    """Allowed scheduler states"""
    RUNNING = auto()
    PAUSED = auto()
    STOPPED =auto()
    KILLED = auto()
    UNSET = auto()
