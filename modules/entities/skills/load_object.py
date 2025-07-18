from typing import Dict, Any
from modules.entity.robot.robot import Robot
from modules.entity.robot.drone import Drone
from modules.entity.robot.ground_vehicle import GroundVehicle
from modules.entity.robot.capabilities import Capability
from .skill import Skill
from .preconditions import has_capability, battery_above, has_target_object, is_not_carrying_object, object_within_range
from .effects import ObjectPickupEffect, StatusChangeEffect

class LoadObjectSkill(Skill):
    """物体装载技能"""
    required_capabilities = {Capability.MANIPULATE}

    def _setup(self):
        """设置前置条件和效果"""
        self.preconditions.add(has_capability(Capability.MANIPULATE))
        self.preconditions.add(battery_above(15.0))
        self.preconditions.add(is_not_carrying_object())
        self.preconditions.add(has_target_object())
        self.preconditions.add(object_within_range(2.0))

        # 添加效果
        self.effects.append(ObjectPickupEffect())
        self.effects.append(StatusChangeEffect('idle'))

    def _default_execute(self, robot: Robot, **kwargs) -> Dict[str, Any]:
        """默认装载逻辑"""
        target_object = kwargs['target_object']
        
        # 设置工作状态
        robot.set_state('status', 'working')
        
        self.logger.info(f"机器人 {robot.label} 开始装载物体 {target_object.label}")
        
        return {
            'robot_id': robot.id,
            'loaded_object_id': target_object.id,
            'object_weight': target_object.get_state('weight_kg', 0)
        }

    def _drone_execute(self, robot: Drone, **kwargs) -> Dict[str, Any]:
        """无人机装载逻辑"""
        result = self._default_execute(robot, **kwargs)
        result['pickup_method'] = 'magnetic_gripper'
        result['hover_altitude'] = robot.get_state('altitude', 0)
        return result

    def _ground_vehicle_execute(self, robot: GroundVehicle, **kwargs) -> Dict[str, Any]:
        """地面车辆装载逻辑"""
        result = self._default_execute(robot, **kwargs)
        result['pickup_method'] = 'mechanical_arm'
        result['ground_clearance'] = kwargs.get('ground_clearance', 0.5)
        return result