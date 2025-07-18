from typing import Dict, Type, List, Any
import os
import importlib
import inspect
from .skill import Skill
from .navigate import NavigateSkill
from .take_photo import TakePhotoSkill
from .identify_anomaly import IdentifyAnomalySkill
from .load_object import LoadObjectSkill
from .unload_object import UnloadObjectSkill
from .search_for_target import SearchForTargetSkill
from .take_off import TakeOffSkill
from modules.utils.global_config import GlobalConfig, SkillNameMapping

class SkillFactory:
    """技能工厂 - 统一的技能创建和管理"""
    
    # 技能注册表 - 使用实际的技能名称
    _skill_map: Dict[str, Type[Skill]] = {}
    _initialized = False

    @classmethod
    def _initialize_skills(cls):
        """初始化技能注册表"""
        if cls._initialized:
            return
        
        # 手动注册已知技能（保持向后兼容）
        cls._skill_map.update({
            "navigate": NavigateSkill,
            "take_photo": TakePhotoSkill,
            "identify_anomaly": IdentifyAnomalySkill,
            "load_object": LoadObjectSkill,
            "unload_object": UnloadObjectSkill,
            "search_for_target": SearchForTargetSkill,
            "take_off": TakeOffSkill,
        })
        
        # 自动发现并注册其他技能
        cls._auto_discover_skills()
        
        cls._initialized = True

    @classmethod
    def _auto_discover_skills(cls):
        """自动发现技能文件夹中的所有技能"""
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 遍历目录中的所有 .py 文件
        for filename in os.listdir(current_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = filename[:-3]  # 移除 .py 后缀
                
                try:
                    # 导入模块
                    module = importlib.import_module(f'.{module_name}', package='modules.entity.skill')
                    
                    # 查找模块中的技能类
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, Skill) and 
                            obj != Skill and
                            hasattr(obj, '__name__')):
                            
                            # 生成技能名称（去掉 'Skill' 后缀，转为小写）
                            skill_name = obj.__name__.replace('Skill', '').lower()
                            
                            # 注册技能
                            cls._skill_map[skill_name] = obj
                            
                except Exception as e:
                    # 忽略导入错误，继续处理其他文件
                    continue

    @classmethod
    def register_skill(cls, skill_name: str, skill_class: Type[Skill]):
        """注册新技能"""
        cls._initialize_skills()
        
        if not issubclass(skill_class, Skill):
            raise TypeError("skill_class 必须是 Skill 的子类")
        cls._skill_map[skill_name.lower()] = skill_class

    @classmethod
    def create_skill(cls, name: str) -> Skill:
        """创建技能实例"""
        cls._initialize_skills()
        
        # 使用全局配置进行技能名称映射
        actual_skill_name = SkillNameMapping.map_scene_to_actual(name)
        skill_name_lower = actual_skill_name.lower()
        skill_class = cls._skill_map.get(skill_name_lower)

        if not skill_class:
            supported_skills = ", ".join(cls._skill_map.keys())
            raise ValueError(
                f"未知的技能类型: '{name}' (映射后: '{actual_skill_name}')。支持的类型有: {supported_skills}"
            )

        return skill_class()

    @classmethod
    def list_skills(cls) -> List[str]:
        """列出所有支持的技能"""
        cls._initialize_skills()
        return list(cls._skill_map.keys())

    @classmethod
    def list_scene_skills(cls) -> List[str]:
        """列出所有支持的场景技能名称"""
        return SkillNameMapping.get_all_scene_skills()

    @classmethod
    def get_skill_info(cls, name: str) -> Dict[str, Any]:
        """获取技能信息"""
        cls._initialize_skills()
        
        # 使用全局配置进行技能名称映射
        actual_skill_name = SkillNameMapping.map_scene_to_actual(name)
        skill_class = cls._skill_map.get(actual_skill_name.lower())
        if not skill_class:
            return {}
        
        skill_instance = skill_class()
        return {
            'name': name,
            'actual_name': actual_skill_name,
            'required_capabilities': list(skill_instance.required_capabilities),
            'preconditions_count': len(skill_instance.preconditions.preconditions),
            'effects_count': len(skill_instance.effects)
        }

    @classmethod
    def validate_skill_name(cls, skill_name: str) -> bool:
        """验证技能名称是否有效"""
        return GlobalConfig.validate_skill_name(skill_name)

    @classmethod
    def get_available_skills_for_robot_type(cls, robot_type: str) -> List[str]:
        """根据机器人类型获取可用技能"""
        cls._initialize_skills()
        
        available_skills = []
        for skill_name, skill_class in cls._skill_map.items():
            try:
                skill_instance = skill_class()
                # 这里可以根据机器人类型和技能要求进行过滤
                # 暂时返回所有技能
                available_skills.append(skill_name)
            except Exception:
                continue
        
        return available_skills