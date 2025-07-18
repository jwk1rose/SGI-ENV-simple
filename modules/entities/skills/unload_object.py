from typing import Dict, Any
from modules.entity.robot.robot import Robot
from modules.entity.robot.drone import Drone
from modules.entity.robot.ground_vehicle import GroundVehicle
from modules.entity.robot.capabilities import Capability
from .skill import Skill
from .preconditions import has_capability, battery_above, has_target_object, is_carrying_object
from .effects import ObjectUnloadEffect, StatusChangeEffect

class UnloadObjectSkill(Skill):
    """卸载物体技能"""
    required_capabilities = {Capability.MANIPULATE}

    def _setup(self):
        """设置前置条件和效果"""
        self.preconditions.add(has_capability(Capability.MANIPULATE))
        self.preconditions.add(battery_above(10.0))
        self.preconditions.add(is_carrying_object())
        self.preconditions.add(has_target_object())

        # 添加效果
        self.effects.append(ObjectUnloadEffect())
        self.effects.append(StatusChangeEffect('idle'))

    def _default_execute(self, robot: Robot, **kwargs) -> Dict[str, Any]:
        """默认卸载逻辑"""
        target_object = kwargs['target_object']
        
        # 设置工作状态
        robot.set_state('status', 'working')
        
        self.logger.info(f"机器人 {robot.label} 开始卸载物体 {target_object.label}")
        
        return {
            'robot_id': robot.id,
            'unloaded_object_id': target_object.id,
            'position': robot.get_state('position')
        }

    def _drone_execute(self, robot: Drone, **kwargs) -> Dict[str, Any]:
        """无人机卸载逻辑"""
        result = self._default_execute(robot, **kwargs)
        result['drop_altitude'] = robot.get_state('altitude', 0)
        result['drop_method'] = 'controlled_release'
        return result

    def _ground_vehicle_execute(self, robot: GroundVehicle, **kwargs) -> Dict[str, Any]:
        """地面车辆卸载逻辑"""
        result = self._default_execute(robot, **kwargs)
        result['drop_height'] = kwargs.get('drop_height', 0.5)
        result['drop_method'] = 'mechanical_arm'
        return result