from enum import Enum, auto


class SchedPriorityTable(Enum):
    """Priority table for tasks in scheduler"""
    water = auto()
    should_water = auto()
    SCHED_STOP = auto()

