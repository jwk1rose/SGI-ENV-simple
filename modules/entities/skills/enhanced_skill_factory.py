from typing import Dict, Type, List, Any, Optional
from modules.config.entities.skill_config import SkillName, SkillConfigManager
from .skill import Skill
from .navigate import NavigateSkill
from .take_photo import TakePhotoSkill
from .identify_anomaly import IdentifyAnomalySkill
from .load_object import LoadObjectSkill
from .unload_object import UnloadObjectSkill
from .search_for_target import SearchForTargetSkill
from .take_off import TakeOffSkill

class SkillFactory:
    """
    
    使用全局配置系统创建和管理技能实例
    """
    
    def __init__(self):
        """初始化增强技能工厂"""
        self.config_manager = SkillConfigManager()
        self._skill_classes: Dict[SkillName, Type[Skill]] = {
            SkillName.NAVIGATE: NavigateSkill,
            SkillName.TAKE_PHOTO: TakePhotoSkill,
            SkillName.IDENTIFY_ANOMALY: IdentifyAnomalySkill,
            SkillName.LOAD_OBJECT: LoadObjectSkill,
            SkillName.UNLOAD_OBJECT: UnloadObjectSkill,
            SkillName.SEARCH_FOR_TARGET: SearchForTargetSkill,
            SkillName.TAKE_OFF: TakeOffSkill
        }
    
    def create_skill(self, skill_name: SkillName, **kwargs) -> Skill:
        """创建技能实例
        
        Args:
            skill_name: 技能名称
            **kwargs: 额外的创建参数
            
        Returns:
            技能实例
            
        Raises:
            ValueError: 如果技能类型不支持
        """
        if skill_name not in self._skill_classes:
            available_skills = ", ".join([skill.value for skill in self._skill_classes.keys()])
            raise ValueError(f"不支持的技能类型: {skill_name.value}。可用类型: {available_skills}")
        
        skill_class = self._skill_classes[skill_name]
        return skill_class()
    
    def create_navigate_skill(self) -> NavigateSkill:
        """创建导航技能实例
        
        Returns:
            导航技能实例
        """
        return NavigateSkill()
    
    def create_take_photo_skill(self) -> TakePhotoSkill:
        """创建拍照技能实例
        
        Returns:
            拍照技能实例
        """
        return TakePhotoSkill()
    
    def create_identify_anomaly_skill(self) -> IdentifyAnomalySkill:
        """创建异常识别技能实例
        
        Returns:
            异常识别技能实例
        """
        return IdentifyAnomalySkill()
    
    def create_load_object_skill(self) -> LoadObjectSkill:
        """创建物体装载技能实例
        
        Returns:
            物体装载技能实例
        """
        return LoadObjectSkill()
    
    def create_unload_object_skill(self) -> UnloadObjectSkill:
        """创建物体卸载技能实例
        
        Returns:
            物体卸载技能实例
        """
        return UnloadObjectSkill()
    
    def create_search_for_target_skill(self) -> SearchForTargetSkill:
        """创建目标搜索技能实例
        
        Returns:
            目标搜索技能实例
        """
        return SearchForTargetSkill()
    
    def create_take_off_skill(self) -> TakeOffSkill:
        """创建起飞技能实例
        
        Returns:
            起飞技能实例
        """
        return TakeOffSkill()
    
    def get_available_skills(self) -> List[SkillName]:
        """获取所有可用的技能类型
        
        Returns:
            技能名称列表
        """
        return list(self._skill_classes.keys())
    
    def get_skill_info(self, skill_name: SkillName) -> Optional[Dict[str, Any]]:
        """获取技能信息
        
        Args:
            skill_name: 技能名称
            
        Returns:
            技能信息字典
        """
        skill_def = self.config_manager.get_skill_definition(skill_name)
        if not skill_def:
            return None
        
        return {
            "name": skill_def.name.value,
            "display_name": skill_def.display_name,
            "description": skill_def.description,
            "required_capabilities": [cap.name for cap in skill_def.required_capabilities],
            "attributes": [
                {
                    "name": attr.name,
                    "type": attr.attribute_type,
                    "required": attr.required,
                    "default": attr.default_value,
                    "description": attr.description
                }
                for attr in skill_def.attributes
            ],
            "preconditions": skill_def.preconditions,
            "effects": skill_def.effects,
            "execution_time": skill_def.execution_time_estimate,
            "energy_cost": skill_def.energy_cost,
            "compatible_robots": skill_def.compatible_robots
        }
    
    def validate_skill_config(self, skill_name: SkillName, config: Dict[str, Any]) -> bool:
        """验证技能配置
        
        Args:
            skill_name: 技能名称
            config: 配置字典
            
        Returns:
            配置是否有效
        """
        return self.config_manager.validate_skill_attributes(skill_name, config)
    
    def get_default_config(self, skill_name: SkillName) -> Dict[str, Any]:
        """获取默认配置
        
        Args:
            skill_name: 技能名称
            
        Returns:
            默认配置字典
        """
        return self.config_manager.create_default_skill_config(skill_name)