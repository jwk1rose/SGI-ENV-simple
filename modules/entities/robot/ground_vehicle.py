

from .robot import Robot
from .capabilities import Capability
from typing import Optional, Dict, Any
from modules.utils.global_config import RobotStatus


class GroundVehicle(Robot):
    """
    地面车辆（GroundVehicle），是 Robot 的一个具体子类。

    它专用于地面操作，具有自己独特的默认属性，如类型、最大速度和载重。
    """

    def __init__(self, entity_id: int, label: str, initial_state: Optional[Dict[str, Any]] = None):
        """
        初始化一个新的 GroundVehicle 实例。

        Args:
            entity_id (int): 实体的唯一ID。
            label (str): 实体的人类可读标签。
            initial_state (Optional[Dict[str, Any]]): 用户传入的、用于覆盖默认值的初始状态。
        """
        # 1. 定义地面车辆专属的默认能力集合
        ground_capabilities = {
            Capability.DRIVE,
            Capability.NAVIGATE,  # 添加导航能力
            Capability.SENSOR,    # 添加传感器能力
            Capability.ANALYZE,   # 添加分析能力
            Capability.MANIPULATE, # 添加操作能力
            Capability.CARRY_PAYLOAD,
            Capability.TAKE_PHOTO
        }

        # 2. 定义地面车辆专属的默认状态
        #    这些值会覆盖掉 Robot 基类中的通用默认值。
        ground_vehicle_defaults = {
            'type': 'ground_vehicle',
            'max_speed_ms': 5,
            'max_payload_kg': 150,
            'status': RobotStatus.PARKED.value  # 地面车辆的初始状态更适合叫 'parked'
        }

        # 3. 如果用户传入了 initial_state，用它来更新地面车辆的默认状态。
        #    这保证了用户的自定义设置有最高优先级。
        if initial_state:
            ground_vehicle_defaults.update(initial_state)

        # 4. 调用父类(Robot)的构造函数。
        #    传入ID、标签、专属的能力集合，以及合并后的最终状态。
        #    Robot的__init__会再将这个状态与它自己的base_state合并，
        #    但因为我们已经覆盖了冲突的键，所以这里的设置会生效。
        super().__init__(
            entity_id=entity_id,
            label=label,
            capabilities=ground_capabilities,
            initial_state=ground_vehicle_defaults
        )
