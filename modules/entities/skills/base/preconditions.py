from typing import Callable, Dict, Any, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.entity.robot.robot import Robot
    from modules.entity.prop.prop import Prop

from modules.entity.robot.capabilities import Capability

# 延迟导入避免循环依赖
def calculate_distance(pos1, pos2):
    """计算两点间距离"""
    try:
        from modules.utils.spatial_utils import calculate_distance as calc_dist
        return calc_dist(pos1, pos2)
    except ImportError:
        # 如果spatial_utils不存在，使用简单计算
        x1, y1 = pos1.get('x', 0), pos1.get('y', 0)
        x2, y2 = pos2.get('x', 0), pos2.get('y', 0)
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

class Precondition:
    """技能前置条件检查器"""
    def __init__(
        self, 
        condition: Callable[['Robot', Dict[str, Any]], bool],
        error_message: str
    ):
        self.condition = condition
        self.error_message = error_message

    def check(self, robot: 'Robot', **kwargs) -> bool:
        """执行前置条件检查"""
        return self.condition(robot, **kwargs)

class PreconditionSet:
    """前置条件集合"""
    def __init__(self, preconditions: List[Precondition] = None):
        self.preconditions = preconditions or []

    def add(self, precondition: Precondition):
        """添加前置条件"""
        self.preconditions.append(precondition)

    def check_all(self, robot: 'Robot', **kwargs) -> Tuple[bool, str]:
        """检查所有前置条件，返回是否通过及错误信息"""
        for precondition in self.preconditions:
            if not precondition.check(robot, **kwargs):
                return False, precondition.error_message
        return True, ""

# ==================== 常用前置条件工厂函数 ====================

def has_capability(capability: Capability) -> Precondition:
    """检查机器人是否拥有指定能力"""
    return Precondition(
        condition=lambda robot, **kwargs: capability in robot.capabilities,
        error_message=f"需要{capability.name}能力"
    )

def battery_above(threshold: float) -> Precondition:
    """检查电池电量是否高于阈值"""
    return Precondition(
        condition=lambda robot, **kwargs: robot.get_state('battery', 0) > threshold,
        error_message=f"电量不足，需要高于{threshold}%"
    )

def has_target_position() -> Precondition:
    """检查是否提供了目标位置参数"""
    return Precondition(
        condition=lambda robot, **kwargs: 'target_position' in kwargs,
        error_message="缺少目标位置参数"
    )

def has_target_object() -> Precondition:
    """检查是否提供了目标物体参数"""
    return Precondition(
        condition=lambda robot, **kwargs: 'target_object' in kwargs and isinstance(kwargs['target_object'], 'Prop'),
        error_message="缺少有效目标物体"
    )

def is_not_carrying_object() -> Precondition:
    """检查机器人是否未携带物体"""
    return Precondition(
        condition=lambda robot, **kwargs: not robot.get_state('carrying_object', False),
        error_message="机器人已携带物体"
    )

def is_carrying_object() -> Precondition:
    """检查机器人是否携带物体"""
    return Precondition(
        condition=lambda robot, **kwargs: robot.get_state('carrying_object', False),
        error_message="机器人未携带任何物体"
    )

def object_within_range(max_distance: float = 2.0) -> Precondition:
    """检查目标物体是否在指定范围内"""
    return Precondition(
        condition=lambda robot, **kwargs: (
            'target_object' in kwargs and 
            isinstance(kwargs['target_object'], 'Prop') and
            calculate_distance(
                robot.get_state('position', {'x': 0, 'y': 0}),
                kwargs['target_object'].get_state('position', {'x': 0, 'y': 0})
            ) <= max_distance
        ),
        error_message=f"目标物体超出{max_distance}米范围"
    )

def has_detection_area() -> Precondition:
    """检查是否提供了检测区域参数"""
    return Precondition(
        condition=lambda robot, **kwargs: 'detection_area' in kwargs,
        error_message="缺少检测区域参数"
    )

def has_target_type() -> Precondition:
    """检查是否提供了目标类型参数"""
    return Precondition(
        condition=lambda robot, **kwargs: 'target_type' in kwargs,
        error_message="缺少目标类型参数"
    )

def robot_status_is(status: str) -> Precondition:
    """检查机器人状态是否为指定状态"""
    return Precondition(
        condition=lambda robot, **kwargs: robot.get_state('status') == status,
        error_message=f"机器人状态必须为'{status}'"
    )

def robot_type_is(robot_type: str) -> Precondition:
    """检查机器人类型是否为指定类型"""
    return Precondition(
        condition=lambda robot, **kwargs: robot.get_state('type') == robot_type,
        error_message=f"机器人类型必须为'{robot_type}'"
    )