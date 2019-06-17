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

@unique
class ObsMode(IntEnum):
    IDLE             = 0
    IMAGING          = 1
    PULSARSEARCH     = 2
    PULSARTIMING     = 3
    DYNAMICSPECTRUM  = 4
    TRANSIENTSEARCH  = 5
    VLBI             = 6
    CALIBRATION      = 7

@unique
class ObsState(IntEnum):
    IDLE        = 0
    CONFIGURING = 1
    READY       = 2
    SCANNING    = 3
    PAUSED      = 4
    ABORTED     = 5
    FAULT       = 6

