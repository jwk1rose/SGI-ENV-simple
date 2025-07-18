"""
Robot Configuration Module

Defines global configurations and factory methods based on existing 
concrete robot types (Drone, GroundVehicle).
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from ..base.enums import RobotStatus, RobotName, SkillName


@dataclass
class RobotAttribute:
    """Robot attribute definition
    
    Attributes:
        name: Attribute name
        attribute_type: Attribute type ("str", "int", "float", "bool", "dict", "list")
        default_value: Default value
        description: Attribute description
        is_required: Whether the attribute is required
        validation_rules: Validation rules
    """
    name: str                       # Attribute name
    attribute_type: str             # Attribute type ("str", "int", "float", "bool", "dict", "list")
    default_value: Any = None       # Default value
    description: str = ""           # Attribute description
    is_required: bool = False       # Whether required
    validation_rules: Dict[str, Any] = field(default_factory=dict)  # Validation rules


@dataclass
class RobotDefinition:
    """Robot definition
    
    Attributes:
        robot_name: Robot name
        display_name: Display name
        description: Description
        class_name: Corresponding class name
        default_skills: Default skills possessed
        attributes: Attribute list
        default_values: Default values
        capabilities: Robot capabilities
        limitations: Robot limitations
    """
    robot_name: RobotName           # Robot name
    display_name: str               # Display name
    description: str                # Description
    class_name: str                 # Corresponding class name
    default_skills: List[SkillName] = field(default_factory=list)  # Default skills possessed
    attributes: List[RobotAttribute] = field(default_factory=list)  # Attribute list
    default_values: Dict[str, Any] = field(default_factory=dict)   # Default values
    capabilities: Dict[str, Any] = field(default_factory=dict)     # Robot capabilities
    limitations: Dict[str, Any] = field(default_factory=dict)      # Robot limitations


class RobotConfigManager:
    """Robot configuration manager
    
    Manages configuration information for all robot types, providing
    configuration query, validation, and creation functionality.
    """
    
    def __init__(self) -> None:
        """Initialize robot configuration manager"""
        self._robot_definitions: Dict[RobotName, RobotDefinition] = {}
        self._initialize_robot_configs()
    
    def _initialize_robot_configs(self) -> None:
        """Initialize robot configurations"""
        
        # Drone configuration
        self._robot_definitions[RobotName.DRONE] = RobotDefinition(
            robot_name=RobotName.DRONE,
            display_name="Drone",
            description="Aerial flying robot with photography and surveillance capabilities",
            class_name="Drone",
            default_skills=[
                SkillName.NAVIGATE,
                SkillName.TAKE_PHOTO,
                SkillName.IDENTIFY_ANOMALY,
                SkillName.TAKE_OFF
            ],
            attributes=[
                RobotAttribute(
                    name="battery_level",
                    attribute_type="float",
                    default_value=100.0,
                    description="Battery level percentage",
                    validation_rules={"min": 0.0, "max": 100.0}
                ),
                RobotAttribute(
                    name="altitude",
                    attribute_type="float",
                    default_value=0.0,
                    description="Current flight altitude in meters",
                    validation_rules={"min": 0.0, "max": 500.0}
                ),
                RobotAttribute(
                    name="camera_resolution",
                    attribute_type="str",
                    default_value="1080p",
                    description="Camera resolution",
                    validation_rules={"allowed_values": ["720p", "1080p", "4K"]}
                )
            ],
            default_values={
                "status": RobotStatus.IDLE,
                "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                "max_speed": 15.0,
                "payload_capacity": 2.0
            },
            capabilities={
                "flight": True,
                "photography": True,
                "surveillance": True,
                "cargo_transport": True
            },
            limitations={
                "weather_dependent": True,
                "flight_time_limited": True,
                "payload_weight_limit": 2.0
            }
        )
        
        # GroundVehicle configuration
        self._robot_definitions[RobotName.GROUND_VEHICLE] = RobotDefinition(
            robot_name=RobotName.GROUND_VEHICLE,
            display_name="Ground Vehicle",
            description="Ground mobile robot with transportation and search capabilities",
            class_name="GroundVehicle",
            default_skills=[
                SkillName.NAVIGATE,
                SkillName.LOAD_OBJECT,
                SkillName.UNLOAD_OBJECT,
                SkillName.SEARCH_FOR_TARGET
            ],
            attributes=[
                RobotAttribute(
                    name="fuel_level",
                    attribute_type="float",
                    default_value=100.0,
                    description="Fuel level percentage",
                    validation_rules={"min": 0.0, "max": 100.0}
                ),
                RobotAttribute(
                    name="cargo_capacity",
                    attribute_type="float",
                    default_value=50.0,
                    description="Cargo carrying capacity in kilograms",
                    validation_rules={"min": 0.0, "max": 100.0}
                ),
                RobotAttribute(
                    name="current_load",
                    attribute_type="float",
                    default_value=0.0,
                    description="Current load weight in kilograms",
                    validation_rules={"min": 0.0}
                )
            ],
            default_values={
                "status": RobotStatus.IDLE,
                "position": {"x": 0.0, "y": 0.0},
                "max_speed": 25.0,
                "loaded_items": []
            },
            capabilities={
                "ground_movement": True,
                "cargo_transport": True,
                "heavy_lifting": True,
                "terrain_navigation": True
            },
            limitations={
                "ground_only": True,
                "terrain_dependent": True,
                "cargo_weight_limit": 50.0
            }
        )
    
    def get_robot_definition(self, robot_name: RobotName) -> Optional[RobotDefinition]:
        """Get robot definition
        
        Args:
            robot_name: Robot name
            
        Returns:
            Robot definition, None if not exists
        """
        return self._robot_definitions.get(robot_name)
    
    def get_all_robot_names(self) -> List[RobotName]:
        """Get all robot names
        
        Returns:
            List of robot names
        """
        return list(self._robot_definitions.keys())
    
    def get_robot_skills(self, robot_name: RobotName) -> List[SkillName]:
        """Get robot's skill list
        
        Args:
            robot_name: Robot name
            
        Returns:
            List of skills
        """
        definition = self._robot_definitions.get(robot_name)
        return definition.default_skills.copy() if definition else []
    
    def create_default_config(self, robot_name: RobotName, **kwargs) -> Dict[str, Any]:
        """Create default robot configuration
        
        Args:
            robot_name: Robot name
            **kwargs: Additional configuration parameters
            
        Returns:
            Configuration dictionary
        """
        definition = self._robot_definitions.get(robot_name)
        if not definition:
            return {}
        
        config = definition.default_values.copy()
        
        # Add attribute default values
        for attr in definition.attributes:
            if attr.default_value is not None:
                config[attr.name] = attr.default_value
        
        # Override with passed parameters
        config.update(kwargs)
        
        return config


# Global robot configuration manager instance
robot_config_manager = RobotConfigManager()
    