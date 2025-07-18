"""
增强的机器人工厂模块

基于全局配置创建机器人实例。
"""
from typing import Dict, Any, Optional, Set
from ...config.entities.robot_config import robot_config_manager, RobotName
from .drone import Drone
from .ground_vehicle import GroundVehicle
from .robot import Robot
from .capabilities import Capability, get_capability_by_name


class EnhancedRobotFactory:
    """增强的机器人工厂类
    
    基于全局配置创建机器人实例。
    """
    
    # 机器人类映射
    _ROBOT_CLASSES = {
        RobotName.DRONE: Drone,
        RobotName.GROUND_VEHICLE: GroundVehicle
    }
    
    @classmethod
    def create_robot(cls, robot_name: RobotName, entity_id: int, label: str, **kwargs) -> Optional[Robot]:
        """创建机器人实例
        
        Args:
            robot_name: 机器人名称
            entity_id: 实体ID
            label: 标签
            **kwargs: 额外的配置参数
            
        Returns:
            机器人实例，如果创建失败则返回None
        """
        # 获取机器人定义
        definition = robot_config_manager.get_robot_definition(robot_name)
        if not definition:
            raise ValueError(f"未知的机器人类型: {robot_name}")
        
        # 创建配置
        config = robot_config_manager.create_default_config(robot_name, **kwargs)
        
        # 验证配置
        if not robot_config_manager.validate_robot_config(robot_name, config):
            raise ValueError(f"机器人配置验证失败: {robot_name}")
        
        # 获取机器人类
        robot_class = cls._ROBOT_CLASSES.get(robot_name)
        if not robot_class:
            raise ValueError(f"未找到机器人类: {robot_name}")
        
        # 准备初始状态（移除类型字段，因为它不属于initial_state）
        initial_state = {k: v for k, v in config.items() if k != "type"}
        
        # 创建实例
        try:
            return robot_class(
                entity_id=entity_id,
                label=label,
                initial_state=initial_state
            )
        except Exception as e:
            raise ValueError(f"创建机器人实例失败: {e}")
    
    @classmethod
    def create_drone(cls, entity_id: int, label: str, **kwargs) -> Drone:
        """创建无人机实例
        
        Args:
            entity_id: 实体ID
            label: 标签
            **kwargs: 额外的配置参数
            
        Returns:
            无人机实例
        """
        return cls.create_robot(
            RobotName.DRONE,
            entity_id=entity_id,
            label=label,
            **kwargs
        )
    
    @classmethod
    def create_ground_vehicle(cls, entity_id: int, label: str, **kwargs) -> GroundVehicle:
        """创建地面车辆实例
        
        Args:
            entity_id: 实体ID
            label: 标签
            **kwargs: 额外的配置参数
            
        Returns:
            地面车辆实例
        """
        return cls.create_robot(
            RobotName.GROUND_VEHICLE,
            entity_id=entity_id,
            label=label,
            **kwargs
        )
    
    @classmethod
    def create_robot_from_config(cls, config: Dict[str, Any]) -> Robot:
        """从配置字典创建机器人实例（兼容原有接口）
        
        Args:
            config: 配置字典，必须包含 'id', 'type' 字段
            
        Returns:
            机器人实例
        """
        # 验证关键字段
        robot_type_str = config.get("type")
        if not robot_type_str:
            raise ValueError("机器人配置中必须包含 'type' 字段。")
        
        entity_id = config.get("id")
        if entity_id is None:
            raise ValueError("机器人配置中必须包含 'id' 字段。")
        
        # 转换类型字符串为枚举
        try:
            robot_name = RobotName(robot_type_str.lower())
        except ValueError:
            supported_types = ", ".join([name.value for name in RobotName])
            raise ValueError(
                f"未知的机器人类型: '{robot_type_str}'。支持的类型有: {supported_types}"
            )
        
        # 准备参数
        label = config.get("label", f"{robot_type_str}_{entity_id}")
        initial_state = config.get("initial_state", {})
        
        return cls.create_robot(
            robot_name=robot_name,
            entity_id=entity_id,
            label=label,
            **initial_state
        )
    
    @classmethod
    def get_available_robots(cls) -> List[RobotName]:
        """获取可用的机器人类型
        
        Returns:
            机器人类型列表
        """
        return robot_config_manager.get_all_robot_names()
    
    @classmethod
    def get_robot_info(cls, robot_name: RobotName) -> Optional[Dict[str, Any]]:
        """获取机器人信息
        
        Args:
            robot_name: 机器人名称
            
        Returns:
            机器人信息字典
        """
        definition = robot_config_manager.get_robot_definition(robot_name)
        if not definition:
            return None
        
        return {
            "name": definition.robot_name.value,
            "display_name": definition.display_name,
            "description": definition.description,
            "class_name": definition.class_name,
            "default_capabilities": definition.default_capabilities,
            "attributes": [{
                "name": attr.name,
                "type": attr.attribute_type,
                "description": attr.description,
                "required": attr.is_required,
                "default": attr.default_value
            } for attr in definition.attributes],
            "metadata": definition.metadata
        }
    
    @classmethod
    def get_robot_capabilities(cls, robot_name: RobotName) -> Set[Capability]:
        """获取机器人的默认能力集合
        
        Args:
            robot_name: 机器人名称
            
        Returns:
            能力集合
        """
        capability_names = robot_config_manager.get_default_capabilities(robot_name)
        capabilities = set()
        
        for cap_name in capability_names:
            try:
                capability = get_capability_by_name(cap_name)
                capabilities.add(capability)
            except ValueError:
                # 忽略未知能力
                continue
        
        return capabilities
    
    @classmethod
    def validate_robot_specification(cls, robot_name: RobotName, spec: Dict[str, Any]) -> bool:
        """验证机器人规格
        
        Args:
            robot_name: 机器人名称
            spec: 规格字典
            
        Returns:
            是否验证通过
        """
        return robot_config_manager.validate_robot_config(robot_name, spec)