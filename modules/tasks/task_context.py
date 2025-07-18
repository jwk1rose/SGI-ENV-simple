import json
import logging
import asyncio
import uuid
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from modules.entities.goal import Goal, GoalFactory
from modules.entities.base.entity import Entity
from modules.entities.prop.prop import Prop
from modules.entities.robot.robot import Robot
from modules.events.event_bus import (
    get_global_event_bus, publish_event, subscribe_event, unsubscribe_event,
    Event, TaskEvent, ConfigEvent, GoalEvent, SystemEvent, EventType,
    SceneEntityEvent, SceneBatchEvent
)

class AsyncTaskContext:
    """异步任务上下文类
    
    提供异步接口来管理任务配置、场景实体和事件通知。
    支持对building、prop、robot等实体的异步操作。
    
    Attributes:
        task_config: 任务配置字典
        scenario_data: 场景数据
        is_feasible: 任务可行性标志
        _entities: 实体缓存字典
        _event_subscriptions: 事件订阅ID列表
        _operation_lock: 操作锁，确保并发安全
        _change_history: 变更历史记录
    """
    
    def __init__(self, 
                 task_config: Dict[str, Any] = None,
                 scenario_data: Optional[Dict[str, Any]] = None):
        """初始化异步任务上下文
        
        Args:
            task_config: 任务配置字典
            scenario_data: 场景数据字典
        """
        self.task_config: Dict[str, Any] = task_config or {}
        self.scenario_data: Optional[Dict[str, Any]] = scenario_data
        self.is_feasible: Optional[bool] = None
        
        # 实体管理
        self._entities: Dict[str, Entity] = {}
        self._buildings: Dict[str, Dict[str, Any]] = {}
        self._props: Dict[str, Prop] = {}
        self._robots: Dict[str, Robot] = {}
        
        # 事件系统
        self._event_subscriptions: List[str] = []
        self._subscribers: List[Callable] = []
        
        # 并发控制
        self._operation_lock = asyncio.Lock()
        self._batch_operations: Dict[str, List[Dict[str, Any]]] = {}
        
        # 变更历史
        self._change_history: List[Dict[str, Any]] = []
        self._max_history_size = 1000
        
        # 日志
        self.logger = logging.getLogger(f"async_task_context.{self.get_id()}")
        
        # 初始化
        asyncio.create_task(self._initialize_async())
    
    async def _initialize_async(self) -> None:
        """异步初始化"""
        try:
            if self.scenario_data:
                await self._merge_scenario_data_async()
            
            await self._setup_event_subscriptions_async()
            await self._load_entities_async()
            
            self.logger.info("异步任务上下文初始化完成")
        except Exception as e:
            self.logger.error(f"异步初始化失败: {e}")
    
    async def _merge_scenario_data_async(self) -> None:
        """异步合并场景数据"""
        if not self.scenario_data:
            return
        
        async with self._operation_lock:
            # 确保环境配置存在
            if "environment" not in self.task_config:
                self.task_config["environment"] = {}
            
            # 合并场景配置
            if "scene_config" in self.scenario_data:
                self.task_config["environment"]["scene_config"] = self.scenario_data["scene_config"]
            
            if "gridmap_config" in self.scenario_data:
                self.task_config["environment"]["gridmap_config"] = self.scenario_data["gridmap_config"]
            
            # 发布配置更新事件
            await self._publish_config_event_async("scenario_merged", None, self.scenario_data)
            
            self.logger.info("场景数据异步合并完成")
    
    async def _setup_event_subscriptions_async(self) -> None:
        """异步设置事件订阅"""
        try:
            # 订阅系统事件
            subscription_id = subscribe_event(
                EventType.SYSTEM.value,
                self._handle_system_event_async,
                f"async_task_context_{self.get_id()}"
            )
            self._event_subscriptions.append(subscription_id)
            
            # 订阅配置事件
            subscription_id = subscribe_event(
                EventType.CONFIG.value,
                self._handle_config_event_async,
                f"async_task_context_{self.get_id()}"
            )
            self._event_subscriptions.append(subscription_id)
            
            self.logger.debug("异步事件订阅设置完成")
        except Exception as e:
            self.logger.error(f"设置异步事件订阅失败: {e}")
    
    async def _load_entities_async(self) -> None:
        """异步加载实体"""
        try:
            env_config = self.get_environment_config()
            if not env_config:
                return
            
            # 加载建筑物
            buildings = env_config.get("buildings", [])
            for building_data in buildings:
                await self._load_building_async(building_data)
            
            # 加载道具
            props = env_config.get("props", [])
            for prop_data in props:
                await self._load_prop_async(prop_data)
            
            # 加载机器人
            robots = env_config.get("robots", [])
            for robot_data in robots:
                await self._load_robot_async(robot_data)
            
            self.logger.info(f"异步加载实体完成: {len(self._entities)} 个实体")
        except Exception as e:
            self.logger.error(f"异步加载实体失败: {e}")
    
    # ==================== 建筑物管理 ====================
    
    async def add_building_async(self, 
                                building_data: Dict[str, Any],
                                validate: bool = True) -> Tuple[bool, str]:
        """异步添加建筑物
        
        Args:
            building_data: 建筑物数据字典
            validate: 是否验证数据
            
        Returns:
            (成功标志, 消息)
        """
        async with self._operation_lock:
            try:
                building_id = building_data.get("id")
                if not building_id:
                    return False, "建筑物ID不能为空"
                
                if building_id in self._buildings:
                    return False, f"建筑物ID {building_id} 已存在"
                
                # 验证数据
                if validate and not await self._validate_building_data_async(building_data):
                    return False, "建筑物数据验证失败"
                
                # 添加建筑物
                self._buildings[building_id] = building_data.copy()
                
                # 记录变更历史
                await self._record_change_async({
                    "type": "building_added",
                    "entity_id": building_id,
                    "data": building_data,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发布事件
                await self._publish_scene_entity_event_async(
                    entity_id=building_id,
                    entity_type="building",
                    entity_label=building_data.get("label", "Unknown Building"),
                    action="added",
                    new_data=building_data,
                    position=building_data.get("position")
                )
                
                self.logger.info(f"建筑物 {building_id} 添加成功")
                return True, f"建筑物 {building_id} 添加成功"
                
            except Exception as e:
                self.logger.error(f"添加建筑物失败: {e}")
                return False, f"添加建筑物失败: {str(e)}"
    
    async def update_building_async(self, 
                                   building_id: str,
                                   updates: Dict[str, Any],
                                   merge: bool = True) -> Tuple[bool, str]:
        """异步更新建筑物
        
        Args:
            building_id: 建筑物ID
            updates: 更新数据
            merge: 是否合并更新（True）还是完全替换（False）
            
        Returns:
            (成功标志, 消息)
        """
        async with self._operation_lock:
            try:
                if building_id not in self._buildings:
                    return False, f"建筑物 {building_id} 不存在"
                
                old_data = self._buildings[building_id].copy()
                
                if merge:
                    self._buildings[building_id].update(updates)
                    new_data = self._buildings[building_id]
                else:
                    self._buildings[building_id] = updates.copy()
                    new_data = updates
                
                # 记录变更历史
                await self._record_change_async({
                    "type": "building_updated",
                    "entity_id": building_id,
                    "old_data": old_data,
                    "new_data": new_data,
                    "updates": updates,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发布事件
                await self._publish_scene_entity_event_async(
                    entity_id=building_id,
                    entity_type="building",
                    entity_label=new_data.get("label", "Unknown Building"),
                    action="updated",
                    old_data=old_data,
                    new_data=new_data,
                    position=new_data.get("position")
                )
                
                self.logger.info(f"建筑物 {building_id} 更新成功")
                return True, f"建筑物 {building_id} 更新成功"
                
            except Exception as e:
                self.logger.error(f"更新建筑物失败: {e}")
                return False, f"更新建筑物失败: {str(e)}"
    
    async def remove_building_async(self, building_id: str) -> Tuple[bool, str]:
        """异步移除建筑物
        
        Args:
            building_id: 建筑物ID
            
        Returns:
            (成功标志, 消息)
        """
        async with self._operation_lock:
            try:
                if building_id not in self._buildings:
                    return False, f"建筑物 {building_id} 不存在"
                
                old_data = self._buildings.pop(building_id)
                
                # 记录变更历史
                await self._record_change_async({
                    "type": "building_removed",
                    "entity_id": building_id,
                    "old_data": old_data,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发布事件
                await self._publish_scene_entity_event_async(
                    entity_id=building_id,
                    entity_type="building",
                    entity_label=old_data.get("label", "Unknown Building"),
                    action="removed",
                    old_data=old_data,
                    position=old_data.get("position")
                )
                
                self.logger.info(f"建筑物 {building_id} 移除成功")
                return True, f"建筑物 {building_id} 移除成功"
                
            except Exception as e:
                self.logger.error(f"移除建筑物失败: {e}")
                return False, f"移除建筑物失败: {str(e)}"
    
    # ==================== 道具管理 ====================
    
    async def add_prop_async(self, 
                            prop_data: Dict[str, Any],
                            validate: bool = True) -> Tuple[bool, str]:
        """异步添加道具
        
        Args:
            prop_data: 道具数据字典
            validate: 是否验证数据
            
        Returns:
            (成功标志, 消息)
        """
        async with self._operation_lock:
            try:
                prop_id = prop_data.get("id")
                if not prop_id:
                    return False, "道具ID不能为空"
                
                if prop_id in self._props:
                    return False, f"道具ID {prop_id} 已存在"
                
                # 验证数据
                if validate and not await self._validate_prop_data_async(prop_data):
                    return False, "道具数据验证失败"
                
                # 创建道具实例
                prop = await self._create_prop_instance_async(prop_data)
                self._props[prop_id] = prop
                self._entities[prop_id] = prop
                
                # 记录变更历史
                await self._record_change_async({
                    "type": "prop_added",
                    "entity_id": prop_id,
                    "data": prop_data,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发布事件
                await self._publish_scene_entity_event_async(
                    entity_id=prop_id,
                    entity_type="prop",
                    entity_label=prop_data.get("label", "Unknown Prop"),
                    action="added",
                    new_data=prop_data,
                    position=prop_data.get("position")
                )
                
                self.logger.info(f"道具 {prop_id} 添加成功")
                return True, f"道具 {prop_id} 添加成功"
                
            except Exception as e:
                self.logger.error(f"添加道具失败: {e}")
                return False, f"添加道具失败: {str(e)}"
    
    async def update_prop_state_async(self, 
                                     prop_id: str,
                                     state_updates: Dict[str, Any]) -> Tuple[bool, str]:
        """异步更新道具状态
        
        Args:
            prop_id: 道具ID
            state_updates: 状态更新字典
            
        Returns:
            (成功标志, 消息)
        """
        async with self._operation_lock:
            try:
                if prop_id not in self._props:
                    return False, f"道具 {prop_id} 不存在"
                
                prop = self._props[prop_id]
                old_state = prop.state.copy()
                
                # 更新状态
                for key, value in state_updates.items():
                    prop.set_state(key, value)
                
                new_state = prop.state.copy()
                
                # 记录变更历史
                await self._record_change_async({
                    "type": "prop_state_updated",
                    "entity_id": prop_id,
                    "old_state": old_state,
                    "new_state": new_state,
                    "updates": state_updates,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发布事件
                await self._publish_scene_entity_event_async(
                    entity_id=prop_id,
                    entity_type="prop",
                    entity_label=prop.label,
                    action="state_changed",
                    old_data={"state": old_state},
                    new_data={"state": new_state},
                    position=prop.get_state("position")
                )
                
                self.logger.info(f"道具 {prop_id} 状态更新成功")
                return True, f"道具 {prop_id} 状态更新成功"
                
            except Exception as e:
                self.logger.error(f"更新道具状态失败: {e}")
                return False, f"更新道具状态失败: {str(e)}"
    
    # ==================== 机器人管理 ====================
    
    async def add_robot_async(self, 
                             robot_data: Dict[str, Any],
                             validate: bool = True) -> Tuple[bool, str]:
        """异步添加机器人
        
        Args:
            robot_data: 机器人数据字典
            validate: 是否验证数据
            
        Returns:
            (成功标志, 消息)
        """
        async with self._operation_lock:
            try:
                robot_id = robot_data.get("id")
                if not robot_id:
                    return False, "机器人ID不能为空"
                
                if robot_id in self._robots:
                    return False, f"机器人ID {robot_id} 已存在"
                
                # 验证数据
                if validate and not await self._validate_robot_data_async(robot_data):
                    return False, "机器人数据验证失败"
                
                # 创建机器人实例
                robot = await self._create_robot_instance_async(robot_data)
                self._robots[robot_id] = robot
                self._entities[robot_id] = robot
                
                # 记录变更历史
                await self._record_change_async({
                    "type": "robot_added",
                    "entity_id": robot_id,
                    "data": robot_data,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发布事件
                await self._publish_scene_entity_event_async(
                    entity_id=robot_id,
                    entity_type="robot",
                    entity_label=robot_data.get("label", "Unknown Robot"),
                    action="added",
                    new_data=robot_data,
                    position=robot_data.get("position")
                )
                
                self.logger.info(f"机器人 {robot_id} 添加成功")
                return True, f"机器人 {robot_id} 添加成功"
                
            except Exception as e:
                self.logger.error(f"添加机器人失败: {e}")
                return False, f"添加机器人失败: {str(e)}"
    
    async def update_robot_async(self, 
                                robot_id: str,
                                updates: Dict[str, Any],
                                merge: bool = True) -> Tuple[bool, str]:
        """异步更新机器人
        
        Args:
            robot_id: 机器人ID
            updates: 更新数据
            merge: 是否合并更新
            
        Returns:
            (成功标志, 消息)
        """
        async with self._operation_lock:
            try:
                if robot_id not in self._robots:
                    return False, f"机器人 {robot_id} 不存在"
                
                robot = self._robots[robot_id]
                old_data = robot.to_dict() if hasattr(robot, 'to_dict') else robot.__dict__.copy()
                
                # 更新机器人属性
                for key, value in updates.items():
                    if hasattr(robot, key):
                        setattr(robot, key, value)
                    elif hasattr(robot, 'set_state'):
                        robot.set_state(key, value)
                
                new_data = robot.to_dict() if hasattr(robot, 'to_dict') else robot.__dict__.copy()
                
                # 记录变更历史
                await self._record_change_async({
                    "type": "robot_updated",
                    "entity_id": robot_id,
                    "old_data": old_data,
                    "new_data": new_data,
                    "updates": updates,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发布事件
                await self._publish_scene_entity_event_async(
                    entity_id=robot_id,
                    entity_type="robot",
                    entity_label=robot.label,
                    action="updated",
                    old_data=old_data,
                    new_data=new_data,
                    position=robot.get_state("position") if hasattr(robot, 'get_state') else None
                )
                
                self.logger.info(f"机器人 {robot_id} 更新成功")
                return True, f"机器人 {robot_id} 更新成功"
                
            except Exception as e:
                self.logger.error(f"更新机器人失败: {e}")
                return False, f"更新机器人失败: {str(e)}"
    
    async def remove_robot_async(self, robot_id: str) -> Tuple[bool, str]:
        """异步移除机器人
        
        Args:
            robot_id: 机器人ID
            
        Returns:
            (成功标志, 消息)
        """
        async with self._operation_lock:
            try:
                if robot_id not in self._robots:
                    return False, f"机器人 {robot_id} 不存在"
                
                robot = self._robots.pop(robot_id)
                if robot_id in self._entities:
                    self._entities.pop(robot_id)
                
                old_data = robot.to_dict() if hasattr(robot, 'to_dict') else robot.__dict__.copy()
                
                # 记录变更历史
                await self._record_change_async({
                    "type": "robot_removed",
                    "entity_id": robot_id,
                    "old_data": old_data,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发布事件
                await self._publish_scene_entity_event_async(
                    entity_id=robot_id,
                    entity_type="robot",
                    entity_label=robot.label,
                    action="removed",
                    old_data=old_data,
                    position=robot.get_state("position") if hasattr(robot, 'get_state') else None
                )
                
                self.logger.info(f"机器人 {robot_id} 移除成功")
                return True, f"机器人 {robot_id} 移除成功"
                
            except Exception as e:
                self.logger.error(f"移除机器人失败: {e}")
                return False, f"移除机器人失败: {str(e)}"
    
    async def move_robot_async(self, 
                              robot_id: str,
                              new_position: Dict[str, float]) -> Tuple[bool, str]:
        """异步移动机器人
        
        Args:
            robot_id: 机器人ID
            new_position: 新位置 {"x": float, "y": float, "z": float}
            
        Returns:
            (成功标志, 消息)
        """
        async with self._operation_lock:
            try:
                if robot_id not in self._robots:
                    return False, f"机器人 {robot_id} 不存在"
                
                robot = self._robots[robot_id]
                old_position = robot.get_state("position", {})
                
                # 更新位置
                robot.set_state("position", new_position)
                
                # 记录变更历史
                await self._record_change_async({
                    "type": "robot_moved",
                    "entity_id": robot_id,
                    "old_position": old_position,
                    "new_position": new_position,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发布事件
                await self._publish_scene_entity_event_async(
                    entity_id=robot_id,
                    entity_type="robot",
                    entity_label=robot.label,
                    action="moved",
                    old_data={"position": old_position},
                    new_data={"position": new_position},
                    position=new_position
                )
                
                self.logger.info(f"机器人 {robot_id} 移动成功")
                return True, f"机器人 {robot_id} 移动成功"
                
            except Exception as e:
                self.logger.error(f"移动机器人失败: {e}")
                return False, f"移动机器人失败: {str(e)}"
    
    # ==================== 目标管理 ====================
    
    async def add_goal_async(self, 
                            goal_data: Dict[str, Any],
                            validate: bool = True) -> Tuple[bool, str]:
        """异步添加目标
        
        Args:
            goal_data: 目标数据字典
            validate: 是否验证数据
            
        Returns:
            (成功标志, 消息)
        """
        async with self._operation_lock:
            try:
                goal_id = goal_data.get("id")
                if not goal_id:
                    return False, "目标ID不能为空"
                
                # 验证数据
                if validate and not await self._validate_goal_data_async(goal_data):
                    return False, "目标数据验证失败"
                
                # 更新任务配置中的目标
                self.task_config["goal"] = goal_data
                
                # 记录变更历史
                await self._record_change_async({
                    "type": "goal_added",
                    "entity_id": goal_id,
                    "data": goal_data,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发布事件
                await self._publish_scene_entity_event_async(
                    entity_id=goal_id,
                    entity_type="goal",
                    entity_label=goal_data.get("label", "Unknown Goal"),
                    action="added",
                    new_data=goal_data
                )
                
                self.logger.info(f"目标 {goal_id} 添加成功")
                return True, f"目标 {goal_id} 添加成功"
                
            except Exception as e:
                self.logger.error(f"添加目标失败: {e}")
                return False, f"添加目标失败: {str(e)}"
    
    async def update_goal_async(self, 
                               goal_id: str,
                               updates: Dict[str, Any],
                               merge: bool = True) -> Tuple[bool, str]:
        """异步更新目标
        
        Args:
            goal_id: 目标ID
            updates: 更新数据
            merge: 是否合并更新
            
        Returns:
            (成功标志, 消息)
        """
        async with self._operation_lock:
            try:
                current_goal = self.task_config.get("goal")
                if not current_goal or current_goal.get("id") != goal_id:
                    return False, f"目标 {goal_id} 不存在"
                
                old_data = current_goal.copy()
                
                if merge:
                    current_goal.update(updates)
                    new_data = current_goal
                else:
                    self.task_config["goal"] = updates.copy()
                    new_data = updates
                
                # 记录变更历史
                await self._record_change_async({
                    "type": "goal_updated",
                    "entity_id": goal_id,
                    "old_data": old_data,
                    "new_data": new_data,
                    "updates": updates,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发布事件
                await self._publish_scene_entity_event_async(
                    entity_id=goal_id,
                    entity_type="goal",
                    entity_label=new_data.get("label", "Unknown Goal"),
                    action="updated",
                    old_data=old_data,
                    new_data=new_data
                )
                
                self.logger.info(f"目标 {goal_id} 更新成功")
                return True, f"目标 {goal_id} 更新成功"
                
            except Exception as e:
                self.logger.error(f"更新目标失败: {e}")
                return False, f"更新目标失败: {str(e)}"
    
    async def remove_goal_async(self, goal_id: str) -> Tuple[bool, str]:
        """异步移除目标
        
        Args:
            goal_id: 目标ID
            
        Returns:
            (成功标志, 消息)
        """
        async with self._operation_lock:
            try:
                current_goal = self.task_config.get("goal")
                if not current_goal or current_goal.get("id") != goal_id:
                    return False, f"目标 {goal_id} 不存在"
                
                old_data = self.task_config.pop("goal")
                
                # 记录变更历史
                await self._record_change_async({
                    "type": "goal_removed",
                    "entity_id": goal_id,
                    "old_data": old_data,
                    "timestamp": datetime.now().isoformat()
                })
                
                # 发布事件
                await self._publish_scene_entity_event_async(
                    entity_id=goal_id,
                    entity_type="goal",
                    entity_label=old_data.get("label", "Unknown Goal"),
                    action="removed",
                    old_data=old_data
                )
                
                self.logger.info(f"目标 {goal_id} 移除成功")
                return True, f"目标 {goal_id} 移除成功"
                
            except Exception as e:
                self.logger.error(f"移除目标失败: {e}")
                return False, f"移除目标失败: {str(e)}"
    
    # ==================== 批量操作 ====================
    
    async def batch_add_entities_async(self, 
                                      entities: List[Dict[str, Any]],
                                      validate: bool = True) -> Dict[str, Any]:
        """异步批量添加实体
        
        Args:
            entities: 实体数据列表，每个包含type和data字段
            validate: 是否验证数据
            
        Returns:
            批量操作结果字典
        """
        batch_id = str(uuid.uuid4())
        results = {
            "batch_id": batch_id,
            "total_count": len(entities),
            "success_count": 0,
            "failed_count": 0,
            "results": [],
            "errors": []
        }
        
        entity_changes = []
        
        async with self._operation_lock:
            try:
                for i, entity_data in enumerate(entities):
                    entity_type = entity_data.get("type")
                    data = entity_data.get("data", {})
                    entity_id = data.get("id", f"entity_{i}")
                    
                    try:
                        if entity_type == "building":
                            success, message = await self.add_building_async(data, validate)
                        elif entity_type == "prop":
                            success, message = await self.add_prop_async(data, validate)
                        elif entity_type == "robot":
                            success, message = await self.add_robot_async(data, validate)
                        else:
                            success, message = False, f"未知实体类型: {entity_type}"
                        
                        if success:
                            results["success_count"] += 1
                            entity_changes.append({
                                "entity_id": entity_id,
                                "entity_type": entity_type,
                                "action": "added",
                                "success": True
                            })
                        else:
                            results["failed_count"] += 1
                            results["errors"].append({
                                "entity_id": entity_id,
                                "entity_type": entity_type,
                                "error": message
                            })
                        
                        results["results"].append({
                            "entity_id": entity_id,
                            "entity_type": entity_type,
                            "success": success,
                            "message": message
                        })
                        
                    except Exception as e:
                        results["failed_count"] += 1
                        error_msg = f"处理实体 {entity_id} 时出错: {str(e)}"
                        results["errors"].append({
                            "entity_id": entity_id,
                            "entity_type": entity_type,
                            "error": error_msg
                        })
                        results["results"].append({
                            "entity_id": entity_id,
                            "entity_type": entity_type,
                            "success": False,
                            "message": error_msg
                        })
                
                # 发布批量事件
                await self._publish_scene_batch_event_async(
                    batch_id=batch_id,
                    operation_type="batch_add",
                    entities_count=len(entities),
                    entity_changes=entity_changes,
                    validation_results=results
                )
                
                self.logger.info(f"批量添加实体完成: {results['success_count']}/{results['total_count']} 成功")
                
            except Exception as e:
                self.logger.error(f"批量添加实体失败: {e}")
                results["errors"].append({"batch_error": str(e)})
        
        return results
    
    # ==================== 事件发布辅助方法 ====================
    
    async def _publish_scene_entity_event_async(self, 
                                               entity_id: str,
                                               entity_type: str,
                                               entity_label: str,
                                               action: str,
                                               old_data: Dict[str, Any] = None,
                                               new_data: Dict[str, Any] = None,
                                               position: Dict[str, float] = None,
                                               affected_entities: List[str] = None) -> None:
        """发布场景实体事件
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            entity_label: 实体标签
            action: 动作类型
            old_data: 旧数据
            new_data: 新数据
            position: 位置信息
            affected_entities: 受影响的实体列表
        """
        try:
            event = SceneEntityEvent(
                entity_id=entity_id,
                entity_type=entity_type,
                entity_label=entity_label,
                action=action,
                old_data=old_data or {},
                new_data=new_data or {},
                position=position,
                affected_entities=affected_entities or [],
                source=f"async_task_context_{self.get_id()}",
                data={
                    "task_id": self.get_id(),
                    "timestamp": datetime.now().isoformat(),
                    "context_type": "scene_modification"
                }
            )
            await publish_event(event)
        except Exception as e:
            self.logger.error(f"发布场景实体事件失败: {e}")
    
    async def _publish_scene_batch_event_async(self, 
                                              batch_id: str,
                                              operation_type: str,
                                              entities_count: int,
                                              entity_changes: List[Dict[str, Any]],
                                              validation_results: Dict[str, Any]) -> None:
        """发布场景批量事件
        
        Args:
            batch_id: 批量操作ID
            operation_type: 操作类型
            entities_count: 实体数量
            entity_changes: 实体变更列表
            validation_results: 验证结果
        """
        try:
            event = SceneBatchEvent(
                batch_id=batch_id,
                operation_type=operation_type,
                entities_count=entities_count,
                entity_changes=entity_changes,
                validation_results=validation_results,
                source=f"async_task_context_{self.get_id()}",
                data={
                    "task_id": self.get_id(),
                    "timestamp": datetime.now().isoformat(),
                    "context_type": "batch_modification"
                }
            )
            await publish_event(event)
        except Exception as e:
            self.logger.error(f"发布场景批量事件失败: {e}")
    
    # ==================== 辅助方法 ====================
    
    async def _validate_building_data_async(self, building_data: Dict[str, Any]) -> bool:
        """异步验证建筑物数据"""
        required_fields = ["id", "label", "type"]
        return all(field in building_data for field in required_fields)
    
    async def _validate_prop_data_async(self, prop_data: Dict[str, Any]) -> bool:
        """异步验证道具数据"""
        required_fields = ["id", "label"]
        return all(field in prop_data for field in required_fields)
    
    async def _validate_robot_data_async(self, robot_data: Dict[str, Any]) -> bool:
        """异步验证机器人数据"""
        required_fields = ["id", "label", "capabilities"]
        return all(field in robot_data for field in required_fields)
    
    async def _validate_goal_data_async(self, goal_data: Dict[str, Any]) -> bool:
        """异步验证目标数据
        
        Args:
            goal_data: 目标数据字典
            
        Returns:
            验证结果
        """
        try:
            required_fields = ["id", "type"]
            for field in required_fields:
                if field not in goal_data:
                    self.logger.error(f"目标数据缺少必需字段: {field}")
                    return False
            
            # 验证目标类型
            goal_type = goal_data.get("type")
            valid_types = ["navigation", "manipulation", "observation", "interaction", "custom"]
            if goal_type not in valid_types:
                self.logger.warning(f"未知的目标类型: {goal_type}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"验证目标数据时出错: {e}")
            return False
    
    async def _create_prop_instance_async(self, prop_data: Dict[str, Any]) -> Prop:
        """异步创建道具实例"""
        # 这里可以根据prop_data创建具体的Prop实例
        # 暂时返回基础Prop实例
        return Prop(
            entity_id=int(prop_data["id"]),
            label=prop_data["label"],
            initial_state=prop_data.get("state", {})
        )
    
    async def _create_robot_instance_async(self, robot_data: Dict[str, Any]) -> Robot:
        """异步创建机器人实例"""
        # 这里可以根据robot_data创建具体的Robot实例
        # 需要导入相关的capabilities
        from modules.entities.robot.capabilities import Capability
        
        capabilities = set()
        for cap_name in robot_data.get("capabilities", []):
            # 这里需要根据实际的Capability枚举来转换
            capabilities.add(Capability.MOVE)  # 示例
        
        return Robot(
            entity_id=int(robot_data["id"]),
            label=robot_data["label"],
            capabilities=capabilities,
            initial_state=robot_data.get("state", {})
        )
    
    async def _record_change_async(self, change_record: Dict[str, Any]) -> None:
        """异步记录变更历史"""
        self._change_history.append(change_record)
        
        # 限制历史记录大小
        if len(self._change_history) > self._max_history_size:
            self._change_history.pop(0)
    
    # ==================== 查询接口 ====================
    
    async def get_entities_async(self, 
                                entity_type: Optional[str] = None) -> Dict[str, Any]:
        """异步获取实体列表
        
        Args:
            entity_type: 实体类型过滤 (building, prop, robot)
            
        Returns:
            实体字典
        """
        if entity_type == "building":
            return self._buildings.copy()
        elif entity_type == "prop":
            return {k: v.to_dict() if hasattr(v, 'to_dict') else v.__dict__ for k, v in self._props.items()}
        elif entity_type == "robot":
            return {k: v.to_dict() if hasattr(v, 'to_dict') else v.__dict__ for k, v in self._robots.items()}
        else:
            return {
                "buildings": self._buildings.copy(),
                "props": {k: v.to_dict() if hasattr(v, 'to_dict') else v.__dict__ for k, v in self._props.items()},
                "robots": {k: v.to_dict() if hasattr(v, 'to_dict') else v.__dict__ for k, v in self._robots.items()}
            }
    
    async def get_change_history_async(self, 
                                      limit: int = 100,
                                      entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """异步获取变更历史
        
        Args:
            limit: 返回记录数量限制
            entity_type: 实体类型过滤
            
        Returns:
            变更历史列表
        """
        history = self._change_history.copy()
        
        if entity_type:
            history = [record for record in history if entity_type in record.get("type", "")]
        
        return history[-limit:]
    
    # ==================== 基础方法 ====================
    
    def get_id(self) -> str:
        """获取任务ID"""
        return self.task_config.get("id", "unknown_task")
    
    def get_environment_config(self) -> Optional[Dict[str, Any]]:
        """获取环境配置"""
        return self.task_config.get("environment")
    
    async def cleanup_async(self) -> None:
        """异步清理资源"""
        # 取消所有事件订阅
        for subscription_id in self._event_subscriptions:
            unsubscribe_event(subscription_id)
        self._event_subscriptions.clear()
        
        # 清空实体缓存
        self._entities.clear()
        self._buildings.clear()
        self._props.clear()
        self._robots.clear()
        
        # 清空订阅者列表
        self._subscribers.clear()
        
        self.logger.info("异步TaskContext资源已清理")


    def update_config(self, new_config: Dict[str, Any]):
        """更新完整配置"""
        old_config = self.task_config.copy()
        self.task_config.update(new_config)

        # 发布本地事件
        event = {"type": "CONFIG_UPDATED", "old_config": old_config, "new_config": self.task_config}
        self._notify_subscribers(event)

        # 发布全局事件
        asyncio.create_task(self._publish_config_event("updated", old_config, self.task_config))

        self._validate_task()

    async def _publish_config_event(self, action: str, old_value: Any = None, new_value: Any = None):
        """发布配置事件到全局事件总线

        Args:
            action: 动作类型
            old_value: 旧值
            new_value: 新值
        """
        try:
            config_event = ConfigEvent(
                config_key="task_config",
                action=action,
                old_value=old_value,
                new_value=new_value,
                source=f"task_context_{self.get_id()}",
                data={
                    "task_id": self.get_id(),
                    "task_type": self.get_type()
                }
            )
            await publish_event(config_event)
        except Exception as e:
            self.logger.error(f"发布配置事件失败: {e}")

    def update_goal(self, new_goal_data: Dict[str, Any]):
        """更新或设置任务的目标"""
        original_goal = self.get_goal_config()
        self.task_config["goal"] = new_goal_data

        # 重新初始化目标实例
        self._initialize_goal()

        # 发布本地事件
        event = {"type": "GOAL_UPDATED", "old_goal": original_goal, "new_goal": new_goal_data}
        self._notify_subscribers(event)

        # 发布全局事件
        asyncio.create_task(self._publish_goal_event("updated", original_goal, new_goal_data))

        self._validate_task()

    async def _publish_goal_event(self, action: str, old_goal: Any = None, new_goal: Any = None):
        """发布目标事件到全局事件总线

        Args:
            action: 动作类型
            old_goal: 旧目标
            new_goal: 新目标
        """
        try:
            goal_event = GoalEvent(
                goal_id=str(new_goal.get("id", "unknown")) if new_goal else "unknown",
                action=action,
                source=f"task_context_{self.get_id()}",
                data={
                    "task_id": self.get_id(),
                    "old_goal": old_goal,
                    "new_goal": new_goal
                }
            )
            await publish_event(goal_event)
        except Exception as e:
            self.logger.error(f"发布目标事件失败: {e}")

    def remove_goal(self) -> Optional[Dict[str, Any]]:
        """从任务中移除目标"""
        if "goal" in self.task_config:
            removed_goal = self.task_config.pop("goal")
            self._current_goal = None

            # 发布本地事件
            event = {"type": "GOAL_REMOVED", "data": removed_goal}
            self._notify_subscribers(event)

            # 发布全局事件
            asyncio.create_task(self._publish_goal_event("removed", removed_goal, None))

            self._validate_task()
            return removed_goal
        return None

    def update_environment(self, new_env_data: Dict[str, Any]):
        """更新环境配置"""
        original_env = self.get_environment_config()
        self.task_config["environment"] = new_env_data

        # 发布本地事件
        event = {"type": "ENVIRONMENT_UPDATED", "old_env": original_env, "new_env": new_env_data}
        self._notify_subscribers(event)

        # 发布全局事件
        asyncio.create_task(self._publish_task_event("environment_updated", {
            "old_environment": original_env,
            "new_environment": new_env_data
        }))

        self._validate_task()

    def update_robots(self, new_robots_data: Dict[str, Any]):
        """更新机器人配置"""
        original_robots = self.get_robots_config()
        self.task_config["robots"] = new_robots_data

        # 发布本地事件
        event = {"type": "ROBOTS_UPDATED", "old_robots": original_robots, "new_robots": new_robots_data}
        self._notify_subscribers(event)

        # 发布全局事件
        asyncio.create_task(self._publish_task_event("robots_updated", {
            "old_robots": original_robots,
            "new_robots": new_robots_data
        }))

        self._validate_task()

    async def _publish_task_event(self, action: str, data: Dict[str, Any]):
        """发布任务事件到全局事件总线

        Args:
            action: 动作类型
            data: 事件数据
        """
        try:
            task_event = TaskEvent(
                task_id=self.get_id(),
                action=action,
                source=f"task_context_{self.get_id()}",
                data=data
            )
            await publish_event(task_event)
        except Exception as e:
            self.logger.error(f"发布任务事件失败: {e}")

    # ==================== 验证和状态 ====================

    def is_valid(self) -> Optional[bool]:
        """返回当前任务配置的最新合法性状态"""
        return self.is_feasible

    def is_loaded(self) -> bool:
        """检查任务上下文是否已加载"""
        return self.task_config is not None and "environment" in self.task_config

    def validate(self) -> bool:
        """验证任务配置"""
        return self.is_valid() is True

    def get_id(self) -> str:
        """获取任务ID"""
        return self.task_config.get("id", "unknown_task")

    def get_robots_config(self) -> Dict[str, Any]:
        """获取机器人配置"""
        return self.task_config.get("robots", {})

    def _validate_task(self):
        """内部验证任务"""
        # 这里可以添加更复杂的验证逻辑
        self.is_feasible = True

    # ==================== 事件系统 ====================

    def subscribe(self, callback: Callable):
        """订阅事件"""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable):
        """取消订阅"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify_subscribers(self, event: Dict[str, Any]):
        """通知订阅者"""
        for callback in self._subscribers:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"事件回调执行失败: {e}")

    # ==================== 数据访问 ====================

    def _get_nodes(self) -> List[Dict[str, Any]]:
        """获取场景节点（内部方法）"""
        env_config = self.get_environment_config()
        if not env_config:
            return []

        # 从环境配置中提取节点信息
        # 这里需要根据实际的数据结构进行调整
        nodes = env_config.get("nodes", [])
        return nodes

    def get_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取实体"""
        nodes = self._get_nodes()
        for node in nodes:
            if node.get("id") == entity_id:
                return node
        return None

    def get_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """根据类型获取实体列表"""
        nodes = self._get_nodes()
        entities = []
        for node in nodes:
            properties = node.get("properties", {})
            if properties.get("type") == entity_type:
                entities.append(node)
        return entities

    def get_entities_by_category(self, category: str) -> List[Dict[str, Any]]:
        """根据分类获取实体列表"""
        nodes = self._get_nodes()
        entities = []
        for node in nodes:
            properties = node.get("properties", {})
            if properties.get("category") == category:
                entities.append(node)
        return entities

    # ==================== 序列化 ====================

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_config": self.task_config,
            "is_feasible": self.is_feasible,
            "goal_status": self.get_goal_status()
        }

    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskContext':
        """从字典创建实例"""
        return cls(task_config=data.get("task_config", {}))

    @classmethod
    def from_json(cls, json_str: str) -> 'TaskContext':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    # ==================== 调试和日志 ====================

    def __str__(self) -> str:
        """字符串表示"""
        goal_status = self.get_goal_status()
        return f"TaskContext(id={self.get_id()}, type={self.get_type()}, goal_achieved={goal_status['is_achieved']})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"TaskContext(task_config={self.task_config}, is_feasible={self.is_feasible})"