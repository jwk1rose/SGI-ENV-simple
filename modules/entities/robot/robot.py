from typing import Dict, Any, Optional, Set, TYPE_CHECKING
from modules.entity.entity import Entity

if TYPE_CHECKING:
    from modules.entity.skill.skill import Skill

from .capabilities import Capability
from .state_machine import RobotStateMachine
from modules.utils.global_config import RobotStatus

class Robot(Entity):
    """机器人基类"""
    def __init__(
        self, 
        entity_id: int, 
        label: str, 
        capabilities: Set[Capability],
        initial_state: Optional[Dict[str, Any]] = None
    ):
        # 1. 定义机器人专属的默认状态
        base_state = {
            'position': {'x': 0, 'y': 0},
            'battery': 100.0,
            'status': RobotStatus.IDLE.value,
            'max_payload_kg': 0,
            'carrying_object': False,
            'carrying_object_id': None
        }

        # 2. 如果用户提供了初始状态，则用它来更新默认状态
        if initial_state:
            base_state.update(initial_state)

        # 3. 调用父类构造函数
        super().__init__(entity_id, label, initial_state=base_state)

        # 4. 初始化能力和技能系统
        self.capabilities: Set[Capability] = capabilities
        self.skills: Dict[str, 'Skill'] = {}
        self.state_machine = RobotStateMachine(self)

    def add_skill(self, name: str, skill_instance: 'Skill'):
        """添加技能"""
        # 延迟导入避免循环依赖
        from modules.entity.skill.skill import Skill as SkillClass
        
        if not isinstance(skill_instance, SkillClass):
            raise TypeError("skill_instance 必须是 Skill 类的实例")

        # 检查技能所需能力
        required_caps = skill_instance.required_capabilities
        missing_caps = required_caps - self.capabilities
        if missing_caps:
            raise ValueError(f"机器人缺少技能所需能力: {[cap.name for cap in missing_caps]}")

        self.skills[name] = skill_instance
        print(f"为 '{self.label}' 添加技能: '{name}'")

    def execute_skill(self, name: str, **kwargs) -> Dict[str, Any]:
        """执行技能并返回结果"""
        if name not in self.skills:
            return {'success': False, 'error': f'技能{name}不存在'}

        # 状态检查
        if not self.state_machine.can_execute_skill():
            return {
                'success': False, 
                'error': f'当前状态{self.state_machine.current_state}无法执行技能'
            }

        # 执行技能
        skill = self.skills[name]
        return skill.execute(self, **kwargs)

    def get_capabilities(self) -> Set[Capability]:
        """获取机器人能力集合"""
        return self.capabilities

    def set_status(self, status: str):
        """设置机器人状态"""
        from modules.utils.global_config import GlobalConfig
        if GlobalConfig.validate_robot_status(status):
            self.set_state('status', status)
        else:
            raise ValueError(f"无效的机器人状态: {status}")

    def get_status(self) -> str:
        """获取机器人状态"""
        return self.get_state('status', RobotStatus.IDLE.value)
