from enum import IntEnum, unique

@unique
class HealthState(IntEnum):
    OK       = 0
    DEGRADED = 1
    FAILED   = 2
    UNKNOWN  = 3

@unique
class AdminMode(IntEnum):
    ONLINE      = 0
    OFFLINE     = 1
    MAINTENANCE = 2
    NOTFITTED   = 3
    RESERVED    = 4

@unique
class ControlMode(IntEnum):
    REMOTE = 0
    LOCAL  = 1

