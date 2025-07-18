"""
技能执行上下文模块

提供统一的技能执行环境信息访问接口，实现单向数据流。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Protocol
from dataclasses import dataclass
from modules.entity.robot.robot import Robot
from modules.entity.prop.prop import Prop


class EnvironmentProvider(Protocol):
    """环境信息提供者协议"""
    
    def get_object_by_id(self, obj_id: Any) -> Optional[Dict[str, Any]]:
        """根据ID获取对象信息"""
        ...
    
    def find_objects_by_type(self, obj_type: str) -> List[Dict[str, Any]]:
        """根据类型查找对象"""
        ...
    
    def find_objects_in_area(self, center: Dict[str, float], radius: float) -> List[Dict[str, Any]]:
        """查找指定区域内的对象"""
        ...
    
    def get_scene_graph(self) -> Any:
        """获取场景图"""
        ...
    
    def get_time(self) -> float:
        """获取当前时间"""
        ...


class StateUpdater(Protocol):
    """状态更新器协议"""
    
    def update_robot_state(self, robot_id: Any, updates: Dict[str, Any]) -> None:
        """更新机器人状态"""
        ...
    
    def update_object_state(self, obj_id: Any, updates: Dict[str, Any]) -> None:
        """更新对象状态"""
        ...
    
    def notify_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """通知事件"""
        ...


@dataclass
class SkillContext:
    """技能执行上下文"""
    
    # 环境信息提供者
    environment: EnvironmentProvider
    
    # 状态更新器
    state_updater: StateUpdater
    
    # 执行参数
    params: Dict[str, Any]
    
    # 执行时间
    execution_time: float
    
    # 日志记录器
    logger: Any = None
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """获取执行参数"""
        return self.params.get(key, default)
    
    def has_param(self, key: str) -> bool:
        """检查是否有指定参数"""
        return key in self.params
    
    def get_target_object(self) -> Optional[Dict[str, Any]]:
        """获取目标对象信息"""
        target_id = self.get_param('target_object_id')
        if target_id:
            return self.environment.get_object_by_id(target_id)
        return None
    
    def get_target_position(self) -> Optional[Dict[str, float]]:
        """获取目标位置"""
        return self.get_param('target_position')
    
    def find_nearby_objects(self, robot_position: Dict[str, float], 
                           radius: float = 10.0) -> List[Dict[str, Any]]:
        """查找附近的对象"""
        return self.environment.find_objects_in_area(robot_position, radius)
    
    def find_objects_of_type(self, obj_type: str) -> List[Dict[str, Any]]:
        """查找指定类型的对象"""
        return self.environment.find_objects_by_type(obj_type)
    
    def update_robot(self, robot: Robot, updates: Dict[str, Any]) -> None:
        """更新机器人状态"""
        self.state_updater.update_robot_state(robot.id, updates)
    
    def update_object(self, obj_id: Any, updates: Dict[str, Any]) -> None:
        """更新对象状态"""
        self.state_updater.update_object_state(obj_id, updates)
    
    def notify(self, event_type: str, data: Dict[str, Any]) -> None:
        """通知事件"""
        self.state_updater.notify_event(event_type, data)


class SkillExecutionContext:
    """技能执行上下文管理器"""
    
    def __init__(self, environment: EnvironmentProvider, state_updater: StateUpdater):
        self.environment = environment
        self.state_updater = state_updater
    
    def create_context(self, params: Dict[str, Any], execution_time: float, 
                      logger: Any = None) -> SkillContext:
        """创建技能执行上下文"""
        return SkillContext(
            environment=self.environment,
            state_updater=self.state_updater,
            params=params,
            execution_time=execution_time,
            logger=logger
        ) 