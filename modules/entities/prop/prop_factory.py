"""
道具工厂模块

基于全局配置创建道具实例。
"""
from typing import Dict, Any, Optional
from ...config.entities.prop_config import prop_config_manager, PropName
from .car import Car
from .cargo import Cargo
from .security_breach import SecurityBreach
from .equioment_failure import EquipmentFailure
from .prop import Prop


class PropFactory:
    """道具工厂类
    
    基于全局配置创建道具实例。
    """
    
    # 道具类映射
    _PROP_CLASSES = {
        PropName.CAR: Car,
        PropName.CARGO: Cargo,
        PropName.SECURITY_BREACH: SecurityBreach,
        PropName.EQUIPMENT_FAILURE: EquipmentFailure
    }
    
    @classmethod
    def create_prop(cls, prop_name: PropName, entity_id: int, label: str, **kwargs) -> Optional[Prop]:
        """创建道具实例
        
        Args:
            prop_name: 道具名称
            entity_id: 实体ID
            label: 标签
            **kwargs: 额外的配置参数
            
        Returns:
            道具实例，如果创建失败则返回None
        """
        # 获取道具定义
        definition = prop_config_manager.get_prop_definition(prop_name)
        if not definition:
            raise ValueError(f"未知的道具类型: {prop_name}")
        
        # 创建配置
        config = prop_config_manager.create_default_config(prop_name, **kwargs)
        
        # 验证配置
        if not prop_config_manager.validate_prop_config(prop_name, config):
            raise ValueError(f"道具配置验证失败: {prop_name}")
        
        # 获取道具类
        prop_class = cls._PROP_CLASSES.get(prop_name)
        if not prop_class:
            raise ValueError(f"未找到道具类: {prop_name}")
        
        # 根据不同道具类型创建实例
        try:
            if prop_name == PropName.CAR:
                return prop_class(
                    entity_id=entity_id,
                    label=label,
                    license_plate=config["license_plate"]
                )
            elif prop_name == PropName.CARGO:
                return prop_class(
                    entity_id=entity_id,
                    label=label,
                    weight_kg=config["weight_kg"],
                    is_fragile=config.get("is_fragile", False)
                )
            elif prop_name == PropName.SECURITY_BREACH:
                return prop_class(
                    entity_id=entity_id,
                    label=label,
                    breach_location=config["breach_location"]
                )
            elif prop_name == PropName.EQUIPMENT_FAILURE:
                return prop_class(
                    entity_id=entity_id,
                    label=label,
                    failed_equipment_id=config["failed_equipment_id"],
                    severity=config.get("severity", "medium")
                )
        except Exception as e:
            raise ValueError(f"创建道具实例失败: {e}")
        
        return None
    
    @classmethod
    def create_car(cls, entity_id: int, label: str, license_plate: str) -> Car:
        """创建汽车实例
        
        Args:
            entity_id: 实体ID
            label: 标签
            license_plate: 车牌号
            
        Returns:
            汽车实例
        """
        return cls.create_prop(
            PropName.CAR,
            entity_id=entity_id,
            label=label,
            license_plate=license_plate
        )
    
    @classmethod
    def create_cargo(cls, entity_id: int, label: str, weight_kg: float, is_fragile: bool = False) -> Cargo:
        """创建货物实例
        
        Args:
            entity_id: 实体ID
            label: 标签
            weight_kg: 重量
            is_fragile: 是否易碎
            
        Returns:
            货物实例
        """
        return cls.create_prop(
            PropName.CARGO,
            entity_id=entity_id,
            label=label,
            weight_kg=weight_kg,
            is_fragile=is_fragile
        )
    
    @classmethod
    def create_security_breach(cls, entity_id: int, label: str, breach_location: Dict[str, float]) -> SecurityBreach:
        """创建安全隐患实例
        
        Args:
            entity_id: 实体ID
            label: 标签
            breach_location: 事件位置
            
        Returns:
            安全隐患实例
        """
        return cls.create_prop(
            PropName.SECURITY_BREACH,
            entity_id=entity_id,
            label=label,
            breach_location=breach_location
        )
    
    @classmethod
    def create_equipment_failure(cls, entity_id: int, label: str, failed_equipment_id: int, severity: str = "medium") -> EquipmentFailure:
        """创建设备故障实例
        
        Args:
            entity_id: 实体ID
            label: 标签
            failed_equipment_id: 故障设备ID
            severity: 严重程度
            
        Returns:
            设备故障实例
        """
        return cls.create_prop(
            PropName.EQUIPMENT_FAILURE,
            entity_id=entity_id,
            label=label,
            failed_equipment_id=failed_equipment_id,
            severity=severity
        )
    
    @classmethod
    def get_available_props(cls) -> List[PropName]:
        """获取可用的道具类型
        
        Returns:
            道具类型列表
        """
        return prop_config_manager.get_all_prop_names()
    
    @classmethod
    def get_prop_info(cls, prop_name: PropName) -> Optional[Dict[str, Any]]:
        """获取道具信息
        
        Args:
            prop_name: 道具名称
            
        Returns:
            道具信息字典
        """
        definition = prop_config_manager.get_prop_definition(prop_name)
        if not definition:
            return None
        
        return {
            "name": definition.prop_name.value,
            "display_name": definition.display_name,
            "description": definition.description,
            "class_name": definition.class_name,
            "attributes": [{
                "name": attr.name,
                "type": attr.attribute_type,
                "description": attr.description,
                "required": attr.is_required,
                "default": attr.default_value
            } for attr in definition.attributes],
            "metadata": definition.metadata
        }