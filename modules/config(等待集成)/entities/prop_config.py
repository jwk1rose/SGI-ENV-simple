"""
Prop Configuration Module

Defines global configurations and factory methods based on existing 
concrete prop types (Car, Cargo, SecurityBreach, EquipmentFailure).
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from ..base.enums import PropName, PropStatus

@dataclass
class PropAttribute:
    """Prop attribute definition
    
    Attributes:
        name: Attribute name
        attribute_type: Attribute type ("str", "int", "float", "bool", "dict")
        default_value: Default value
        description: Attribute description
        is_required: Whether the attribute is required
        validation_rules: Validation rules
    """
    name: str                       # Attribute name
    attribute_type: str             # Attribute type ("str", "int", "float", "bool", "dict")
    default_value: Any = None       # Default value
    description: str = ""           # Attribute description
    is_required: bool = False       # Whether required
    validation_rules: Dict[str, Any] = field(default_factory=dict)  # Validation rules


@dataclass
class PropDefinition:
    """Prop definition
    
    Attributes:
        prop_name: Prop name
        display_name: Display name
        description: Description
        class_name: Corresponding class name
        attributes: Attribute list
        default_values: Default values
        validation_rules: Validation rules
        metadata: Metadata
    """
    prop_name: PropName             # Prop name
    display_name: str               # Display name
    description: str                # Description
    class_name: str                 # Corresponding class name
    attributes: List[PropAttribute] = field(default_factory=list)  # Attribute list
    default_values: Dict[str, Any] = field(default_factory=dict)   # Default values
    validation_rules: Dict[str, Any] = field(default_factory=dict) # Validation rules


class PropConfigManager:
    """Prop configuration manager
    
    Manages configuration information for all prop types, providing
    configuration query, validation, and creation functionality.
    """
    
    def __init__(self) -> None:
        """Initialize prop configuration manager"""
        self._prop_definitions: Dict[PropName, PropDefinition] = {}
        self._initialize_prop_configs()
    
    def _initialize_prop_configs(self) -> None:
        """Initialize prop configurations"""
        
        # Car configuration
        self._prop_definitions[PropName.CAR] = PropDefinition(
            prop_name=PropName.CAR,
            display_name="Car",
            description="Physical prop with license plate number",
            class_name="Car",
            attributes=[
                PropAttribute(
                    name="license_plate",
                    attribute_type="str",
                    description="License plate number",
                    is_required=True,
                    validation_rules={"min_length": 1, "max_length": 20}
                )
            ],
            default_values={
                "status":PropStatus.UNDISCOVERED 
            },
            validation_rules={
                "required_fields": ["license_plate"]
            }
        )
        
        # Cargo configuration
        self._prop_definitions[PropName.CARGO] = PropDefinition(
            prop_name=PropName.CARGO,
            display_name="Cargo",
            description="Cargo prop with weight attribute",
            class_name="Cargo",
            attributes=[
                PropAttribute(
                    name="weight_kg",
                    attribute_type="float",
                    description="Cargo weight in kilograms",
                    is_required=True,
                    validation_rules={"min": 0.0, "max": 1000.0}
                ),
            ],
            default_values={
                "is_held": False,
                "location": "warehouse_A"
            },
            validation_rules={
                "required_fields": ["weight_kg"]
            },
        )
        
        # SecurityBreach configuration
        self._prop_definitions[PropName.SECURITY_BREACH] = PropDefinition(
            prop_name=PropName.SECURITY_BREACH,
            display_name="Security Breach",
            description="Security incident that needs to be handled",
            class_name="SecurityBreach",
            attributes=[
                PropAttribute(
                    name="breach_location",
                    attribute_type="dict",
                    description="Location coordinates where the incident occurred",
                    is_required=True,
                    validation_rules={"required_keys": ["x", "y"]}
                )
            ],
            default_values={
                "type": "security_breach",
                "status": "discovered"
            },
            validation_rules={
                "required_fields": ["breach_location"]
            },
            metadata={
                "category": "event",
                "physical": False,
                "resolvable": True
            }
        )
        
        # EquipmentFailure configuration
        self._prop_definitions[PropName.EQUIPMENT_FAILURE] = PropDefinition(
            prop_name=PropName.EQUIPMENT_FAILURE,
            display_name="Equipment Failure",
            description="Equipment failure incident",
            class_name="EquipmentFailure",
            attributes=[
                PropAttribute(
                    name="failed_equipment_id",
                    attribute_type="int",
                    description="ID of the failed equipment",
                    is_required=True,
                    validation_rules={"min": 1}
                ),
                PropAttribute(
                    name="severity",
                    attribute_type="str",
                    default_value="medium",
                    description="Failure severity level",
                    validation_rules={"allowed_values": ["low", "medium", "high", "critical"]}
                )
            ],
            default_values={
                "type": "equipment_failure",
                "is_resolved": False
            },
            validation_rules={
                "required_fields": ["failed_equipment_id"]
            },
        )
    
    def get_prop_definition(self, prop_name: PropName) -> Optional[PropDefinition]:
        """Get prop definition
        
        Args:
            prop_name: Prop name
            
        Returns:
            Prop definition, None if not exists
        """
        return self._prop_definitions.get(prop_name)
    
    def get_all_prop_names(self) -> List[PropName]:
        """Get all prop names
        
        Returns:
            List of prop names
        """
        return list(self._prop_definitions.keys())
    
    def get_prop_attributes(self, prop_name: PropName) -> List[PropAttribute]:
        """Get attributes of specified prop
        
        Args:
            prop_name: Prop name
            
        Returns:
            List of attributes
        """
        definition = self._prop_definitions.get(prop_name)
        return definition.attributes if definition else []
    
    def get_default_values(self, prop_name: PropName) -> Dict[str, Any]:
        """Get default values of prop
        
        Args:
            prop_name: Prop name
            
        Returns:
            Dictionary of default values
        """
        definition = self._prop_definitions.get(prop_name)
        return definition.default_values.copy() if definition else {}
    
    def validate_prop_config(self, prop_name: PropName, config: Dict[str, Any]) -> bool:
        """Validate prop configuration
        
        Args:
            prop_name: Prop name
            config: Configuration dictionary
            
        Returns:
            Whether validation passes
        """
        definition = self._prop_definitions.get(prop_name)
        if not definition:
            return False
        
        # Check required fields
        required_fields = definition.validation_rules.get("required_fields", [])
        for field in required_fields:
            if field not in config:
                return False
        
        # Check attribute validation rules
        for attr in definition.attributes:
            if attr.name in config:
                value = config[attr.name]
                if not self._validate_attribute_value(attr, value):
                    return False
        
        return True
    
    def _validate_attribute_value(self, attr: PropAttribute, value: Any) -> bool:
        """Validate attribute value
        
        Args:
            attr: Attribute definition
            value: Attribute value
            
        Returns:
            Whether validation passes
        """
        rules = attr.validation_rules
        
        # Type checking
        if attr.attribute_type == "str" and not isinstance(value, str):
            return False
        elif attr.attribute_type == "int" and not isinstance(value, int):
            return False
        elif attr.attribute_type == "float" and not isinstance(value, (int, float)):
            return False
        elif attr.attribute_type == "bool" and not isinstance(value, bool):
            return False
        elif attr.attribute_type == "dict" and not isinstance(value, dict):
            return False
        
        # Range checking
        if "min" in rules and value < rules["min"]:
            return False
        if "max" in rules and value > rules["max"]:
            return False
        
        # Length checking
        if "min_length" in rules and len(str(value)) < rules["min_length"]:
            return False
        if "max_length" in rules and len(str(value)) > rules["max_length"]:
            return False
        
        # Allowed values checking
        if "allowed_values" in rules and value not in rules["allowed_values"]:
            return False
        
        # Dictionary required keys checking
        if "required_keys" in rules and isinstance(value, dict):
            for key in rules["required_keys"]:
                if key not in value:
                    return False
        
        return True
    
    def create_default_config(self, prop_name: PropName, **kwargs) -> Dict[str, Any]:
        """Create default configuration
        
        Args:
            prop_name: Prop name
            **kwargs: Additional configuration parameters
            
        Returns:
            Configuration dictionary
        """
        definition = self._prop_definitions.get(prop_name)
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


# Global configuration manager instance
prop_config_manager = PropConfigManager()