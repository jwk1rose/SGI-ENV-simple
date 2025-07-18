"""
Robot Skill Library Descriptions

Structured skill descriptions for all available robot skills based on the definitive skill library.
"""

from modules.entities.skills.base.descriptions import (
    SkillDescription, SkillCategory, SkillRequirement, 
    SkillPrecondition, SkillOutput, SkillDescriptionRegistry
)
from typing import Dict, List


def register_drone_skill_descriptions() -> None:
    """
    Register all drone skill descriptions in the skill description registry.
    
    This function creates and registers structured descriptions for all drone skills
    as defined in the Robot Skill Library documentation.
    """
    
    # Takeoff Skill
    takeoff_description = SkillDescription(
        name="takeoff",
        display_name="Takeoff",
        category=SkillCategory.MOVEMENT,
        description="Ascending vertically from the ground to a safe, standard operational altitude.",
        capabilities=["FLY", "ALTITUDE_CONTROL", "STABILIZATION"],
        requirements=[
            SkillRequirement(
                capability="FLY",
                min_battery=15.0,
                description="Drone must have flight capability and sufficient power for takeoff"
            )
        ],
        preconditions=[
            SkillPrecondition(
                condition="Drone is on a stable, flat surface",
                check_type="position",
                description="Landing surface must be stable and level"
            ),
            SkillPrecondition(
                condition="Clear vertical space above drone",
                check_type="environment",
                description="No obstacles in takeoff path"
            ),
            SkillPrecondition(
                condition="System status is nominal",
                check_type="status",
                description="All drone systems functioning properly"
            )
        ],
        input_params={},
        outputs=[
            SkillOutput(
                output_type="status",
                description="Drone is airborne and hovering, ready for commands",
                data_format="{'status': 'HOVERING', 'altitude': float, 'position': [x, y, z]}"
            )
        ],
        execution_time="5-10 seconds",
        examples=[
            "takeoff() - Drone ascends to operational altitude"
        ],
        notes=[
            "Consumes significant battery during ascent",
            "Requires clear airspace above",
            "Automatically stabilizes at safe altitude"
        ]
    )
    
    # Land Skill
    land_description = SkillDescription(
        name="land",
        display_name="Land",
        category=SkillCategory.MOVEMENT,
        description="Descends vertically from current altitude to land on a designated ground surface or rooftop platform.",
        capabilities=["FLY", "ALTITUDE_CONTROL", "PRECISION_LANDING"],
        requirements=[
            SkillRequirement(
                capability="FLY",
                min_battery=5.0,
                description="Sufficient power for controlled descent"
            )
        ],
        preconditions=[
            SkillPrecondition(
                condition="Drone is in stable hover state",
                check_type="status",
                description="Drone must be airborne and stable"
            ),
            SkillPrecondition(
                condition="Designated landing zone is flat",
                check_type="environment",
                description="Landing area must be suitable for safe landing"
            )
        ],
        input_params={
            "landing_position": "Target landing coordinates [x, y] (optional, uses current position if not specified)"
        },
        outputs=[
            SkillOutput(
                output_type="status",
                description="Drone safely landed and in standby mode",
                data_format="{'status': 'LANDED', 'position': [x, y, 0]}"
            )
        ],
        execution_time="5-15 seconds",
        examples=[
            "land() - Land at current position",
            "land(landing_position=[10, 20]) - Land at specified coordinates"
        ],
        notes=[
            "Automatically enters standby mode after landing",
            "Requires flat, stable landing surface",
            "Precision landing capability for rooftops"
        ]
    )
    
    # Navigate To Skill (Drone)
    drone_navigate_description = SkillDescription(
        name="navigate_to",
        display_name="Navigate To (Drone)",
        category=SkillCategory.MOVEMENT,
        description="Flies from the current position to a specific 3D coordinate.",
        capabilities=["FLY", "NAVIGATE", "PATH_PLANNING"],
        requirements=[
            SkillRequirement(
                capability="NAVIGATE",
                min_battery=10.0,
                description="Navigation system and sufficient flight power"
            )
        ],
        preconditions=[
            SkillPrecondition(
                condition="Reasonably clear flight path exists",
                check_type="environment",
                description="Path to destination must be navigable"
            ),
            SkillPrecondition(
                condition="Valid target location provided",
                check_type="parameter",
                description="Destination coordinates must be valid"
            )
        ],
        input_params={
            "location": "Target 3D coordinates [x, y, z] or named location"
        },
        outputs=[
            SkillOutput(
                output_type="position",
                description="Drone position updated to specified location",
                data_format="{'position': [x, y, z], 'status': 'ARRIVED'}"
            )
        ],
        execution_time="Variable based on distance (1-60 seconds)",
        examples=[
            "navigate_to(location=[50, 100, 30]) - Fly to coordinates",
            "navigate_to(location='hospital') - Fly to named location"
        ],
        notes=[
            "Supports 3D navigation with altitude control",
            "Automatic obstacle avoidance",
            "Battery consumption proportional to distance"
        ]
    )
    
    # Take Photo Skill (Drone)
    drone_photo_description = SkillDescription(
        name="take_photo_area",
        display_name="Take Photo (Area)",
        category=SkillCategory.SENSING,
        description="Captures a wide-angle aerial image of a specified area to provide general overview and situational awareness.",
        capabilities=["TAKE_PHOTO", "CAMERA", "GPS"],
        requirements=[
            SkillRequirement(
                capability="TAKE_PHOTO",
                min_battery=5.0,
                description="Camera system and basic power"
            )
        ],
        preconditions=[
            SkillPrecondition(
                condition="Drone at safe operational altitude",
                check_type="position",
                description="Must be at appropriate height for area photography"
            ),
            SkillPrecondition(
                condition="Camera is functional",
                check_type="capability",
                description="Camera system must be operational"
            )
        ],
        input_params={
            "area": "Target area to photograph (polygon or bounding box)"
        },
        outputs=[
            SkillOutput(
                output_type="data",
                description="High-altitude, wide-field-of-view digital image with metadata",
                data_format="{'image_file': str, 'metadata': {'gps': [lat, lon], 'altitude': float, 'timestamp': str}}"
            )
        ],
        execution_time="2-5 seconds",
        examples=[
            "take_photo(area='park') - Photograph park area",
            "take_photo(area=[[0,0], [100,0], [100,100], [0,100]]) - Photo of defined area"
        ],
        notes=[
            "Ideal for mapping and large zone assessment",
            "Images tagged with GPS coordinates",
            "Wide-angle lens for maximum coverage"
        ]
    )
    
    # Load Object Skill (Drone)
    drone_load_description = SkillDescription(
        name="load_object",
        display_name="Load Object (Drone)",
        category=SkillCategory.MANIPULATION,
        description="Uses an onboard gripper or winch to pick up and secure a specified object.",
        capabilities=["MANIPULATE", "GRIPPER", "PRECISION_HOVER"],
        requirements=[
            SkillRequirement(
                capability="MANIPULATE",
                min_battery=10.0,
                max_payload=3.0,
                description="Gripper system and sufficient lift capacity"
            )
        ],
        preconditions=[
            SkillPrecondition(
                condition="Drone hovering accurately above object",
                check_type="position",
                description="Precise positioning required for pickup"
            ),
            SkillPrecondition(
                condition="Object weight within 3kg limit",
                check_type="object",
                description="Payload must not exceed drone capacity"
            ),
            SkillPrecondition(
                condition="Object size compatible with gripper",
                check_type="object",
                description="Object must fit gripper mechanism"
            )
        ],
        input_params={
            "object": "Target object ID to pick up"
        },
        outputs=[
            SkillOutput(
                output_type="object",
                description="Object securely attached to drone",
                data_format="{'carrying_object': str, 'attachment_status': 'SECURED'}"
            )
        ],
        execution_time="10-20 seconds",
        examples=[
            "load(object='cargo_01') - Pick up specified cargo"
        ],
        notes=[
            "Maximum payload: 3kg",
            "Requires precise hovering capability",
            "Magnetic or mechanical gripper system"
        ]
    )
    
    # Unload Object Skill (Drone)
    drone_unload_description = SkillDescription(
        name="unload_object",
        display_name="Unload Object (Drone)",
        category=SkillCategory.MANIPULATION,
        description="Releases a currently attached object at the drone's current position.",
        capabilities=["MANIPULATE", "GRIPPER", "PRECISION_HOVER"],
        requirements=[
            SkillRequirement(
                capability="MANIPULATE",
                min_battery=5.0,
                description="Gripper release mechanism"
            )
        ],
        preconditions=[
            SkillPrecondition(
                condition="Drone currently carrying an object",
                check_type="object",
                description="Must have object attached to release"
            ),
            SkillPrecondition(
                condition="Positioned over safe drop-off zone",
                check_type="environment",
                description="Safe area for object release"
            )
        ],
        input_params={
            "object": "Object ID to release"
        },
        outputs=[
            SkillOutput(
                output_type="status",
                description="Object released, gripper mechanism free",
                data_format="{'carrying_object': null, 'gripper_status': 'FREE'}"
            )
        ],
        execution_time="5-10 seconds",
        examples=[
            "unload(object='cargo_01') - Release carried object"
        ],
        notes=[
            "Requires safe drop zone",
            "Frees up payload capacity",
            "Controlled release mechanism"
        ]
    )
    
    # Register all drone skills
    SkillDescriptionRegistry.register("takeoff", takeoff_description)
    SkillDescriptionRegistry.register("land", land_description)
    SkillDescriptionRegistry.register("navigate_to_drone", drone_navigate_description)
    SkillDescriptionRegistry.register("take_photo_area", drone_photo_description)
    SkillDescriptionRegistry.register("load_object_drone", drone_load_description)
    SkillDescriptionRegistry.register("unload_object_drone", drone_unload_description)


def register_ground_vehicle_skill_descriptions() -> None:
    """
    Register all ground vehicle skill descriptions in the skill description registry.
    
    This function creates and registers structured descriptions for all ground vehicle skills
    as defined in the Robot Skill Library documentation.
    """
    
    # Move To Skill (Ground Vehicle)
    vehicle_move_description = SkillDescription(
        name="move_to",
        display_name="Move To (Ground Vehicle)",
        category=SkillCategory.MOVEMENT,
        description="Drives autonomously along Cybertown's road network to a specified ground-level location.",
        capabilities=["DRIVE", "NAVIGATE", "ROAD_FOLLOWING"],
        requirements=[
            SkillRequirement(
                capability="NAVIGATE",
                min_battery=10.0,
                description="Navigation system and driving capability"
            )
        ],
        preconditions=[
            SkillPrecondition(
                condition="Navigable ground path exists",
                check_type="environment",
                description="Road network connection to destination"
            ),
            SkillPrecondition(
                condition="Valid target location provided",
                check_type="parameter",
                description="Destination must be accessible by road"
            )
        ],
        input_params={
            "location": "Target ground-level coordinates [x, y] or named location"
        },
        outputs=[
            SkillOutput(
                output_type="position",
                description="Vehicle position updated to target location",
                data_format="{'position': [x, y, 0], 'status': 'ARRIVED'}"
            )
        ],
        execution_time="Variable based on distance and traffic (30-300 seconds)",
        examples=[
            "move_to(location=[100, 200]) - Drive to coordinates",
            "move_to(location='hospital') - Drive to named location"
        ],
        notes=[
            "Follows road network constraints",
            "Automatic traffic and obstacle avoidance",
            "Ground-level navigation only"
        ]
    )
    
    # Take Photo Skill (Ground Vehicle)
    vehicle_photo_description = SkillDescription(
        name="take_photo_target",
        display_name="Take Photo (Target)",
        category=SkillCategory.SENSING,
        description="Captures a high-resolution, ground-level image of a specific target for close-range inspection.",
        capabilities=["TAKE_PHOTO", "CAMERA", "ZOOM"],
        requirements=[
            SkillRequirement(
                capability="TAKE_PHOTO",
                min_battery=3.0,
                description="Camera system and basic power"
            )
        ],
        preconditions=[
            SkillPrecondition(
                condition="Unobstructed line-of-sight to target",
                check_type="environment",
                description="Clear view of target object"
            ),
            SkillPrecondition(
                condition="Target within camera range",
                check_type="position",
                description="Target must be within effective camera distance"
            ),
            SkillPrecondition(
                condition="Vehicle is stationary",
                check_type="status",
                description="Must be stopped for image clarity"
            )
        ],
        input_params={
            "target": "Specific target object ID to photograph"
        },
        outputs=[
            SkillOutput(
                output_type="data",
                description="High-resolution, detailed digital image file",
                data_format="{'image_file': str, 'target_id': str, 'metadata': {'timestamp': str, 'camera_settings': dict}}"
            )
        ],
        execution_time="3-8 seconds",
        examples=[
            "take_photo(target='building_01') - Photograph specific building",
            "take_photo(target='vehicle_car_0001') - Photo of target vehicle"
        ],
        notes=[
            "High-resolution for detailed analysis",
            "Requires stationary position",
            "Optimal for close-range inspection"
        ]
    )
    
    # Load Object Skill (Ground Vehicle)
    vehicle_load_description = SkillDescription(
        name="load_object_vehicle",
        display_name="Load Object (Ground Vehicle)",
        category=SkillCategory.MANIPULATION,
        description="Uses a robotic arm or conveyor system to move an object into the vehicle's cargo bay.",
        capabilities=["MANIPULATE", "ROBOTIC_ARM", "CARGO_BAY"],
        requirements=[
            SkillRequirement(
                capability="MANIPULATE",
                min_battery=8.0,
                max_payload=150.0,
                description="Robotic arm system and cargo capacity"
            )
        ],
        preconditions=[
            SkillPrecondition(
                condition="Vehicle positioned adjacent to object",
                check_type="position",
                description="Must be within arm reach of object"
            ),
            SkillPrecondition(
                condition="Object weight within 150kg limit",
                check_type="object",
                description="Payload must not exceed vehicle capacity"
            ),
            SkillPrecondition(
                condition="Cargo bay has sufficient space",
                check_type="capacity",
                description="Available space for object storage"
            )
        ],
        input_params={
            "object": "Target object ID to load into cargo bay"
        },
        outputs=[
            SkillOutput(
                output_type="object",
                description="Object securely stored in vehicle cargo bay",
                data_format="{'cargo_bay': [object_ids], 'load_status': 'SECURED'}"
            )
        ],
        execution_time="15-30 seconds",
        examples=[
            "load(object='cargo_box_01') - Load object into cargo bay"
        ],
        notes=[
            "Maximum payload: 150kg",
            "Robotic arm with precision control",
            "Automatic cargo bay management"
        ]
    )
    
    # Unload Object Skill (Ground Vehicle)
    vehicle_unload_description = SkillDescription(
        name="unload_object_vehicle",
        display_name="Unload Object (Ground Vehicle)",
        category=SkillCategory.MANIPULATION,
        description="Removes a specified object from cargo bay and places it on the ground adjacent to the vehicle.",
        capabilities=["MANIPULATE", "ROBOTIC_ARM", "CARGO_BAY"],
        requirements=[
            SkillRequirement(
                capability="MANIPULATE",
                min_battery=8.0,
                description="Robotic arm operation"
            )
        ],
        preconditions=[
            SkillPrecondition(
                condition="Vehicle carrying specified object",
                check_type="object",
                description="Object must be in cargo bay"
            ),
            SkillPrecondition(
                condition="Clear, stable surface for unloading",
                check_type="environment",
                description="Safe area adjacent to vehicle"
            )
        ],
        input_params={
            "object": "Object ID to remove from cargo bay"
        },
        outputs=[
            SkillOutput(
                output_type="status",
                description="Object placed on ground, cargo space freed",
                data_format="{'cargo_bay': [remaining_objects], 'unload_status': 'COMPLETED'}"
            )
        ],
        execution_time="15-25 seconds",
        examples=[
            "unload(object='cargo_box_01') - Unload object from cargo bay"
        ],
        notes=[
            "Requires stable unloading surface",
            "Frees cargo bay space",
            "Precise placement control"
        ]
    )
    
    # Register all ground vehicle skills
    SkillDescriptionRegistry.register("move_to", vehicle_move_description)
    SkillDescriptionRegistry.register("take_photo_target", vehicle_photo_description)
    SkillDescriptionRegistry.register("load_object_vehicle", vehicle_load_description)
    SkillDescriptionRegistry.register("unload_object_vehicle", vehicle_unload_description)


def register_all_skill_descriptions() -> None:
    """
    Register all skill descriptions from the Robot Skill Library.
    
    This function registers both drone and ground vehicle skill descriptions
    in the global skill description registry.
    """
    register_drone_skill_descriptions()
    register_ground_vehicle_skill_descriptions()
    
    print(f"Registered {len(SkillDescriptionRegistry.get_all())} skill descriptions")


def get_skill_library_summary() -> Dict[str, List[str]]:
    """
    Get a summary of all registered skills organized by robot type.
    
    Returns:
        Dict containing skill names organized by robot type (drone/ground_vehicle)
    """
    all_descriptions = SkillDescriptionRegistry.get_all()
    
    drone_skills = []
    vehicle_skills = []
    
    for name, desc in all_descriptions.items():
        if 'drone' in name or name in ['takeoff', 'land', 'take_photo_area']:
            drone_skills.append(desc.display_name)
        else:
            vehicle_skills.append(desc.display_name)
    
    return {
        'drone_skills': drone_skills,
        'ground_vehicle_skills': vehicle_skills
    }


if __name__ == "__main__":
    # Register all skill descriptions
    register_all_skill_descriptions()
    
    # Print summary
    summary = get_skill_library_summary()
    print("\n=== Robot Skill Library Summary ===")
    print(f"Drone Skills: {summary['drone_skills']}")
    print(f"Ground Vehicle Skills: {summary['ground_vehicle_skills']}")
    
    # Example: Get specific skill description
    takeoff_desc = SkillDescriptionRegistry.get("takeoff")
    if takeoff_desc:
        print(f"\n=== Takeoff Skill Description ===")
        print(f"Summary: {takeoff_desc.get_summary()}")
        print(f"Requirements: {takeoff_desc.get_requirements_text()}")
        print(f"Preconditions: {takeoff_desc.get_preconditions_text()}")