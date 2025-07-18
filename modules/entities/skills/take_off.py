from typing import Dict, Any
from modules.entities.robot.robot import Robot
from modules.entities.robot.drone import Drone
from modules.entities.robot.ground_vehicle import GroundVehicle
from modules.entities.robot.capabilities import Capability
from .skill import Skill
from .preconditions import has_capability, battery_above, robot_status_is
from .effects import StatusChangeEffect, AltitudeChangeEffect

class TakeOffSkill(Skill):
    """无人机起飞技能"""
    
    def _setup(self):
        """设置前置条件和效果"""
        self.preconditions.add(has_capability(Capability.FLY))
        self.preconditions.add(battery_above(20.0))  # 起飞需要更多电量
        self.preconditions.add(robot_status_is('landed'))

        # 添加效果
        self.effects.append(StatusChangeEffect('flying'))
        self.effects.append(AltitudeChangeEffect())

    def _default_execute(self, robot: Robot, **kwargs) -> Dict[str, Any]:
        """默认起飞逻辑（仅无人机可用）"""
        if not isinstance(robot, Drone):
            return {'error': '仅无人机可执行起飞技能'}
        
        self.logger.info(f"无人机 {robot.label} 开始起飞")
        
        return {
            'drone_id': robot.id,
            'takeoff_altitude': kwargs.get('altitude', 50)
        }

    def _drone_execute(self, robot: Drone, **kwargs) -> Dict[str, Any]:
        """无人机专用起飞逻辑"""
        return self._default_execute(robot, **kwargs)

    def _ground_vehicle_execute(self, robot: GroundVehicle, **kwargs) -> Dict[str, Any]:
        """地面车辆无法起飞"""
        return {'error': '地面车辆无法执行起飞技能'}