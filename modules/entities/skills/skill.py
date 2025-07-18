import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Set, List, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.entity.robot.robot import Robot
    from modules.entity.robot.drone import Drone
    from modules.entity.robot.ground_vehicle import GroundVehicle

from modules.entity.robot.capabilities import Capability
from .preconditions import PreconditionSet
from .effects import SkillEffect

def get_logger(name: str) -> logging.Logger:
    """获取技能专用日志器"""
    return logging.getLogger(f"skill.{name}")

class Skill(ABC):
    """技能基类 - 简洁的执行框架"""
    
    # 技能所需能力
    required_capabilities: Set[Capability] = set()
    
    def __init__(self):
        # 初始化前置条件和效果
        self.preconditions = PreconditionSet()
        self.effects: List[SkillEffect] = []
        self.logger = get_logger(self.__class__.__name__)
        self._setup()
        self._validate_implementation()

    def _validate_implementation(self):
        """自动验证技能实现完整性"""
        if not self.required_capabilities:
            self.logger.warning(f"技能{self.__class__.__name__}未声明能力需求")

    def execute_with_logging(self, robot: 'Robot', **kwargs) -> Dict[str, Any]:
        """带日志的执行包装器"""
        self.logger.info(f"执行技能: {self.__class__.__name__} (机器人ID: {robot.id})")
        start_time = time.time()
        try:
            result = self.execute(robot, **kwargs)
            self.logger.info(f"技能执行成功，耗时{time.time()-start_time:.2f}s")
            return result
        except Exception as e:
            self.logger.error(f"技能执行失败: {str(e)}")
            raise

    def _setup(self):
        """初始化钩子，子类可重写以设置前置条件和效果"""
        pass

    def check_preconditions(self, robot: 'Robot', **kwargs) -> Tuple[bool, str]:
        """检查所有前置条件"""
        return self.preconditions.check_all(robot, **kwargs)

    def apply_effects(self, robot: 'Robot', **kwargs) -> Dict[str, Any]:
        """应用所有效果"""
        results = {}
        for effect in self.effects:
            effect_name = effect.__class__.__name__
            results[effect_name] = effect.apply(robot, **kwargs)
        return results

    def execute(self, robot: 'Robot', **kwargs) -> Dict[str, Any]:
        """执行技能完整流程"""
        # 1. 检查前置条件
        pre_check, message = self.check_preconditions(robot, **kwargs)
        if not pre_check:
            return {
                'success': False, 
                'error': message,
                'skill_name': self.__class__.__name__,
                'robot_id': robot.id
            }

        # 2. 根据机器人类型执行相应逻辑
        try:
            # 延迟导入避免循环依赖
            from modules.entity.robot.drone import Drone
            from modules.entity.robot.ground_vehicle import GroundVehicle
            
            if isinstance(robot, Drone):
                execution_result = self._drone_execute(robot, **kwargs)
            elif isinstance(robot, GroundVehicle):
                execution_result = self._ground_vehicle_execute(robot, **kwargs)
            else:
                execution_result = self._default_execute(robot, **kwargs)
            
            # 3. 应用效果
            effects_result = self.apply_effects(robot, **kwargs)
            
            # 4. 构建返回结果
            result = {
                'success': True,
                'skill_name': self.__class__.__name__,
                'robot_id': robot.id,
                'execution_result': execution_result,
                'effects_result': effects_result,
                'timestamp': time.time()
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"技能执行异常: {e}")
            return {
                'success': False,
                'error': str(e),
                'skill_name': self.__class__.__name__,
                'robot_id': robot.id
            }

    def _default_execute(self, robot: 'Robot', **kwargs) -> Dict[str, Any]:
        """默认执行逻辑，子类可重写"""
        return {'message': '默认执行完成'}

    def _drone_execute(self, robot: 'Drone', **kwargs) -> Dict[str, Any]:
        """无人机执行逻辑，子类可重写"""
        return self._default_execute(robot, **kwargs)

    def _ground_vehicle_execute(self, robot: 'GroundVehicle', **kwargs) -> Dict[str, Any]:
        """地面车辆执行逻辑，子类可重写"""
        return self._default_execute(robot, **kwargs)
