"""Global Enumeration Definitions Module

Defines all enumeration types used in the system to ensure global consistency.
"""
from enum import Enum
from typing import List


class RobotName(Enum):
    """Specific robot name enumeration"""
    DRONE = "drone"
    GROUND_VEHICLE = "ground_vehicle"


class RobotStatus(Enum):
    """Robot status enumeration"""
    IDLE = "idle"                    # Idle state
    MOVING = "moving"                # Moving
    WORKING = "working"              # Working
    CHARGING = "charging"            # Charging
    ERROR = "error"                  # Error state


class ObjectStatus(Enum):
    """Object status enumeration"""
    AVAILABLE = "available"          # Available
    UNAVAILABLE = "unavailable"      # Unavailable
    DISCOVERED = "discovered"        # Discovered
    UNDISCOVERED = "undiscovered"    # Undiscovered
    LOADED = "loaded"                # Loaded
    UNLOADED = "unloaded"            # Unloaded
    IN_USE = "in_use"                # In use


class PropName(Enum):
    """Specific prop name enumeration"""
    CAR = "car"
    CARGO = "cargo"
    SECURITY_BREACH = "security_breach"
    EQUIPMENT_FAILURE = "equipment_failure"


class SkillName(Enum):
    """Skill name enumeration"""
    NAVIGATE = "navigate"            # Navigate
    TAKE_PHOTO = "take_photo"        # Take photo
    IDENTIFY_ANOMALY = "identify_anomaly"  # Identify anomaly
    LOAD_OBJECT = "load_object"      # Load object
    UNLOAD_OBJECT = "unload_object"  # Unload object
    SEARCH_FOR_TARGET = "search_for_target"  # Search for target
    TAKE_OFF = "take_off"            # Take off
