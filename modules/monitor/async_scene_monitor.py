"""异步场景监控器

监控场景中实体的变化，生成自然语言描述并发布监控事件。
订阅SceneEntityEvent和SceneBatchEvent，生成对应的自然语言描述。
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field

from ..events.event_bus import (
    EventBus, get_global_event_bus, subscribe_event, publish_event,
    SceneEntityEvent, SceneBatchEvent, MonitorEvent, EventType
)

logger = logging.getLogger(__name__)


@dataclass
class SceneDescription:
    """场景描述数据类
    
    Attributes:
        description: 自然语言描述
        entities: 相关实体列表
        timestamp: 生成时间戳
        context: 上下文信息
    """
    description: str
    entities: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)


class AsyncSceneMonitor:
    """异步场景监控器
    
    监控场景中building、prop、robot、goal等实体的增删改查操作，
    生成自然语言描述并通过事件总线发布。
    
    Attributes:
        monitor_id: 监控器唯一标识
        event_bus: 事件总线实例
        is_running: 运行状态
        _subscriptions: 事件订阅ID列表
        _scene_state: 当前场景状态缓存
        _description_history: 描述历史记录
        _language_generator: 自然语言生成器
    """
    
    def __init__(self, 
                 monitor_id: Optional[str] = None,
                 event_bus: Optional[EventBus] = None,
                 max_history_size: int = 1000,
                 enable_detailed_descriptions: bool = True):
        """初始化异步场景监控器
        
        Args:
            monitor_id: 监控器ID，如果为None则自动生成
            event_bus: 事件总线实例，如果为None则使用全局实例
            max_history_size: 最大历史记录数量
            enable_detailed_descriptions: 是否启用详细描述
        """
        self.monitor_id = monitor_id or f"scene_monitor_{uuid.uuid4().hex[:8]}"
        self.event_bus = event_bus or get_global_event_bus()
        self.max_history_size = max_history_size
        self.enable_detailed_descriptions = enable_detailed_descriptions
        
        # 运行状态
        self.is_running = False
        self._subscriptions: List[str] = []
        
        # 场景状态管理
        self._scene_state: Dict[str, Dict[str, Any]] = {
            "buildings": {},
            "props": {},
            "robots": {},
            "goals": {}
        }
        
        # 描述历史和缓存
        self._description_history: List[SceneDescription] = []
        self._last_scene_summary = ""
        
        # 自然语言生成配置
        self._language_templates = self._initialize_language_templates()
        
        # 日志
        self.logger = logging.getLogger(f"async_scene_monitor.{self.monitor_id}")
        
        self.logger.info(f"异步场景监控器 {self.monitor_id} 已创建")
    
    def _initialize_language_templates(self) -> Dict[str, Dict[str, str]]:
        """初始化自然语言模板
        
        Returns:
            语言模板字典
        """
        return {
            "building": {
                "added": "在场景中添加了建筑物 '{label}'（ID: {entity_id}）{position_desc}",
                "updated": "建筑物 '{label}'（ID: {entity_id}）的信息已更新{update_desc}",
                "removed": "从场景中移除了建筑物 '{label}'（ID: {entity_id}）",
                "state_changed": "建筑物 '{label}'（ID: {entity_id}）的状态发生了变化{state_desc}"
            },
            "prop": {
                "added": "在场景中添加了道具 '{label}'（ID: {entity_id}）{position_desc}",
                "updated": "道具 '{label}'（ID: {entity_id}）的信息已更新{update_desc}",
                "removed": "从场景中移除了道具 '{label}'（ID: {entity_id}）",
                "state_changed": "道具 '{label}'（ID: {entity_id}）的状态发生了变化{state_desc}"
            },
            "robot": {
                "added": "机器人 '{label}'（ID: {entity_id}）加入了场景{position_desc}",
                "updated": "机器人 '{label}'（ID: {entity_id}）的配置已更新{update_desc}",
                "removed": "机器人 '{label}'（ID: {entity_id}）离开了场景",
                "state_changed": "机器人 '{label}'（ID: {entity_id}）的状态发生了变化{state_desc}"
            },
            "goal": {
                "added": "设置了新的目标 '{label}'（ID: {entity_id}）{goal_desc}",
                "updated": "目标 '{label}'（ID: {entity_id}）已更新{update_desc}",
                "removed": "移除了目标 '{label}'（ID: {entity_id}）",
                "state_changed": "目标 '{label}'（ID: {entity_id}）的状态发生了变化{state_desc}"
            }
        }
    
    async def start_async(self) -> None:
        """异步启动监控器"""
        if self.is_running:
            self.logger.warning("监控器已经在运行")
            return
        
        try:
            # 订阅场景实体事件
            entity_subscription_id = subscribe_event(
                EventType.SCENE_ENTITY.value,
                self._handle_scene_entity_event_async,
                f"{self.monitor_id}_entity"
            )
            self._subscriptions.append(entity_subscription_id)
            
            # 订阅场景批量事件
            batch_subscription_id = subscribe_event(
                EventType.SCENE_BATCH.value,
                self._handle_scene_batch_event_async,
                f"{self.monitor_id}_batch"
            )
            self._subscriptions.append(batch_subscription_id)
            
            self.is_running = True
            
            # 发布监控器启动事件
            await self._publish_monitor_event_async(
                "system_status",
                f"场景监控器 {self.monitor_id} 已启动，开始监控场景变化",
                severity="info"
            )
            
            self.logger.info(f"异步场景监控器 {self.monitor_id} 启动成功")
            
        except Exception as e:
            self.logger.error(f"启动监控器失败: {e}")
            self.is_running = False
            raise
    
    async def stop_async(self) -> None:
        """异步停止监控器"""
        if not self.is_running:
            self.logger.warning("监控器未在运行")
            return
        
        try:
            # 取消事件订阅
            for subscription_id in self._subscriptions:
                # 注意：这里需要实现unsubscribe_event函数
                # unsubscribe_event(subscription_id)
                pass
            
            self._subscriptions.clear()
            self.is_running = False
            
            # 发布监控器停止事件
            await self._publish_monitor_event_async(
                "system_status",
                f"场景监控器 {self.monitor_id} 已停止",
                severity="info"
            )
            
            self.logger.info(f"异步场景监控器 {self.monitor_id} 停止成功")
            
        except Exception as e:
            self.logger.error(f"停止监控器失败: {e}")
            raise
    
    async def _handle_scene_entity_event_async(self, event: SceneEntityEvent) -> None:
        """异步处理场景实体事件
        
        Args:
            event: 场景实体事件
        """
        try:
            # 更新场景状态缓存
            await self._update_scene_state_async(event)
            
            # 生成自然语言描述
            description = await self._generate_entity_description_async(event)
            
            if description:
                # 添加到历史记录
                scene_desc = SceneDescription(
                    description=description,
                    entities=[event.entity_id],
                    context={
                        "event_type": "scene_entity",
                        "entity_type": event.entity_type,
                        "action": event.action,
                        "event_id": event.event_id
                    }
                )
                await self._add_to_history_async(scene_desc)
                
                # 发布监控事件
                await self._publish_monitor_event_async(
                    "entity_change",
                    description,
                    related_entities=[event.entity_id],
                    context={
                        "original_event_id": event.event_id,
                        "entity_type": event.entity_type,
                        "action": event.action
                    }
                )
            
            self.logger.debug(f"处理场景实体事件: {event.entity_type} {event.action} {event.entity_id}")
            
        except Exception as e:
            self.logger.error(f"处理场景实体事件失败: {e}")
    
    async def _handle_scene_batch_event_async(self, event: SceneBatchEvent) -> None:
        """异步处理场景批量事件
        
        Args:
            event: 场景批量事件
        """
        try:
            # 生成批量操作描述
            description = await self._generate_batch_description_async(event)
            
            if description:
                # 提取相关实体ID
                related_entities = []
                for change in event.entity_changes:
                    if "entity_id" in change:
                        related_entities.append(change["entity_id"])
                
                # 添加到历史记录
                scene_desc = SceneDescription(
                    description=description,
                    entities=related_entities,
                    context={
                        "event_type": "scene_batch",
                        "operation_type": event.operation_type,
                        "operation_id": event.operation_id,
                        "event_id": event.event_id
                    }
                )
                await self._add_to_history_async(scene_desc)
                
                # 发布监控事件
                await self._publish_monitor_event_async(
                    "scene_update",
                    description,
                    related_entities=related_entities,
                    context={
                        "original_event_id": event.event_id,
                        "operation_type": event.operation_type,
                        "operation_id": event.operation_id
                    }
                )
            
            self.logger.debug(f"处理场景批量事件: {event.operation_type} {event.operation_id}")
            
        except Exception as e:
            self.logger.error(f"处理场景批量事件失败: {e}")
    
    async def _update_scene_state_async(self, event: SceneEntityEvent) -> None:
        """异步更新场景状态缓存
        
        Args:
            event: 场景实体事件
        """
        entity_type = event.entity_type
        entity_id = event.entity_id
        action = event.action
        
        if entity_type not in self._scene_state:
            self._scene_state[entity_type] = {}
        
        if action == "added" and event.new_data:
            self._scene_state[entity_type][entity_id] = event.new_data.copy()
        elif action == "updated" and event.new_data:
            if entity_id in self._scene_state[entity_type]:
                self._scene_state[entity_type][entity_id].update(event.new_data)
            else:
                self._scene_state[entity_type][entity_id] = event.new_data.copy()
        elif action == "removed":
            self._scene_state[entity_type].pop(entity_id, None)
        elif action == "state_changed" and event.new_data:
            if entity_id in self._scene_state[entity_type]:
                # 更新状态信息
                if "state" not in self._scene_state[entity_type][entity_id]:
                    self._scene_state[entity_type][entity_id]["state"] = {}
                self._scene_state[entity_type][entity_id]["state"].update(event.new_data)
    
    async def _generate_entity_description_async(self, event: SceneEntityEvent) -> str:
        """异步生成实体变化的自然语言描述
        
        Args:
            event: 场景实体事件
            
        Returns:
            自然语言描述
        """
        try:
            entity_type = event.entity_type
            action = event.action
            entity_label = event.entity_label or "未知实体"
            
            # 获取模板
            if entity_type not in self._language_templates:
                return f"{entity_type} '{entity_label}' {action}"
            
            if action not in self._language_templates[entity_type]:
                return f"{entity_type} '{entity_label}' {action}"
            
            template = self._language_templates[entity_type][action]
            
            # 准备模板参数
            template_params = {
                "label": entity_label,
                "entity_id": event.entity_id,
                "position_desc": await self._format_position_description_async(event.position),
                "update_desc": await self._format_update_description_async(event.old_data, event.new_data),
                "state_desc": await self._format_state_description_async(event.old_data, event.new_data),
                "goal_desc": await self._format_goal_description_async(event.new_data)
            }
            
            # 格式化描述
            description = template.format(**template_params)
            
            # 如果启用详细描述，添加额外信息
            if self.enable_detailed_descriptions:
                additional_info = await self._generate_additional_info_async(event)
                if additional_info:
                    description += f"。{additional_info}"
            
            return description
            
        except Exception as e:
            self.logger.error(f"生成实体描述失败: {e}")
            return f"{event.entity_type} '{event.entity_label}' {event.action}"
    
    async def _generate_batch_description_async(self, event: SceneBatchEvent) -> str:
        """异步生成批量操作的自然语言描述
        
        Args:
            event: 场景批量事件
            
        Returns:
            自然语言描述
        """
        try:
            operation_type = event.operation_type
            entity_count = len(event.entity_changes)
            
            if operation_type == "batch_add":
                description = f"批量添加了 {entity_count} 个实体到场景中"
            elif operation_type == "batch_update":
                description = f"批量更新了 {entity_count} 个实体的信息"
            elif operation_type == "batch_remove":
                description = f"批量从场景中移除了 {entity_count} 个实体"
            else:
                description = f"对 {entity_count} 个实体执行了批量操作: {operation_type}"
            
            # 添加摘要信息
            if event.summary:
                description += f"。{event.summary}"
            
            # 如果启用详细描述，添加实体类型统计
            if self.enable_detailed_descriptions and entity_count <= 10:
                entity_types = {}
                for change in event.entity_changes:
                    entity_type = change.get("entity_type", "unknown")
                    entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
                
                if entity_types:
                    type_desc = ", ".join([f"{count}个{etype}" for etype, count in entity_types.items()])
                    description += f"，包括: {type_desc}"
            
            return description
            
        except Exception as e:
            self.logger.error(f"生成批量描述失败: {e}")
            return f"执行了批量操作: {event.operation_type}"
    
    async def _format_position_description_async(self, position: Optional[Dict[str, Any]]) -> str:
        """异步格式化位置描述
        
        Args:
            position: 位置信息字典
            
        Returns:
            位置描述字符串
        """
        if not position:
            return ""
        
        try:
            if "x" in position and "y" in position:
                return f"，位置在 ({position['x']:.1f}, {position['y']:.1f})"
            elif "coordinates" in position:
                coords = position["coordinates"]
                if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    return f"，位置在 ({coords[0]:.1f}, {coords[1]:.1f})"
            elif "location" in position:
                return f"，位置在 {position['location']}"
        except Exception:
            pass
        
        return ""
    
    async def _format_update_description_async(self, 
                                              old_data: Optional[Dict[str, Any]], 
                                              new_data: Optional[Dict[str, Any]]) -> str:
        """异步格式化更新描述
        
        Args:
            old_data: 旧数据
            new_data: 新数据
            
        Returns:
            更新描述字符串
        """
        if not old_data or not new_data:
            return ""
        
        try:
            changes = []
            for key, new_value in new_data.items():
                if key in old_data and old_data[key] != new_value:
                    changes.append(f"{key}: {old_data[key]} → {new_value}")
            
            if changes and len(changes) <= 3:  # 只显示前3个变化
                return f"，变更: {', '.join(changes)}"
        except Exception:
            pass
        
        return ""
    
    async def _format_state_description_async(self, 
                                             old_data: Optional[Dict[str, Any]], 
                                             new_data: Optional[Dict[str, Any]]) -> str:
        """异步格式化状态描述
        
        Args:
            old_data: 旧数据
            new_data: 新数据
            
        Returns:
            状态描述字符串
        """
        if not new_data:
            return ""
        
        try:
            if "status" in new_data:
                return f"，当前状态: {new_data['status']}"
            elif "state" in new_data:
                state = new_data["state"]
                if isinstance(state, dict) and "status" in state:
                    return f"，当前状态: {state['status']}"
        except Exception:
            pass
        
        return ""
    
    async def _format_goal_description_async(self, data: Optional[Dict[str, Any]]) -> str:
        """异步格式化目标描述
        
        Args:
            data: 目标数据
            
        Returns:
            目标描述字符串
        """
        if not data:
            return ""
        
        try:
            if "description" in data:
                return f"，描述: {data['description']}"
            elif "objective" in data:
                return f"，目标: {data['objective']}"
        except Exception:
            pass
        
        return ""
    
    async def _generate_additional_info_async(self, event: SceneEntityEvent) -> str:
        """异步生成额外信息
        
        Args:
            event: 场景实体事件
            
        Returns:
            额外信息字符串
        """
        try:
            info_parts = []
            
            # 添加时间信息
            info_parts.append(f"时间: {event.timestamp.strftime('%H:%M:%S')}")
            
            # 添加来源信息
            if event.source:
                info_parts.append(f"来源: {event.source}")
            
            # 添加元数据信息
            if event.metadata:
                metadata_desc = ", ".join([f"{k}: {v}" for k, v in event.metadata.items() if k not in ["internal", "debug"]])
                if metadata_desc:
                    info_parts.append(f"元数据: {metadata_desc}")
            
            return " | ".join(info_parts) if info_parts else ""
            
        except Exception:
            return ""
    
    async def _add_to_history_async(self, scene_desc: SceneDescription) -> None:
        """异步添加到历史记录
        
        Args:
            scene_desc: 场景描述
        """
        self._description_history.append(scene_desc)
        
        # 保持历史记录大小限制
        if len(self._description_history) > self.max_history_size:
            self._description_history = self._description_history[-self.max_history_size:]
    
    async def _publish_monitor_event_async(self, 
                                          description_type: str,
                                          description: str,
                                          related_entities: Optional[List[str]] = None,
                                          severity: str = "info",
                                          context: Optional[Dict[str, Any]] = None) -> None:
        """异步发布监控事件
        
        Args:
            description_type: 描述类型
            description: 自然语言描述
            related_entities: 相关实体列表
            severity: 严重程度
            context: 上下文信息
        """
        try:
            monitor_event = MonitorEvent(
                monitor_id=self.monitor_id,
                description_type=description_type,
                natural_language_description=description,
                related_entities=related_entities or [],
                severity=severity,
                context=context or {},
                source=f"async_scene_monitor.{self.monitor_id}"
            )
            
            await publish_event(monitor_event)
            
        except Exception as e:
            self.logger.error(f"发布监控事件失败: {e}")
    
    async def get_current_scene_summary_async(self) -> str:
        """异步获取当前场景摘要
        
        Returns:
            场景摘要的自然语言描述
        """
        try:
            summary_parts = []
            
            # 统计各类实体数量
            for entity_type, entities in self._scene_state.items():
                count = len(entities)
                if count > 0:
                    if entity_type == "buildings":
                        summary_parts.append(f"{count}个建筑物")
                    elif entity_type == "props":
                        summary_parts.append(f"{count}个道具")
                    elif entity_type == "robots":
                        summary_parts.append(f"{count}个机器人")
                    elif entity_type == "goals":
                        summary_parts.append(f"{count}个目标")
                    else:
                        summary_parts.append(f"{count}个{entity_type}")
            
            if summary_parts:
                summary = f"当前场景包含: {', '.join(summary_parts)}"
            else:
                summary = "当前场景为空"
            
            # 添加最近的变化
            if self._description_history:
                recent_changes = self._description_history[-3:]  # 最近3个变化
                if recent_changes:
                    recent_desc = "; ".join([desc.description for desc in recent_changes])
                    summary += f"。最近的变化: {recent_desc}"
            
            self._last_scene_summary = summary
            return summary
            
        except Exception as e:
            self.logger.error(f"生成场景摘要失败: {e}")
            return "无法生成场景摘要"
    
    async def get_description_history_async(self, limit: int = 10) -> List[SceneDescription]:
        """异步获取描述历史记录
        
        Args:
            limit: 返回记录数量限制
            
        Returns:
            描述历史记录列表
        """
        return self._description_history[-limit:] if self._description_history else []
    
    def get_scene_state(self) -> Dict[str, Dict[str, Any]]:
        """获取当前场景状态
        
        Returns:
            场景状态字典
        """
        return self._scene_state.copy()
    
    def get_monitor_stats(self) -> Dict[str, Any]:
        """获取监控器统计信息
        
        Returns:
            统计信息字典
        """
        total_entities = sum(len(entities) for entities in self._scene_state.values())
        
        return {
            "monitor_id": self.monitor_id,
            "is_running": self.is_running,
            "total_entities": total_entities,
            "entity_breakdown": {k: len(v) for k, v in self._scene_state.items()},
            "description_history_count": len(self._description_history),
            "subscriptions_count": len(self._subscriptions),
            "last_scene_summary": self._last_scene_summary
        }