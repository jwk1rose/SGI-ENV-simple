"""
集成现有机器人系统的RobotManager

使用modules/entity/robot/中的完整机器人实现，
而不是重新创建简化的TemplateRobot。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field

from modules.entity.robot.robot import Robot
from modules.entity.robot.drone import Drone
from modules.entity.robot.ground_vehicle import GroundVehicle
from modules.entity.robot.robot_factory import RobotFactory
from modules.entity.robot.capabilities import Capability
from modules.entity.skill.skill_factory import SkillFactory
from modules.scenario_builder.entity_library import EntityTemplateLibrary
from modules.utils.global_config import GlobalConfig, RobotStatus, EntityType, EntityCategory

logger = logging.getLogger(__name__)


class IntegratedRobotManager:
    """集成现有机器人系统的管理器"""
    
    def __init__(self, task_context):
        """
        初始化机器人管理器
        
        Args:
            task_context: 任务上下文，用于同步机器人状态
        """
        self.task_context = task_context
        self.template_library = EntityTemplateLibrary()
        self.robots: Dict[Any, Robot] = {}
        
        # 状态同步回调
        self.state_sync_callbacks: List[Callable[[Any, Dict[str, Any]], None]] = []
    
    def add_state_sync_callback(self, callback: Callable[[Any, Dict[str, Any]], None]):
        """添加状态同步回调"""
        self.state_sync_callbacks.append(callback)
    
    async def initialize_from_config(self, config: Dict[str, Any]):
        """从配置初始化机器人"""
        environment = config.get('environment', {})
        scene_config = environment.get('scene_config', {})
        nodes = scene_config.get('nodes', [])
        
        for node in nodes:
            properties = node.get('properties', {})
            if properties.get('category') == EntityCategory.ROBOT.value:
                robot_id = node.get('id')
                robot_type = properties.get('type', 'unknown')
                robot_label = properties.get('label', str(robot_id))
                
                # 验证机器人类型
                if not GlobalConfig.validate_entity_type(robot_type):
                    logger.warning(f"无效的机器人类型: {robot_type}")
                    continue
                
                # 创建集成机器人
                robot = await self._create_integrated_robot(robot_id, robot_type, robot_label, properties, node)
                if robot:
                    self.robots[robot_id] = robot
                    logger.info(f"初始化集成机器人: {robot_label} ({robot_type})")
    
    async def _create_integrated_robot(self, robot_id: Any, robot_type: str, robot_label: str, 
                                     properties: Dict[str, Any], node: Dict[str, Any]) -> Optional[Robot]:
        """创建集成的机器人"""
        try:
            # 获取机器人模板
            try:
                robot_template = self.template_library.get_template("robot", robot_type)
            except KeyError:
                logger.warning(f"未找到机器人模板: {robot_type}")
                return None
            
            # 提取位置信息
            position = self._extract_position_from_node(node)
            
            # 获取模板中的默认状态
            template_status = robot_template.get('status', RobotStatus.IDLE.value)
            
            # 准备机器人配置
            robot_config = {
                'id': robot_id,
                'type': robot_type,
                'label': robot_label,
                'initial_state': {
                    'position': position,
                    'battery': 100.0,
                    'status': template_status
                }
            }
            
            # 使用RobotFactory创建机器人
            robot = RobotFactory.create_robot(robot_config)
            
            # 为机器人添加技能
            skills_list = robot_template.get('skills', [])
            for skill_name in skills_list:
                try:
                    # 验证技能名称
                    if not GlobalConfig.validate_skill_name(skill_name):
                        logger.warning(f"无效的技能名称: {skill_name}")
                        continue
                        
                    skill_instance = SkillFactory.create_skill(skill_name)
                    robot.add_skill(skill_name, skill_instance)
                    logger.debug(f"为机器人 {robot_label} 添加技能: {skill_name}")
                except Exception as e:
                    logger.warning(f"为机器人 {robot_label} 添加技能 {skill_name} 失败: {e}")
            
            return robot
            
        except Exception as e:
            logger.error(f"创建集成机器人失败: {e}")
            return None
    
    def _extract_position_from_node(self, node: Dict[str, Any]) -> Dict[str, float]:
        """从节点配置中提取位置信息"""
        shape = node.get("shape", {})
        if shape.get("type") == "rectangle":
            min_corner = shape.get("min_corner", [0, 0])
            max_corner = shape.get("max_corner", [0, 0])
            return {
                "x": (min_corner[0] + max_corner[0]) / 2,
                "y": (min_corner[1] + max_corner[1]) / 2
            }
        
        return {"x": 0, "y": 0}
    
    def get_robot(self, robot_id: Any) -> Optional[Robot]:
        """获取机器人"""
        return self.robots.get(robot_id)
    
    def get_all_robots(self) -> Dict[Any, Robot]:
        """获取所有机器人"""
        return self.robots.copy()
    
    async def update_robot_state(self, robot_id: Any, updates: Dict[str, Any]):
        """更新机器人状态"""
        robot = self.robots.get(robot_id)
        if not robot:
            return
        
        # 验证状态更新
        if 'status' in updates:
            status = updates['status']
            if not GlobalConfig.validate_robot_status(status):
                logger.warning(f"无效的机器人状态: {status}")
                return
        
        # 更新机器人状态
        if 'position' in updates:
            robot.set_state('position', updates['position'])
        if 'battery' in updates:
            robot.set_state('battery', updates['battery'])
        if 'status' in updates:
            robot.set_state('status', updates['status'])
        
        # 同步到TaskContext
        self.task_context.update_object_properties(robot_id, updates)
        
        # 触发状态同步回调
        for callback in self.state_sync_callbacks:
            try:
                callback(robot_id, updates)
            except Exception as e:
                logger.error(f"状态同步回调执行错误: {e}")
    
    async def add_skill_to_robot(self, robot_id: Any, skill_id: str):
        """为机器人添加技能（标记为正在执行）"""
        robot = self.robots.get(robot_id)
        if not robot:
            return
        
        # 设置机器人状态为忙碌
        robot.set_state('status', RobotStatus.BUSY.value)
        
        await self.update_robot_state(robot_id, {
            'status': RobotStatus.BUSY.value
        })
    
    async def remove_skill_from_robot(self, robot_id: Any, skill_id: str):
        """从机器人移除技能（标记为完成）"""
        robot = self.robots.get(robot_id)
        if not robot:
            return
        
        # 设置机器人状态为空闲
        robot.set_state('status', RobotStatus.IDLE.value)
        
        await self.update_robot_state(robot_id, {
            'status': RobotStatus.IDLE.value
        })
    
    async def get_robot_status(self, robot_id: Any) -> Optional[Dict[str, Any]]:
        """获取机器人状态"""
        robot = self.robots.get(robot_id)
        if not robot:
            return None
        
        return {
            'entity_id': robot.id,
            'robot_type': robot.__class__.__name__,
            'label': robot.label,
            'position': robot.get_state('position'),
            'battery': robot.get_state('battery'),
            'status': robot.get_state('status'),
            'capabilities': [cap.name for cap in robot.get_capabilities()],
            'skills': list(robot.skills.keys())
        }
    
    def reset_all_robots(self):
        """重置所有机器人状态"""
        for robot in self.robots.values():
            robot.set_state('battery', 100.0)
            robot.set_state('status', RobotStatus.IDLE.value)
            robot.set_state('position', {'x': 0, 'y': 0})
        
        logger.info("所有集成机器人状态已重置")
    
    def handle_task_context_event(self, event: Dict[str, Any]):
        """处理TaskContext事件"""
        event_type = event.get("type")
        
        if event_type == "OBJECT_ADDED":
            self._handle_object_added(event)
        elif event_type == "OBJECT_UPDATED":
            self._handle_object_updated(event)
        elif event_type == "OBJECT_REMOVED":
            self._handle_object_removed(event)
    
    def _handle_object_added(self, event: Dict[str, Any]):
        """处理对象添加事件"""
        object_id = event.get("object_id")
        data = event.get("data", {})
        
        properties = data.get("properties", {})
        if properties.get("category") == EntityCategory.ROBOT.value:
            logger.info(f"检测到新机器人: {object_id}")
    
    def _handle_object_updated(self, event: Dict[str, Any]):
        """处理对象更新事件"""
        object_id = event.get("object_id")
        data = event.get("data", {})
        
        # 如果是机器人，同步状态
        if object_id in self.robots:
            robot = self.robots[object_id]
            if 'position' in data:
                robot.set_state('position', data['position'])
            if 'battery' in data:
                robot.set_state('battery', data['battery'])
            if 'status' in data:
                # 验证状态
                status = data['status']
                if GlobalConfig.validate_robot_status(status):
                    robot.set_state('status', status)
                else:
                    logger.warning(f"收到无效的机器人状态: {status}")
    
    def _handle_object_removed(self, event: Dict[str, Any]):
        """处理对象移除事件"""
        object_id = event.get("object_id")
        if object_id in self.robots:
            del self.robots[object_id]
            logger.info(f"机器人已移除: {object_id}")


# 导出类
RobotManager = IntegratedRobotManager 