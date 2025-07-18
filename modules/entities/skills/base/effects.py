from abc import ABC, abstractmethod
from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.entity.robot.robot import Robot
    from modules.entity.prop.prop import Prop

class SkillEffect(ABC):
    """技能效果基类"""
    @abstractmethod
    def apply(self, robot: 'Robot', **kwargs) -> Dict[str, Any]:
        """应用效果并返回效果结果"""
        pass

class BatteryConsumptionEffect(SkillEffect):
    """电池消耗效果"""
    def __init__(self, rate: float = 0.02):
        self.consumption_rate = rate  # 每米消耗率

    def apply(self, robot: 'Robot', **kwargs) -> Dict[str, Any]:
        distance = kwargs.get('distance', 0)
        consumption = distance * self.consumption_rate
        current_battery = robot.get_state('battery', 0)
        new_battery = max(0, current_battery - consumption)
        robot.set_state('battery', new_battery)
        return {
            'battery_consumed': consumption,
            'new_battery_level': new_battery
        }

class PositionChangeEffect(SkillEffect):
    """位置变更效果"""
    def apply(self, robot: 'Robot', **kwargs) -> Dict[str, Any]:
        target_position = kwargs.get('target_position')
        if not target_position:
            return {'error': '缺少目标位置'}

        old_position = robot.get_state('position', {})
        robot.set_state('position', target_position)
        return {
            'old_position': old_position,
            'new_position': target_position
        }

class ObjectPickupEffect(SkillEffect):
    """物体拾取效果"""
    def apply(self, robot: 'Robot', **kwargs) -> Dict[str, Any]:
        target_object = kwargs.get('target_object')
        if not isinstance(target_object, 'Prop'):
            return {'error': '目标不是有效道具'}

        # 检查负载能力
        max_payload = robot.get_state('max_payload_kg', 0)
        object_weight = target_object.get_state('weight_kg', 0)

        if object_weight > max_payload:
            return {'error': '物体超重'}

        # 更新物体状态
        target_object.set_state('is_held', True)
        target_object.set_state('holder_id', robot.id)

        # 更新机器人状态
        robot.set_state('carrying_object', True)
        robot.set_state('carrying_object_id', target_object.id)

        return {'success': True, 'carried_object_id': target_object.id}

class ObjectUnloadEffect(SkillEffect):
    """物体卸载效果"""
    def apply(self, robot: 'Robot', **kwargs) -> Dict[str, Any]:
        target_object = kwargs.get('target_object')
        if not isinstance(target_object, 'Prop'):
            return {'error': '目标不是有效道具'}

        # 更新物体状态
        target_object.set_state('is_held', False)
        target_object.set_state('holder_id', None)
        target_object.set_state('position', robot.get_state('position'))

        # 更新机器人状态
        robot.set_state('carrying_object', False)
        robot.set_state('carrying_object_id', None)

        return {'success': True, 'unloaded_object_id': target_object.id}

class StatusChangeEffect(SkillEffect):
    """状态变更效果"""
    def __init__(self, new_status: str):
        self.new_status = new_status

    def apply(self, robot: 'Robot', **kwargs) -> Dict[str, Any]:
        old_status = robot.get_state('status', 'unknown')
        robot.set_state('status', self.new_status)
        return {
            'old_status': old_status,
            'new_status': self.new_status
        }

class AltitudeChangeEffect(SkillEffect):
    """高度变更效果（无人机专用）"""
    def apply(self, robot: 'Robot', **kwargs) -> Dict[str, Any]:
        altitude = kwargs.get('altitude', 50)
        old_altitude = robot.get_state('altitude', 0)
        robot.set_state('altitude', altitude)
        return {
            'old_altitude': old_altitude,
            'new_altitude': altitude
        }

class CompositeEffect(SkillEffect):
    """组合效果管理器"""
    def __init__(self, effects: List[SkillEffect]):
        self.effects = effects

    def apply(self, robot: 'Robot', **kwargs) -> Dict[str, Any]:
        results = {}
        for effect in self.effects:
            results[effect.__class__.__name__] = effect.apply(robot, **kwargs)
        return results