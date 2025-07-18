from typing import Dict, Any, Optional, Set
from .robot import Robot
from .capabilities import Capability
from modules.utils.global_config import RobotStatus


class Drone(Robot):
    """
    无人机（Drone），是 Robot 的一个具体子类。

    它专用于空中操作，拥有飞行能力，并具有自己独特的默认属性，
    例如类型、最大速度和悬停时的初始状态。
    """

    def __init__(self, entity_id: int, label: str, initial_state: Optional[Dict[str, Any]] = None):
        """
        初始化一个新的 Drone 实例。

        Args:
            entity_id (int): 实体的唯一ID。
            label (str): 实体的人类可读标签。
            initial_state (Optional[Dict[str, Any]]): 用户传入的、用于覆盖默认值的初始状态。
        """
        # 1. 定义无人机专属的默认能力集合
        drone_capabilities = {
            Capability.FLY,
            Capability.NAVIGATE,  # 添加导航能力
            Capability.SENSOR,    # 添加传感器能力
            Capability.ANALYZE,   # 添加分析能力
            Capability.MANIPULATE, # 添加操作能力
            Capability.CARRY_PAYLOAD,
            Capability.TAKE_PHOTO,
            Capability.SEARCH,
            Capability.IDENTIFY_ANOMALY
        }

        # 2. 定义无人机专属的默认状态
        #    这些值会覆盖掉 Robot 基类中的通用默认值。
        drone_defaults = {
            'type': 'drone',
            'max_speed_ms': 20,
            'max_payload_kg': 3,
            'status': RobotStatus.LANDED.value  # 无人机的初始状态为"已降落"
        }

        # 3. 如果用户传入了 initial_state，用它来更新无人机的默认状态。
        if initial_state:
            drone_defaults.update(initial_state)

        # 4. 调用父类(Robot)的构造函数，传入所有信息。
        super().__init__(
            entity_id=entity_id,
            label=label,
            capabilities=drone_capabilities,
            initial_state=drone_defaults
        )
