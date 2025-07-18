"""道具基类模块

定义道具的基础结构和行为。
"""
from typing import Dict, Any, Optional
from modules.entities import Entity
from modules.config.manager import GlobalConfigManager
from modules.config.base.enums import PropType, ObjectStatus


class Prop(Entity):
    """道具基类
    
    代表场景中一个被动的、有状态的物体。
    它本身不执行任何动作，但其状态可以被其他实体（如机器人）所改变。
    """
    
    def __init__(self, entity_id: int, label: str, initial_state: Dict[str, Any], 
                 prop_type: Optional[PropType] = None):
        """初始化道具实例
        
        Args:
            entity_id: 唯一ID
            label: 标签
            initial_state: 初始状态字典
            prop_type: 道具类型（可选）
        """
        super().__init__(entity_id, label, initial_state)
        self._prop_type = prop_type
        self._config_manager = GlobalConfigManager()
    
    @property
    def prop_type(self) -> Optional[PropType]:
        """获取道具类型"""
        return self._prop_type
    
    def get_type_definition(self):
        """获取类型定义"""
        if self._prop_type:
            return self._config_manager.get_prop_definition(self._prop_type)
        return None
    
    def validate_state(self) -> bool:
        """验证当前状态是否符合类型定义"""
        if not self._prop_type:
            return True
        
        definition = self.get_type_definition()
        if not definition:
            return True
        
        # 验证必需属性
        for attr_def in definition.base_attributes:
            if attr_def.is_required and attr_def.name not in self.state:
                return False
        
        return True
    
    def get_interaction_rules(self) -> Dict[str, Any]:
        """获取交互规则"""
        definition = self.get_type_definition()
        return definition.interaction_rules if definition else {}
    
    def get_physical_properties(self) -> Dict[str, Any]:
        """获取物理属性"""
        definition = self.get_type_definition()
        return definition.physical_properties if definition else {}
