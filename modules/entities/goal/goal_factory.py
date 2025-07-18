# 文件: modules/goal/goal_factory.py

from typing import Any, Dict, List, Optional
import logging

from .goal import Goal


class GoalFactory:
    """
    简化的目标工厂类，直接创建Goal实例
    """

    def __init__(self):
        """初始化目标工厂"""
        self.logger = logging.getLogger("goal_factory")
        self._goals: Dict[str, Goal] = {}
    
    def create_goal(self, config: Dict[str, Any]) -> Goal:
        """
        创建目标实例
        
        Args:
            config: 目标配置字典，直接来自数据集
            
        Returns:
            Goal: 目标实例
            
        Raises:
            ValueError: 配置无效时抛出
        """
        try:
            # 验证配置
            self._validate_config(config)
            
            # 创建目标
            goal = Goal(config)
            
            # 注册目标
            self._goals[goal.id] = goal
            
            self.logger.info(f"创建目标: {goal.id}")
            return goal
            
        except Exception as e:
            self.logger.error(f"创建目标失败: {e}")
            raise ValueError(f"创建目标失败: {e}")
    
    def _validate_config(self, config: Dict[str, Any]):
        """验证目标配置"""
        required_fields = ["id", "description", "target", "success_condition"]
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"目标配置缺少必需字段: {field}")
        
        # 验证target
        target = config.get("target", {})
        if not isinstance(target, dict):
            raise ValueError("target必须是字典")
        
        # 验证success_condition
        success_condition = config.get("success_condition", {})
        if not isinstance(success_condition, dict):
            raise ValueError("success_condition必须是字典")
        
        required_condition_fields = ["field", "operator", "value"]
        for field in required_condition_fields:
            if field not in success_condition:
                raise ValueError(f"success_condition缺少必需字段: {field}")
    
    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """获取目标实例"""
        return self._goals.get(goal_id)
    
    def get_all_goals(self) -> List[Goal]:
        """获取所有目标"""
        return list(self._goals.values())
    
    def get_achieved_goals(self) -> List[Goal]:
        """获取已达成的目标"""
        return [goal for goal in self._goals.values() if goal.is_achieved]
    
    def get_pending_goals(self) -> List[Goal]:
        """获取待达成的目标"""
        return [goal for goal in self._goals.values() if not goal.is_achieved]
    
    def evaluate_all_goals(self, world_state: Dict[str, Any]) -> Dict[str, bool]:
        """评估所有目标"""
        results = {}
        for goal_id, goal in self._goals.items():
            results[goal_id] = goal.evaluate(world_state)
        return results
    
    def reset_all_goals(self):
        """重置所有目标"""
        for goal in self._goals.values():
            goal.reset()
        self.logger.info("所有目标已重置")
    
    def remove_goal(self, goal_id: str) -> bool:
        """移除目标"""
        if goal_id in self._goals:
            del self._goals[goal_id]
            self.logger.info(f"移除目标: {goal_id}")
            return True
        return False
    
    def clear_all_goals(self):
        """清空所有目标"""
        self._goals.clear()
        self.logger.info("所有目标已清空")
    
    def get_goal_statistics(self) -> Dict[str, Any]:
        """获取目标统计信息"""
        total = len(self._goals)
        achieved = len(self.get_achieved_goals())
        pending = len(self.get_pending_goals())
        
        return {
            "total_goals": total,
            "achieved_goals": achieved,
            "pending_goals": pending,
            "achievement_rate": achieved / total if total > 0 else 0.0
        }
    
    def __str__(self) -> str:
        stats = self.get_goal_statistics()
        return f"GoalFactory(total={stats['total_goals']}, achieved={stats['achieved_goals']})"
    
    def __repr__(self) -> str:
        return self.__str__()