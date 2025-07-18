"""异步任务环境

集成异步任务上下文、场景监控器和事件总线的完整任务环境。
提供场景管理、实体操作和自然语言描述的统一接口。
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from datetime import datetime
from dataclasses import dataclass, field

# 导入核心组件
from ..tasks.task_context import AsyncTaskContext
from ..monitor.async_scene_monitor import AsyncSceneMonitor, SceneDescription
from ..events.event_bus import (
    EventBus, get_global_event_bus, set_global_event_bus,
    start_global_event_bus, stop_global_event_bus,
    publish_event, subscribe_event,
    SystemEvent, TaskEvent, MonitorEvent, EventType
)

logger = logging.getLogger(__name__)


@dataclass
class TaskEnvironmentConfig:
    """任务环境配置
    
    Attributes:
        env_id: 环境ID
        task_config: 任务配置
        scenario_data: 场景数据
        enable_monitoring: 是否启用监控
        enable_natural_language: 是否启用自然语言描述
        monitor_detailed_descriptions: 是否启用详细描述
        max_history_size: 最大历史记录数量
        auto_start_event_bus: 是否自动启动事件总线
    """
    env_id: str = field(default_factory=lambda: f"task_env_{uuid.uuid4().hex[:8]}")
    task_config: Dict[str, Any] = field(default_factory=dict)
    scenario_data: Optional[Dict[str, Any]] = None
    enable_monitoring: bool = True
    enable_natural_language: bool = True
    monitor_detailed_descriptions: bool = True
    max_history_size: int = 1000
    auto_start_event_bus: bool = True


class AsyncTaskEnvironment:
    """异步任务环境
    
    集成了以下核心组件：
    - AsyncTaskContext: 异步任务上下文管理
    - AsyncSceneMonitor: 异步场景监控器
    - EventBus: 事件总线
    
    提供统一的异步接口来管理任务配置、场景实体和自然语言描述。
    
    Attributes:
        config: 环境配置
        task_context: 异步任务上下文
        scene_monitor: 异步场景监控器
        event_bus: 事件总线
        is_initialized: 初始化状态
        is_running: 运行状态
    """
    
    def __init__(self, config: Optional[TaskEnvironmentConfig] = None):
        """初始化异步任务环境
        
        Args:
            config: 环境配置，如果为None则使用默认配置
        """
        self.config = config or TaskEnvironmentConfig()
        
        # 核心组件
        self.task_context: Optional[AsyncTaskContext] = None
        self.scene_monitor: Optional[AsyncSceneMonitor] = None
        self.event_bus: Optional[EventBus] = None
        
        # 状态管理
        self.is_initialized = False
        self.is_running = False
        self._initialization_lock = asyncio.Lock()
        self._operation_lock = asyncio.Lock()
        
        # 事件订阅
        self._event_subscriptions: List[str] = []
        
        # 自然语言描述缓存
        self._cached_scene_description = ""
        self._description_cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 5.0  # 缓存5秒
        
        # 日志
        self.logger = logging.getLogger(f"async_task_env.{self.config.env_id}")
        
        self.logger.info(f"异步任务环境 {self.config.env_id} 已创建")
    
    async def initialize_async(self) -> None:
        """异步初始化环境"""
        async with self._initialization_lock:
            if self.is_initialized:
                self.logger.warning("环境已经初始化")
                return
            
            try:
                # 1. 初始化或获取事件总线
                await self._initialize_event_bus_async()
                
                # 2. 初始化任务上下文
                await self._initialize_task_context_async()
                
                # 3. 初始化场景监控器
                if self.config.enable_monitoring:
                    await self._initialize_scene_monitor_async()
                
                # 4. 设置事件订阅
                await self._setup_event_subscriptions_async()
                
                # 5. 启动组件
                await self._start_components_async()
                
                self.is_initialized = True
                self.is_running = True
                
                # 发布环境初始化完成事件
                await self._publish_system_event_async(
                    "environment_initialized",
                    f"异步任务环境 {self.config.env_id} 初始化完成",
                    {
                        "env_id": self.config.env_id,
                        "monitoring_enabled": self.config.enable_monitoring,
                        "natural_language_enabled": self.config.enable_natural_language
                    }
                )
                
                self.logger.info(f"异步任务环境 {self.config.env_id} 初始化完成")
                
            except Exception as e:
                self.logger.error(f"环境初始化失败: {e}")
                self.is_initialized = False
                self.is_running = False
                raise
    
    async def shutdown_async(self) -> None:
        """异步关闭环境"""
        if not self.is_running:
            self.logger.warning("环境未在运行")
            return
        
        try:
            # 发布环境关闭事件
            await self._publish_system_event_async(
                "environment_shutting_down",
                f"异步任务环境 {self.config.env_id} 正在关闭"
            )
            
            # 停止场景监控器
            if self.scene_monitor:
                await self.scene_monitor.stop_async()
            
            # 取消事件订阅
            for subscription_id in self._event_subscriptions:
                # 注意：这里需要实现unsubscribe_event函数
                pass
            self._event_subscriptions.clear()
            
            # 停止事件总线（如果是自动启动的）
            if self.config.auto_start_event_bus and self.event_bus:
                await stop_global_event_bus()
            
            self.is_running = False
            
            self.logger.info(f"异步任务环境 {self.config.env_id} 关闭完成")
            
        except Exception as e:
            self.logger.error(f"环境关闭失败: {e}")
            raise
    
    async def _initialize_event_bus_async(self) -> None:
        """异步初始化事件总线"""
        try:
            # 获取或创建全局事件总线
            self.event_bus = get_global_event_bus()
            
            if self.event_bus is None:
                from ..events.event_bus import EventBus
                self.event_bus = EventBus()
                set_global_event_bus(self.event_bus)
            
            # 如果配置为自动启动，则启动事件总线
            if self.config.auto_start_event_bus:
                await start_global_event_bus()
            
            self.logger.debug("事件总线初始化完成")
            
        except Exception as e:
            self.logger.error(f"事件总线初始化失败: {e}")
            raise
    
    async def _initialize_task_context_async(self) -> None:
        """异步初始化任务上下文"""
        try:
            self.task_context = AsyncTaskContext(
                task_config=self.config.task_config,
                scenario_data=self.config.scenario_data
            )
            
            # 等待任务上下文初始化完成
            # 注意：AsyncTaskContext的_initialize_async是在__init__中通过create_task调用的
            # 这里我们需要等待一下确保初始化完成
            await asyncio.sleep(0.1)  # 给一点时间让初始化任务执行
            
            self.logger.debug("任务上下文初始化完成")
            
        except Exception as e:
            self.logger.error(f"任务上下文初始化失败: {e}")
            raise
    
    async def _initialize_scene_monitor_async(self) -> None:
        """异步初始化场景监控器"""
        try:
            self.scene_monitor = AsyncSceneMonitor(
                monitor_id=f"{self.config.env_id}_monitor",
                event_bus=self.event_bus,
                max_history_size=self.config.max_history_size,
                enable_detailed_descriptions=self.config.monitor_detailed_descriptions
            )
            
            self.logger.debug("场景监控器初始化完成")
            
        except Exception as e:
            self.logger.error(f"场景监控器初始化失败: {e}")
            raise
    
    async def _setup_event_subscriptions_async(self) -> None:
        """异步设置事件订阅"""
        try:
            # 订阅监控事件以更新缓存
            if self.config.enable_natural_language:
                monitor_subscription_id = subscribe_event(
                    EventType.MONITOR.value,
                    self._handle_monitor_event_async,
                    f"{self.config.env_id}_monitor_handler"
                )
                self._event_subscriptions.append(monitor_subscription_id)
            
            # 订阅系统事件
            system_subscription_id = subscribe_event(
                EventType.SYSTEM.value,
                self._handle_system_event_async,
                f"{self.config.env_id}_system_handler"
            )
            self._event_subscriptions.append(system_subscription_id)
            
            self.logger.debug("事件订阅设置完成")
            
        except Exception as e:
            self.logger.error(f"事件订阅设置失败: {e}")
            raise
    
    async def _start_components_async(self) -> None:
        """异步启动组件"""
        try:
            # 启动场景监控器
            if self.scene_monitor:
                await self.scene_monitor.start_async()
            
            self.logger.debug("组件启动完成")
            
        except Exception as e:
            self.logger.error(f"组件启动失败: {e}")
            raise
    
    async def _handle_monitor_event_async(self, event: MonitorEvent) -> None:
        """异步处理监控事件
        
        Args:
            event: 监控事件
        """
        try:
            # 更新自然语言描述缓存
            if event.description_type in ["scene_update", "entity_change"]:
                self._cached_scene_description = event.natural_language_description
                self._description_cache_timestamp = datetime.now()
            
            self.logger.debug(f"处理监控事件: {event.description_type}")
            
        except Exception as e:
            self.logger.error(f"处理监控事件失败: {e}")
    
    async def _handle_system_event_async(self, event: SystemEvent) -> None:
        """异步处理系统事件
        
        Args:
            event: 系统事件
        """
        try:
            self.logger.debug(f"处理系统事件: {event.message}")
            
        except Exception as e:
            self.logger.error(f"处理系统事件失败: {e}")
    
    async def _publish_system_event_async(self, 
                                         action: str, 
                                         message: str, 
                                         data: Optional[Dict[str, Any]] = None) -> None:
        """异步发布系统事件
        
        Args:
            action: 动作类型
            message: 事件消息
            data: 事件数据
        """
        try:
            system_event = SystemEvent(
                message=message,
                data=data or {},
                source=f"async_task_env.{self.config.env_id}"
            )
            
            await publish_event(system_event)
            
        except Exception as e:
            self.logger.error(f"发布系统事件失败: {e}")
    
    # ==================== 实体管理API ====================
    
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
        if not self.task_context:
            return False, "任务上下文未初始化"
        
        return await self.task_context.add_building_async(building_data, validate)
    
    async def update_building_async(self, 
                                   building_id: str,
                                   updates: Dict[str, Any],
                                   merge: bool = True) -> Tuple[bool, str]:
        """异步更新建筑物
        
        Args:
            building_id: 建筑物ID
            updates: 更新数据
            merge: 是否合并更新
            
        Returns:
            (成功标志, 消息)
        """
        if not self.task_context:
            return False, "任务上下文未初始化"
        
        return await self.task_context.update_building_async(building_id, updates, merge)
    
    async def remove_building_async(self, building_id: str) -> Tuple[bool, str]:
        """异步移除建筑物
        
        Args:
            building_id: 建筑物ID
            
        Returns:
            (成功标志, 消息)
        """
        if not self.task_context:
            return False, "任务上下文未初始化"
        
        return await self.task_context.remove_building_async(building_id)
    
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
        if not self.task_context:
            return False, "任务上下文未初始化"
        
        return await self.task_context.add_prop_async(prop_data, validate)
    
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
        if not self.task_context:
            return False, "任务上下文未初始化"
        
        return await self.task_context.update_prop_state_async(prop_id, state_updates)
    
    async def remove_prop_async(self, prop_id: str) -> Tuple[bool, str]:
        """异步移除道具
        
        Args:
            prop_id: 道具ID
            
        Returns:
            (成功标志, 消息)
        """
        if not self.task_context:
            return False, "任务上下文未初始化"
        
        return await self.task_context.remove_prop_async(prop_id)
    
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
        if not self.task_context:
            return False, "任务上下文未初始化"
        
        # 注意：这里假设task_context有add_robot_async方法
        # 如果没有，需要在AsyncTaskContext中添加
        if hasattr(self.task_context, 'add_robot_async'):
            return await self.task_context.add_robot_async(robot_data, validate)
        else:
            return False, "机器人管理功能未实现"
    
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
        if not self.task_context:
            return False, "任务上下文未初始化"
        
        if hasattr(self.task_context, 'update_robot_async'):
            return await self.task_context.update_robot_async(robot_id, updates, merge)
        else:
            return False, "机器人管理功能未实现"
    
    async def remove_robot_async(self, robot_id: str) -> Tuple[bool, str]:
        """异步移除机器人
        
        Args:
            robot_id: 机器人ID
            
        Returns:
            (成功标志, 消息)
        """
        if not self.task_context:
            return False, "任务上下文未初始化"
        
        if hasattr(self.task_context, 'remove_robot_async'):
            return await self.task_context.remove_robot_async(robot_id)
        else:
            return False, "机器人管理功能未实现"
    
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
        if not self.task_context:
            return False, "任务上下文未初始化"
        
        # 注意：这里假设task_context有add_goal_async方法
        if hasattr(self.task_context, 'add_goal_async'):
            return await self.task_context.add_goal_async(goal_data, validate)
        else:
            return False, "目标管理功能未实现"
    
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
        if not self.task_context:
            return False, "任务上下文未初始化"
        
        if hasattr(self.task_context, 'update_goal_async'):
            return await self.task_context.update_goal_async(goal_id, updates, merge)
        else:
            return False, "目标管理功能未实现"
    
    async def remove_goal_async(self, goal_id: str) -> Tuple[bool, str]:
        """异步移除目标
        
        Args:
            goal_id: 目标ID
            
        Returns:
            (成功标志, 消息)
        """
        if not self.task_context:
            return False, "任务上下文未初始化"
        
        if hasattr(self.task_context, 'remove_goal_async'):
            return await self.task_context.remove_goal_async(goal_id)
        else:
            return False, "目标管理功能未实现"
    
    # ==================== 自然语言描述API ====================
    
    async def get_current_scene_description_async(self, force_refresh: bool = False) -> str:
        """异步获取当前场景的自然语言描述
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            场景的自然语言描述
        """
        if not self.config.enable_natural_language:
            return "自然语言描述功能未启用"
        
        if not self.scene_monitor:
            return "场景监控器未初始化"
        
        try:
            # 检查缓存是否有效
            now = datetime.now()
            cache_valid = (
                not force_refresh and
                self._description_cache_timestamp and
                (now - self._description_cache_timestamp).total_seconds() < self._cache_ttl_seconds and
                self._cached_scene_description
            )
            
            if cache_valid:
                return self._cached_scene_description
            
            # 获取新的场景摘要
            scene_summary = await self.scene_monitor.get_current_scene_summary_async()
            
            # 更新缓存
            self._cached_scene_description = scene_summary
            self._description_cache_timestamp = now
            
            return scene_summary
            
        except Exception as e:
            self.logger.error(f"获取场景描述失败: {e}")
            return "无法获取场景描述"
    
    async def get_scene_change_history_async(self, limit: int = 10) -> List[str]:
        """异步获取场景变化历史
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            场景变化历史描述列表
        """
        if not self.config.enable_natural_language or not self.scene_monitor:
            return []
        
        try:
            history = await self.scene_monitor.get_description_history_async(limit)
            return [desc.description for desc in history]
            
        except Exception as e:
            self.logger.error(f"获取场景变化历史失败: {e}")
            return []
    
    async def get_detailed_scene_report_async(self) -> Dict[str, Any]:
        """异步获取详细的场景报告
        
        Returns:
            包含场景状态、描述和统计信息的详细报告
        """
        try:
            report = {
                "env_id": self.config.env_id,
                "timestamp": datetime.now().isoformat(),
                "is_running": self.is_running,
                "current_description": await self.get_current_scene_description_async(),
                "change_history": await self.get_scene_change_history_async(5),
                "scene_state": {},
                "monitor_stats": {},
                "task_context_stats": {}
            }
            
            # 添加场景状态
            if self.scene_monitor:
                report["scene_state"] = self.scene_monitor.get_scene_state()
                report["monitor_stats"] = self.scene_monitor.get_monitor_stats()
            
            # 添加任务上下文统计
            if self.task_context:
                # 注意：这里假设task_context有get_stats方法
                if hasattr(self.task_context, 'get_stats'):
                    report["task_context_stats"] = self.task_context.get_stats()
            
            return report
            
        except Exception as e:
            self.logger.error(f"生成详细场景报告失败: {e}")
            return {
                "env_id": self.config.env_id,
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    # ==================== 批量操作API ====================
    
    async def batch_add_entities_async(self, 
                                      entities: List[Dict[str, Any]],
                                      validate: bool = True) -> Dict[str, Any]:
        """异步批量添加实体
        
        Args:
            entities: 实体数据列表，每个实体需要包含'type'字段
            validate: 是否验证数据
            
        Returns:
            批量操作结果字典
        """
        if not self.task_context:
            return {"success": False, "message": "任务上下文未初始化"}
        
        async with self._operation_lock:
            try:
                results = {
                    "success": True,
                    "total": len(entities),
                    "successful": 0,
                    "failed": 0,
                    "details": []
                }
                
                for entity_data in entities:
                    entity_type = entity_data.get("type")
                    entity_id = entity_data.get("id", "unknown")
                    
                    try:
                        if entity_type == "building":
                            success, message = await self.add_building_async(entity_data, validate)
                        elif entity_type == "prop":
                            success, message = await self.add_prop_async(entity_data, validate)
                        elif entity_type == "robot":
                            success, message = await self.add_robot_async(entity_data, validate)
                        elif entity_type == "goal":
                            success, message = await self.add_goal_async(entity_data, validate)
                        else:
                            success, message = False, f"未知实体类型: {entity_type}"
                        
                        if success:
                            results["successful"] += 1
                        else:
                            results["failed"] += 1
                        
                        results["details"].append({
                            "entity_id": entity_id,
                            "entity_type": entity_type,
                            "success": success,
                            "message": message
                        })
                        
                    except Exception as e:
                        results["failed"] += 1
                        results["details"].append({
                            "entity_id": entity_id,
                            "entity_type": entity_type,
                            "success": False,
                            "message": str(e)
                        })
                
                # 发布批量操作事件
                if results["successful"] > 0:
                    from ..events.event_bus import SceneBatchEvent
                    batch_event = SceneBatchEvent(
                        operation_id=str(uuid.uuid4()),
                        operation_type="batch_add",
                        entity_changes=[
                            {
                                "entity_id": detail["entity_id"],
                                "entity_type": detail["entity_type"],
                                "action": "added",
                                "success": detail["success"]
                            }
                            for detail in results["details"]
                            if detail["success"]
                        ],
                        summary=f"批量添加了 {results['successful']} 个实体",
                        source=f"async_task_env.{self.config.env_id}"
                    )
                    await publish_event(batch_event)
                
                if results["failed"] > 0:
                    results["success"] = False
                
                return results
                
            except Exception as e:
                self.logger.error(f"批量添加实体失败: {e}")
                return {
                    "success": False,
                    "message": str(e),
                    "total": len(entities),
                    "successful": 0,
                    "failed": len(entities)
                }
    
    # ==================== 状态查询API ====================
    
    def get_environment_status(self) -> Dict[str, Any]:
        """获取环境状态
        
        Returns:
            环境状态字典
        """
        return {
            "env_id": self.config.env_id,
            "is_initialized": self.is_initialized,
            "is_running": self.is_running,
            "config": {
                "enable_monitoring": self.config.enable_monitoring,
                "enable_natural_language": self.config.enable_natural_language,
                "monitor_detailed_descriptions": self.config.monitor_detailed_descriptions,
                "max_history_size": self.config.max_history_size
            },
            "components": {
                "task_context": self.task_context is not None,
                "scene_monitor": self.scene_monitor is not None,
                "event_bus": self.event_bus is not None
            },
            "subscriptions_count": len(self._event_subscriptions),
            "cache_status": {
                "has_cached_description": bool(self._cached_scene_description),
                "cache_timestamp": self._description_cache_timestamp.isoformat() if self._description_cache_timestamp else None
            }
        }
    
    def get_config(self) -> TaskEnvironmentConfig:
        """获取环境配置
        
        Returns:
            环境配置对象
        """
        return self.config
    
    async def health_check_async(self) -> Dict[str, Any]:
        """异步健康检查
        
        Returns:
            健康检查结果
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "env_id": self.config.env_id,
            "components": {},
            "warnings": [],
            "errors": []
        }
        
        try:
            # 检查基本状态
            if not self.is_initialized:
                health_status["errors"].append("环境未初始化")
                health_status["status"] = "unhealthy"
            
            if not self.is_running:
                health_status["errors"].append("环境未运行")
                health_status["status"] = "unhealthy"
            
            # 检查组件状态
            health_status["components"]["task_context"] = {
                "available": self.task_context is not None,
                "status": "ok" if self.task_context else "missing"
            }
            
            health_status["components"]["scene_monitor"] = {
                "available": self.scene_monitor is not None,
                "running": self.scene_monitor.is_running if self.scene_monitor else False,
                "status": "ok" if (self.scene_monitor and self.scene_monitor.is_running) else "not_running"
            }
            
            health_status["components"]["event_bus"] = {
                "available": self.event_bus is not None,
                "status": "ok" if self.event_bus else "missing"
            }
            
            # 检查事件总线健康状态
            if self.event_bus and hasattr(self.event_bus, 'health_check'):
                try:
                    bus_health = await self.event_bus.health_check()
                    health_status["components"]["event_bus"]["details"] = bus_health
                    if bus_health.get("status") != "healthy":
                        health_status["warnings"].append(f"事件总线状态: {bus_health.get('status')}")
                except Exception as e:
                    health_status["warnings"].append(f"事件总线健康检查失败: {e}")
            
            # 根据错误和警告确定最终状态
            if health_status["errors"]:
                health_status["status"] = "unhealthy"
            elif health_status["warnings"]:
                health_status["status"] = "degraded"
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["errors"].append(f"健康检查异常: {e}")
        
        return health_status


# ==================== 便利函数 ====================

async def create_async_task_environment(config: Optional[TaskEnvironmentConfig] = None) -> AsyncTaskEnvironment:
    """创建并初始化异步任务环境
    
    Args:
        config: 环境配置
        
    Returns:
        已初始化的异步任务环境
    """
    env = AsyncTaskEnvironment(config)
    await env.initialize_async()
    return env


async def create_simple_task_environment(task_config: Optional[Dict[str, Any]] = None,
                                        scenario_data: Optional[Dict[str, Any]] = None,
                                        enable_monitoring: bool = True) -> AsyncTaskEnvironment:
    """创建简单的异步任务环境
    
    Args:
        task_config: 任务配置
        scenario_data: 场景数据
        enable_monitoring: 是否启用监控
        
    Returns:
        已初始化的异步任务环境
    """
    config = TaskEnvironmentConfig(
        task_config=task_config or {},
        scenario_data=scenario_data,
        enable_monitoring=enable_monitoring
    )
    
    return await create_async_task_environment(config)