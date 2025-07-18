"""
技能描述系统

为技能提供结构化的自然语言描述，包括能力、前置条件、需求、输出等信息。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class SkillCategory(Enum):
    """技能分类"""
    MOVEMENT = "movement"      # 移动类
    MANIPULATION = "manipulation"  # 操作类
    SENSING = "sensing"        # 感知类
    COMMUNICATION = "communication"  # 通信类
    MAINTENANCE = "maintenance"  # 维护类


@dataclass
class SkillRequirement:
    """技能需求描述"""
    capability: str  # 所需能力
    min_battery: float = 0.0  # 最小电量
    min_payload: float = 0.0  # 最小载重
    description: str = ""  # 需求描述


@dataclass
class SkillPrecondition:
    """技能前置条件描述"""
    condition: str  # 条件描述
    check_type: str  # 检查类型：capability, battery, position, object, etc.
    description: str = ""  # 详细描述


@dataclass
class SkillOutput:
    """技能输出描述"""
    output_type: str  # 输出类型：position, status, data, object, etc.
    description: str  # 输出描述
    data_format: str = ""  # 数据格式


@dataclass
class SkillDescription:
    """技能完整描述"""
    # 基本信息
    name: str
    display_name: str
    category: SkillCategory
    description: str
    
    # 能力描述
    capabilities: List[str] = field(default_factory=list)
    
    # 需求描述
    requirements: List[SkillRequirement] = field(default_factory=list)
    
    # 前置条件描述
    preconditions: List[SkillPrecondition] = field(default_factory=list)
    
    # 输入参数描述
    input_params: Dict[str, str] = field(default_factory=dict)
    
    # 输出描述
    outputs: List[SkillOutput] = field(default_factory=list)
    
    # 执行时间描述
    execution_time: str = "variable"
    
    # 使用示例
    examples: List[str] = field(default_factory=list)
    
    # 注意事项
    notes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "category": self.category.value,
            "description": self.description,
            "capabilities": self.capabilities,
            "requirements": [
                {
                    "capability": req.capability,
                    "min_battery": req.min_battery,
                    "min_payload": req.min_payload,
                    "description": req.description
                } for req in self.requirements
            ],
            "preconditions": [
                {
                    "condition": pre.condition,
                    "check_type": pre.check_type,
                    "description": pre.description
                } for pre in self.preconditions
            ],
            "input_params": self.input_params,
            "outputs": [
                {
                    "output_type": out.output_type,
                    "description": out.description,
                    "data_format": out.data_format
                } for out in self.outputs
            ],
            "execution_time": self.execution_time,
            "examples": self.examples,
            "notes": self.notes
        }
    
    def get_summary(self) -> str:
        """获取技能摘要描述"""
        return f"{self.display_name}: {self.description}"
    
    def get_requirements_text(self) -> str:
        """获取需求文本描述"""
        if not self.requirements:
            return "无特殊需求"
        
        req_texts = []
        for req in self.requirements:
            text = f"需要{req.capability}"
            if req.min_battery > 0:
                text += f"，电量≥{req.min_battery}%"
            if req.min_payload > 0:
                text += f"，载重≥{req.min_payload}kg"
            if req.description:
                text += f"（{req.description}）"
            req_texts.append(text)
        
        return "；".join(req_texts)
    
    def get_preconditions_text(self) -> str:
        """获取前置条件文本描述"""
        if not self.preconditions:
            return "无前置条件"
        
        pre_texts = []
        for pre in self.preconditions:
            text = pre.condition
            if pre.description:
                text += f"（{pre.description}）"
            pre_texts.append(text)
        
        return "；".join(pre_texts)
    
    def get_outputs_text(self) -> str:
        """获取输出文本描述"""
        if not self.outputs:
            return "无输出"
        
        out_texts = []
        for out in self.outputs:
            text = f"{out.output_type}：{out.description}"
            if out.data_format:
                text += f"（格式：{out.data_format}）"
            out_texts.append(text)
        
        return "；".join(out_texts)


class SkillDescriptionRegistry:
    """技能描述注册表"""
    
    _descriptions: Dict[str, SkillDescription] = {}
    
    @classmethod
    def register(cls, skill_name: str, description: SkillDescription):
        """注册技能描述"""
        cls._descriptions[skill_name.lower()] = description
    
    @classmethod
    def get(cls, skill_name: str) -> Optional[SkillDescription]:
        """获取技能描述"""
        return cls._descriptions.get(skill_name.lower())
    
    @classmethod
    def get_all(cls) -> Dict[str, SkillDescription]:
        """获取所有技能描述"""
        return cls._descriptions.copy()
    
    @classmethod
    def get_all_descriptions(cls) -> Dict[str, SkillDescription]:
        """获取所有技能描述（别名方法）"""
        return cls.get_all()
    
    @classmethod
    def get_by_category(cls, category: SkillCategory) -> List[SkillDescription]:
        """根据分类获取技能描述"""
        return [
            desc for desc in cls._descriptions.values()
            if desc.category == category
        ]
    
    @classmethod
    def search(cls, keyword: str) -> List[SkillDescription]:
        """搜索技能描述"""
        keyword_lower = keyword.lower()
        results = []
        
        for desc in cls._descriptions.values():
            if (keyword_lower in desc.name.lower() or
                keyword_lower in desc.display_name.lower() or
                keyword_lower in desc.description.lower() or
                any(keyword_lower in cap.lower() for cap in desc.capabilities)):
                results.append(desc)
        
        return results 