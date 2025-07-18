import time
from typing import Dict, Any, Optional, TYPE_CHECKING
from modules.entity.robot.robot import Robot
from modules.entity.robot.drone import Drone
from modules.entity.robot.ground_vehicle import GroundVehicle
from modules.entity.robot.capabilities import Capability

if TYPE_CHECKING:
    from modules.map.scene_graph import SceneGraph

from .skill import Skill
from .preconditions import has_capability, battery_above, has_target_type
from .effects import SkillEffect, StatusChangeEffect

class TargetFoundEffect(SkillEffect):
    """目标搜索效果：记录搜索结果"""
    def apply(self, robot: Robot, **kwargs) -> Dict[str, Any]:
        target_found = kwargs.get('target_found', False)
        target_position = kwargs.get('target_position', None)

        # 记录搜索结果到机器人状态
        robot.set_state('last_search_result', {
            'found': target_found,
            'position': target_position,
            'timestamp': kwargs.get('timestamp', time.time())
        })

        return {
            'target_found': target_found,
            'target_position': target_position
        }

class SearchForTargetSkill(Skill):
    """目标搜索技能"""
    required_capabilities = {Capability.SENSOR}

    def _setup(self):
        """设置前置条件和效果"""
        self.preconditions.add(has_capability(Capability.SENSOR))
        self.preconditions.add(battery_above(10.0))
        self.preconditions.add(has_target_type())

        self.effects.append(TargetFoundEffect())
        self.effects.append(StatusChangeEffect('idle'))

    def _default_execute(self, robot: Robot, **kwargs) -> Dict[str, Any]:
        """默认搜索逻辑：使用场景图查找目标"""
        target_type = kwargs['target_type']
        search_radius = kwargs.get('radius', 100)  # 搜索半径，默认100米
        current_pos = robot.get_state('position', {'x': 0, 'y': 0})

        # 设置搜索状态
        robot.set_state('status', 'working')

        # 延迟导入避免循环依赖
        try:
            from modules.map.scene_graph import SceneGraph
            scene_graph = kwargs.get('scene_graph', SceneGraph())
            target = scene_graph.find_closest_object(
                position=current_pos,
                object_type=target_type,
                max_distance=search_radius
            )
        except ImportError:
            # 如果SceneGraph不可用，使用模拟数据
            target = None

        result = {
            'target_type': target_type,
            'search_radius': search_radius,
            'target_found': bool(target),
            'target_position': target.get('position') if target else None,
            'timestamp': time.time()
        }

        self.logger.info(f"机器人 {robot.label} 搜索 {target_type}，结果: {'找到' if result['target_found'] else '未找到'}")

        # 将搜索结果添加到kwargs供效果使用
        kwargs.update(result)
        return result

    def _drone_execute(self, robot: Drone, **kwargs) -> Dict[str, Any]:
        """无人机搜索逻辑"""
        result = self._default_execute(robot, **kwargs)
        result['search_altitude'] = robot.get_state('altitude', 0)
        result['search_pattern'] = kwargs.get('search_pattern', 'spiral')
        return result

    def _ground_vehicle_execute(self, robot: GroundVehicle, **kwargs) -> Dict[str, Any]:
        """地面车辆搜索逻辑"""
        result = self._default_execute(robot, **kwargs)
        result['search_speed'] = kwargs.get('search_speed', 5.0)
        result['search_pattern'] = kwargs.get('search_pattern', 'grid')
        return result