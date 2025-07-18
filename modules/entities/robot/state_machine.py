"""
机器人状态机

管理机器人的状态转换和状态检查逻辑。
"""

from enum import Enum
from typing import Set, Dict, Any


class RobotState(Enum):
    """机器人状态枚举"""
    IDLE = "idle"           # 空闲状态
    BUSY = "busy"           # 忙碌状态（执行技能中）
    MOVING = "moving"       # 移动中
    CHARGING = "charging"   # 充电中
    ERROR = "error"         # 错误状态
    OFFLINE = "offline"     # 离线状态
    
    # 无人机特有状态
    LANDED = "landed"       # 已降落
    FLYING = "flying"       # 飞行中
    TAKEOFF = "takeoff"     # 起飞中
    LANDING = "landing"     # 降落中
    
    # 地面车辆特有状态
    PARKED = "parked"       # 已停放
    DRIVING = "driving"     # 行驶中


class RobotStateMachine:
    """机器人状态机"""
    
    def __init__(self, robot):
        """
        初始化状态机
        
        Args:
            robot: 机器人实例
        """
        self.robot = robot
        self.current_state = RobotState.IDLE
        
        # 定义状态转换规则
        self._transitions = self._build_transitions()
        
        # 定义可执行技能的状态
        self._skill_executable_states = {
            RobotState.IDLE,
            RobotState.PARKED,
            RobotState.LANDED
        }
    
    def _build_transitions(self) -> Dict[RobotState, Set[RobotState]]:
        """构建状态转换规则"""
        transitions = {
            # 通用状态转换
            RobotState.IDLE: {
                RobotState.BUSY, RobotState.MOVING, RobotState.CHARGING, 
                RobotState.ERROR, RobotState.OFFLINE
            },
            RobotState.BUSY: {
                RobotState.IDLE, RobotState.ERROR, RobotState.OFFLINE
            },
            RobotState.MOVING: {
                RobotState.IDLE, RobotState.BUSY, RobotState.ERROR, RobotState.OFFLINE
            },
            RobotState.CHARGING: {
                RobotState.IDLE, RobotState.ERROR, RobotState.OFFLINE
            },
            RobotState.ERROR: {
                RobotState.IDLE, RobotState.OFFLINE
            },
            RobotState.OFFLINE: {
                RobotState.IDLE, RobotState.ERROR
            },
            
            # 无人机特有状态转换
            RobotState.LANDED: {
                RobotState.TAKEOFF, RobotState.ERROR, RobotState.OFFLINE
            },
            RobotState.FLYING: {
                RobotState.LANDING, RobotState.ERROR, RobotState.OFFLINE
            },
            RobotState.TAKEOFF: {
                RobotState.FLYING, RobotState.ERROR, RobotState.OFFLINE
            },
            RobotState.LANDING: {
                RobotState.LANDED, RobotState.ERROR, RobotState.OFFLINE
            },
            
            # 地面车辆特有状态转换
            RobotState.PARKED: {
                RobotState.DRIVING, RobotState.ERROR, RobotState.OFFLINE
            },
            RobotState.DRIVING: {
                RobotState.PARKED, RobotState.ERROR, RobotState.OFFLINE
            }
        }
        return transitions
    
    def can_transition_to(self, target_state: RobotState) -> bool:
        """检查是否可以转换到目标状态"""
        if self.current_state not in self._transitions:
            return False
        return target_state in self._transitions[self.current_state]
    
    def transition_to(self, new_state: RobotState) -> bool:
        """
        转换到新状态
        
        Args:
            new_state: 目标状态
            
        Returns:
            是否转换成功
        """
        if not self.can_transition_to(new_state):
            return False
        
        old_state = self.current_state
        self.current_state = new_state
        
        # 更新机器人的状态
        self.robot.set_state('status', new_state.value)
        
        print(f"机器人 {self.robot.label} 状态转换: {old_state.value} -> {new_state.value}")
        return True
    
    def can_execute_skill(self) -> bool:
        """检查当前状态是否可以执行技能"""
        return self.current_state in self._skill_executable_states
    
    def get_available_transitions(self) -> Set[RobotState]:
        """获取当前可用的状态转换"""
        return self._transitions.get(self.current_state, set())
    
    def is_in_error_state(self) -> bool:
        """检查是否处于错误状态"""
        return self.current_state == RobotState.ERROR
    
    def is_offline(self) -> bool:
        """检查是否离线"""
        return self.current_state == RobotState.OFFLINE
    
    def reset_to_idle(self):
        """重置到空闲状态"""
        self.transition_to(RobotState.IDLE)
    
    def set_error(self, error_message: str = "未知错误"):
        """设置错误状态"""
        self.transition_to(RobotState.ERROR)
        self.robot.set_state('error_message', error_message)
    
    def clear_error(self):
        """清除错误状态"""
        if self.current_state == RobotState.ERROR:
            self.transition_to(RobotState.IDLE)
            self.robot.set_state('error_message', None) 