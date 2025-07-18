from typing import Any, Dict, List, Optional, Callable
import logging


class Goal:
    """
    简化的目标类，直接适配数据集格式
    
    数据集中的goal格式：
    {
        "id": "g1",
        "description": "找到车牌号为 00001 的小轿车",
        "target": {
            "category": "prop",
            "type": "car",
            "license_plate": "00001"
        },
        "success_condition": {
            "field": "status",
            "operator": "EQ",
            "value": "discovered"
        },
        "quantifier": "EXISTS"
    }
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化目标
        
        Args:
            config: 目标配置字典，直接来自数据集
        """
        self.logger = logging.getLogger(f"goal.{config.get('id', 'unknown')}")
        
        # 基础属性
        self.id = config.get("id", "unknown")
        self.description = config.get("description", "")
        self.config = config
        
        # 目标信息
        self.target = config.get("target", {})
        self.success_condition = config.get("success_condition", {})
        self.quantifier = config.get("quantifier", "EXISTS")  # EXISTS, FORALL
        
        # 状态跟踪
        self.is_achieved = False
        self.achievement_time = None
        self.attempts = 0
        
        self.logger.info(f"创建目标: {self.id} - {self.description}")
    
    def evaluate(self, world_state: Dict[str, Any]) -> bool:
        """
        评估目标是否达成
        
        Args:
            world_state: 当前世界状态，包含所有实体信息
            
        Returns:
            bool: 目标是否达成
        """
        self.attempts += 1
        self.logger.debug(f"评估目标 {self.id} (第{self.attempts}次)")
        
        try:
            # 1. 找到目标实体
            target_entities = self._find_target_entities(world_state)
            if not target_entities:
                self.logger.debug(f"目标 {self.id} 未找到目标实体")
                return False
            
            # 2. 检查成功条件
            if self.quantifier == "EXISTS":
                # 存在性目标：至少有一个实体满足条件
                for entity in target_entities:
                    if self._check_success_condition(entity):
                        self._mark_achieved()
                        return True
                return False
                
            elif self.quantifier == "FORALL":
                # 全称目标：所有实体都必须满足条件
                for entity in target_entities:
                    if not self._check_success_condition(entity):
                        return False
                self._mark_achieved()
                return True
                
            else:
                self.logger.warning(f"未知的量词: {self.quantifier}")
                return False
                
        except Exception as e:
            self.logger.error(f"评估目标 {self.id} 时出错: {e}")
            return False
    
    def _find_target_entities(self, world_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """根据target条件找到匹配的实体"""
        entities = world_state.get("entities", [])
        matched_entities = []
        
        for entity in entities:
            if self._matches_target(entity):
                matched_entities.append(entity)
        
        return matched_entities
    
    def _matches_target(self, entity: Dict[str, Any]) -> bool:
        """检查实体是否匹配target条件"""
        entity_props = entity.get("properties", {})
        
        # 检查基本属性
        if self.target.get("category") and entity_props.get("category") != self.target["category"]:
            return False
        
        if self.target.get("type") and entity_props.get("type") != self.target["type"]:
            return False
        
        # 检查其他属性（如license_plate等）
        for key, value in self.target.items():
            if key not in ["category", "type"]:
                if entity_props.get(key) != value:
                    return False
        
        return True
    
    def _check_success_condition(self, entity: Dict[str, Any]) -> bool:
        """检查实体是否满足成功条件"""
        field = self.success_condition.get("field", "")
        operator = self.success_condition.get("operator", "EQ")
        expected_value = self.success_condition.get("value")
        
        # 获取实际值（支持嵌套字段，如"states.loaded"）
        actual_value = self._get_nested_value(entity, field)
        
        # 执行比较
        return self._compare_values(actual_value, operator, expected_value)
    
    def _get_nested_value(self, entity: Dict[str, Any], field_path: str) -> Any:
        """获取嵌套字段的值，如"states.loaded" """
        if "." not in field_path:
            return entity.get(field_path)
        
        parts = field_path.split(".")
        current = entity
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        
        return current
    
    def _compare_values(self, actual: Any, operator: str, expected: Any) -> bool:
        """比较实际值和期望值"""
        op_map = {
            "EQ": lambda a, e: a == e,
            "NEQ": lambda a, e: a != e,
            "GT": lambda a, e: a > e,
            "LT": lambda a, e: a < e,
            "GTE": lambda a, e: a >= e,
            "LTE": lambda a, e: a <= e,
            "IN": lambda a, e: a in e,
            "NOT_IN": lambda a, e: a not in e,
        }
        
        if operator not in op_map:
            self.logger.warning(f"不支持的操作符: {operator}")
            return False
        
        try:
            return op_map[operator](actual, expected)
        except Exception:
            return False
    
    def _mark_achieved(self):
        """标记目标已达成"""
        if not self.is_achieved:
            self.is_achieved = True
            import time
            self.achievement_time = time.time()
            self.logger.info(f"目标 {self.id} 已达成！")
    
    def reset(self):
        """重置目标状态"""
        self.is_achieved = False
        self.achievement_time = None
        self.attempts = 0
    
    def get_status(self) -> Dict[str, Any]:
        """获取目标状态"""
        return {
            "id": self.id,
            "description": self.description,
            "is_achieved": self.is_achieved,
            "attempts": self.attempts,
            "achievement_time": self.achievement_time,
            "target": self.target,
            "success_condition": self.success_condition,
            "quantifier": self.quantifier
        }
    
    def __str__(self) -> str:
        return f"Goal({self.id}: {self.description})"
    
    def __repr__(self) -> str:
        return self.__str__()