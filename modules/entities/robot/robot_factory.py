"""
机器人工厂

根据配置字典动态创建具体的机器人实例。
"""

from typing import Dict, Any, Type

from .robot import Robot
from .drone import Drone
from .ground_vehicle import GroundVehicle


class RobotFactory:
    """
    一个无状态的工厂类，负责根据配置字典动态创建具体的机器人实例。

    它使用注册表模式来映射类型字符串到具体的机器人-实现类，
    从而实现清晰、可扩展的设计。
    """

    # _robot_map 是一个内部注册表。
    # 当需要支持新的机器人类型时，只需在这里添加一行。
    _robot_map: Dict[str, Type[Robot]] = {
        "drone": Drone,
        "ground_vehicle": GroundVehicle,
    }

    @classmethod
    def create_robot(cls, config: Dict[str, Any]) -> Robot:
        """
        根据配置字典创建并返回一个机器人实例。

        这是一个类方法，可以直接通过 RobotFactory.create_robot() 调用。

        Args:
            config (Dict[str, Any]): 单个机器人的配置，
                                     必须包含 'id' 和 'type' 字段。

        Returns:
            一个 Robot 的子类实例 (例如 Drone 或 GroundVehicle)。

        Raises:
            ValueError: 如果配置缺少关键字段，或机器人类型未知。
        """
        # 1. 验证关键字段是否存在
        robot_type_str = config.get("type")
        if not robot_type_str:
            raise ValueError("机器人配置中必须包含 'type' 字段。")

        entity_id = config.get("id")
        if not entity_id:
            raise ValueError("机器人配置中必须包含 'id' 字段。")

        # 2. 从注册表中查找对应的机器人-实现类
        robot_class = cls._robot_map.get(robot_type_str.lower())

        if not robot_class:
            supported_types = ", ".join(cls._robot_map.keys())
            raise ValueError(
                f"未知的机器人类型: '{robot_type_str}'。支持的类型有: {supported_types}"
            )

        # 3. 准备构造函数所需的其他参数，并提供合理的默认值
        label = config.get("label", f"{robot_type_str}_{entity_id}")
        initial_state = config.get("initial_state", {})

        # 4. 调用找到的类的构造函数来创建实例，并返回
        print(f"FACTORY: Creating '{label}' as a {robot_class.__name__} instance.")
        return robot_class(
            entity_id=entity_id,
            label=label,
            initial_state=initial_state
        )