"""Skill Configuration Module

Defines skill types, parameters, and execution configurations.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from ..base.enums import RobotName, SkillName


@dataclass
class SkillParameter:
    """Skill parameter definition
    
    Attributes:
        name: Parameter name
        param_type: Parameter type ("str", "int", "float", "bool", "list", "dict")
        required: Whether the parameter is required
        default_value: Default value
        description: Parameter description
        validation_rules: Validation rules
    """
    name: str                       # Parameter name
    param_type: str                 # Parameter type ("str", "int", "float", "bool", "list", "dict")
    required: bool = True           # Whether required
    default_value: Any = None       # Default value
    description: str = ""           # Parameter description
    validation_rules: Dict[str, Any] = field(default_factory=dict)  # Validation rules


@dataclass
class SkillDefinition:
    """Skill definition
    
    Attributes:
        skill_name: Skill name enum
        display_name: Display name
        description: Skill description
        parameters: Skill parameters
        compatible_robots: Compatible robots
        execution_time_estimate: Estimated execution time
        energy_cost: Energy cost
        prerequisites: Prerequisites
        effects: Effects
        success_rate: Success rate
    """
    skill_name: SkillName           # Skill name enum
    display_name: str               # Display name
    description: str                # Skill description
    parameters: List[SkillParameter] = field(default_factory=list)  # Skill parameters
    compatible_robots: List[RobotName] = field(default_factory=list)  # Compatible robots
    execution_time_estimate: float = 1.0  # Estimated execution time (seconds)
    energy_cost: float = 1.0        # Energy cost
    prerequisites: List[str] = field(default_factory=list)  # Prerequisites
    effects: List[str] = field(default_factory=list)   # Effects
    success_rate: float = 0.95      # Success rate


class SkillConfigManager:
    """Skill configuration manager
    
    Manages configuration information for all skills, providing
    skill query, validation, and execution configuration.
    """
    
    def __init__(self) -> None:
        """Initialize skill configuration manager"""
        self._skill_definitions: Dict[SkillName, SkillDefinition] = {}
        self._initialize_skill_configs()
    
    def _initialize_skill_configs(self) -> None:
        """Initialize skill configurations"""
        
        # Navigate skill
        self._skill_definitions[SkillName.NAVIGATE] = SkillDefinition(
            skill_name=SkillName.NAVIGATE,
            display_name="Navigate",
            description="Move to specified position",
            parameters=[
                SkillParameter(
                    name="target_position",
                    param_type="dict",
                    required=True,
                    description="Target position coordinates",
                    validation_rules={"required_keys": ["x", "y"]}
                ),
                SkillParameter(
                    name="speed",
                    param_type="float",
                    required=False,
                    default_value=5.0,
                    description="Movement speed",
                    validation_rules={"min": 0.1, "max": 30.0}
                )
            ],
            compatible_robots=[RobotName.DRONE, RobotName.GROUND_VEHICLE],
            execution_time_estimate=10.0,
            energy_cost=5.0,
            effects=["position_changed"],
            success_rate=0.98
        )
        
        # Take Photo skill
        self._skill_definitions[SkillName.TAKE_PHOTO] = SkillDefinition(
            skill_name=SkillName.TAKE_PHOTO,
            display_name="Take Photo",
            description="Capture photograph",
            parameters=[
                SkillParameter(
                    name="resolution",
                    param_type="str",
                    required=False,
                    default_value="1080p",
                    description="Photo resolution",
                    validation_rules={"allowed_values": ["720p", "1080p", "4K"]}
                ),
                SkillParameter(
                    name="target_object",
                    param_type="str",
                    required=False,
                    description="Target object to photograph"
                )
            ],
            compatible_robots=[RobotName.DRONE],
            execution_time_estimate=2.0,
            energy_cost=1.0,
            effects=["photo_taken"],
            success_rate=0.99
        )
        
        # Identify Anomaly skill
        self._skill_definitions[SkillName.IDENTIFY_ANOMALY] = SkillDefinition(
            skill_name=SkillName.IDENTIFY_ANOMALY,
            display_name="Identify Anomaly",
            description="Detect and identify anomalies in the environment",
            parameters=[
                SkillParameter(
                    name="scan_area",
                    param_type="dict",
                    required=True,
                    description="Area to scan for anomalies",
                    validation_rules={"required_keys": ["x", "y", "radius"]}
                ),
                SkillParameter(
                    name="sensitivity",
                    param_type="str",
                    required=False,
                    default_value="medium",
                    description="Detection sensitivity level",
                    validation_rules={"allowed_values": ["low", "medium", "high"]}
                )
            ],
            compatible_robots=[RobotName.DRONE],
            execution_time_estimate=15.0,
            energy_cost=8.0,
            prerequisites=["camera_available"],
            effects=["anomaly_detected"],
            success_rate=0.92
        )
        
        # Load Object skill
        self._skill_definitions[SkillName.LOAD_OBJECT] = SkillDefinition(
            skill_name=SkillName.LOAD_OBJECT,
            display_name="Load Object",
            description="Load specified object",
            parameters=[
                SkillParameter(
                    name="object_id",
                    param_type="str",
                    required=True,
                    description="ID of object to load"
                ),
                SkillParameter(
                    name="loading_method",
                    param_type="str",
                    required=False,
                    default_value="standard",
                    description="Loading method",
                    validation_rules={"allowed_values": ["standard", "careful", "quick"]}
                )
            ],
            compatible_robots=[RobotName.GROUND_VEHICLE, RobotName.DRONE],
            execution_time_estimate=15.0,
            energy_cost=8.0,
            prerequisites=["object_available", "sufficient_capacity"],
            effects=["object_loaded", "weight_increased"],
            success_rate=0.95
        )
        
        # Unload Object skill
        self._skill_definitions[SkillName.UNLOAD_OBJECT] = SkillDefinition(
            skill_name=SkillName.UNLOAD_OBJECT,
            display_name="Unload Object",
            description="Unload specified object",
            parameters=[
                SkillParameter(
                    name="object_id",
                    param_type="str",
                    required=True,
                    description="ID of object to unload"
                ),
                SkillParameter(
                    name="target_location",
                    param_type="dict",
                    required=False,
                    description="Target location for unloading",
                    validation_rules={"required_keys": ["x", "y"]}
                )
            ],
            compatible_robots=[RobotName.GROUND_VEHICLE, RobotName.DRONE],
            execution_time_estimate=10.0,
            energy_cost=5.0,
            prerequisites=["object_loaded"],
            effects=["object_unloaded", "weight_decreased"],
            success_rate=0.97
        )
        
        # Search for Target skill
        self._skill_definitions[SkillName.SEARCH_FOR_TARGET] = SkillDefinition(
            skill_name=SkillName.SEARCH_FOR_TARGET,
            display_name="Search for Target",
            description="Search for specified target in area",
            parameters=[
                SkillParameter(
                    name="target_description",
                    param_type="str",
                    required=True,
                    description="Description of target to search for"
                ),
                SkillParameter(
                    name="search_area",
                    param_type="dict",
                    required=True,
                    description="Area to search",
                    validation_rules={"required_keys": ["x", "y", "radius"]}
                ),
                SkillParameter(
                    name="search_pattern",
                    param_type="str",
                    required=False,
                    default_value="grid",
                    description="Search pattern to use",
                    validation_rules={"allowed_values": ["grid", "spiral", "random"]}
                )
            ],
            compatible_robots=[RobotName.GROUND_VEHICLE, RobotName.DRONE],
            execution_time_estimate=30.0,
            energy_cost=15.0,
            effects=["target_found", "area_searched"],
            success_rate=0.85
        )
        
        # Take Off skill
        self._skill_definitions[SkillName.TAKE_OFF] = SkillDefinition(
            skill_name=SkillName.TAKE_OFF,
            display_name="Take Off",
            description="Take off and reach specified altitude",
            parameters=[
                SkillParameter(
                    name="target_altitude",
                    param_type="float",
                    required=False,
                    default_value=10.0,
                    description="Target altitude in meters",
                    validation_rules={"min": 1.0, "max": 500.0}
                )
            ],
            compatible_robots=[RobotName.DRONE],
            execution_time_estimate=5.0,
            energy_cost=10.0,
            prerequisites=["sufficient_battery", "clear_airspace"],
            effects=["airborne", "altitude_changed"],
            success_rate=0.98
        )
    
    def get_skill_definition(self, skill_name: SkillName) -> Optional[SkillDefinition]:
        """Get skill definition
        
        Args:
            skill_name: Skill name
            
        Returns:
            Skill definition, None if not exists
        """
        return self._skill_definitions.get(skill_name)
    
    def get_compatible_skills(self, robot_name: RobotName) -> List[SkillName]:
        """Get skills compatible with specified robot
        
        Args:
            robot_name: Robot name
            
        Returns:
            List of compatible skills
        """
        compatible_skills = []
        for skill_name, definition in self._skill_definitions.items():
            if robot_name in definition.compatible_robots:
                compatible_skills.append(skill_name)
        return compatible_skills
    
    def validate_skill_parameters(self, skill_name: SkillName, parameters: Dict[str, Any]) -> bool:
        """Validate skill parameters
        
        Args:
            skill_name: Skill name
            parameters: Parameter dictionary
            
        Returns:
            Whether validation passes
        """
        definition = self._skill_definitions.get(skill_name)
        if not definition:
            return False
        
        # Check required parameters
        for param in definition.parameters:
            if param.required and param.name not in parameters:
                return False
        
        return True
    
    def get_all_skill_names(self) -> List[SkillName]:
        """Get all skill names
        
        Returns:
            List of all skill names
        """
        return list(self._skill_definitions.keys())


# Global skill configuration manager instance
skill_config_manager = SkillConfigManager()
    