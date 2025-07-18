"""全局事件总线实现

提供系统组件间的异步事件通信机制。
基于refactored_system的event_bus实现，提供全局单例模式。
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, deque
import uuid
import logging
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)

# 全局事件总线实例
_global_event_bus: Optional['EventBus'] = None

# 导入增强事件总线组件（如果可用）
try:
    from .enhanced_event_bus import (
        get_enhanced_event_bus, EnhancedEventBus, EnhancedEvent,
        EventCategory as EnhancedEventCategory, EventPriority, MonitorType
    )
    ENHANCED_EVENT_BUS_AVAILABLE = True
except ImportError:
    ENHANCED_EVENT_BUS_AVAILABLE = False

# 导入统一监控系统（如果可用）
try:
    from ..monitor.unified_monitor_system import (
        get_unified_monitor_manager, MonitorType as UnifiedMonitorType
    )
    UNIFIED_MONITOR_AVAILABLE = True
except ImportError:
    UNIFIED_MONITOR_AVAILABLE = False


class EventType(Enum):
    """事件类型枚举"""
    SYSTEM = "system"
    TASK = "task"
    ROBOT = "robot"
    SKILL = "skill"
    OBJECT = "object"
    GOAL = "goal"
    CONFIG = "config"
    MONITOR = "monitor"
    ERROR = "error"
    SCENE_ENTITY = "scene_entity"
    SCENE_BATCH = "scene_batch"


@dataclass
class Event(ABC):
    """事件基类
    
    所有事件都应该继承此基类，并实现event_type属性。
    
    Attributes:
        event_id: 事件唯一标识符
        timestamp: 事件时间戳
        source: 事件来源
    """
    
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None
    
    @property
    @abstractmethod
    def event_type(self) -> str:
        """事件类型
        
        Returns:
            事件类型字符串
        """
        pass


@dataclass
class SystemEvent(Event):
    """系统事件
    
    用于系统级别的事件通知，如启动、停止、配置变更等。
    
    Attributes:
        message: 事件消息
        data: 事件数据
    """
    
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def event_type(self) -> str:
        return EventType.SYSTEM.value


@dataclass
class TaskEvent(Event):
    """任务事件
    
    用于任务相关的事件通知，如任务创建、开始、完成、失败等。
    
    Attributes:
        task_id: 任务ID
        action: 动作类型 (created, started, completed, failed, cancelled)
        data: 事件数据
    """
    
    task_id: str = ""
    action: str = ""  # created, started, completed, failed, cancelled
    data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def event_type(self) -> str:
        return EventType.TASK.value


@dataclass
class RobotEvent(Event):
    """机器人事件
    
    用于机器人相关的事件通知，如状态变更、任务分配、技能执行等。
    
    Attributes:
        robot_id: 机器人ID
        action: 动作类型 (status_changed, task_assigned, skill_executed)
        data: 事件数据
    """
    
    robot_id: str = ""
    action: str = ""  # status_changed, task_assigned, skill_executed
    data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def event_type(self) -> str:
        return EventType.ROBOT.value


@dataclass
class SkillEvent(Event):
    """技能事件
    
    用于技能执行相关的事件通知。
    
    Attributes:
        skill_name: 技能名称
        robot_id: 执行技能的机器人ID
        action: 动作类型 (started, completed, failed)
        data: 事件数据
    """
    
    skill_name: str = ""
    robot_id: str = ""
    action: str = ""  # started, completed, failed
    data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def event_type(self) -> str:
        return EventType.SKILL.value


@dataclass
class ObjectEvent(Event):
    """对象事件
    
    用于对象相关的事件通知，如对象添加、移除、更新等。
    
    Attributes:
        object_id: 对象ID
        action: 动作类型 (added, removed, updated)
        data: 事件数据
    """
    
    object_id: str = ""
    action: str = ""  # added, removed, updated
    data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def event_type(self) -> str:
        return EventType.OBJECT.value


@dataclass
class GoalEvent(Event):
    """目标事件
    
    用于目标相关的事件通知，如目标更新、完成、移除等。
    
    Attributes:
        goal_id: 目标ID
        action: 动作类型 (updated, completed, removed)
        data: 事件数据
    """
    
    goal_id: str = ""
    action: str = ""  # updated, completed, removed
    data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def event_type(self) -> str:
        return EventType.GOAL.value


@dataclass
class ConfigEvent(Event):
    """配置事件
    
    用于配置变更相关的事件通知。
    
    Attributes:
        config_key: 配置键
        action: 动作类型 (updated, added, removed)
        old_value: 旧值
        new_value: 新值
        data: 事件数据
    """
    
    config_key: str = ""
    action: str = ""  # updated, added, removed
    old_value: Any = None
    new_value: Any = None
    data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def event_type(self) -> str:
        return EventType.CONFIG.value


@dataclass
class SceneEntityEvent(Event):
    """场景实体事件
    
    用于场景中实体（building、prop、robot、goal）的增删改查事件通知。
    
    Attributes:
        entity_id: 实体ID
        entity_type: 实体类型 (building, prop, robot, goal)
        entity_label: 实体标签/名称
        action: 动作类型 (added, updated, removed, state_changed)
        old_data: 旧数据
        new_data: 新数据
        position: 实体位置信息
        metadata: 额外元数据
    """
    
    entity_id: str = ""
    entity_type: str = ""  # building, prop, robot, goal
    entity_label: str = ""
    action: str = ""  # added, updated, removed, state_changed
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    position: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def event_type(self) -> str:
        return EventType.SCENE_ENTITY.value


@dataclass
class SceneBatchEvent(Event):
    """场景批量操作事件
    
    用于场景中多个实体的批量操作事件通知。
    
    Attributes:
        operation_id: 操作ID
        operation_type: 操作类型 (batch_add, batch_update, batch_remove)
        entity_changes: 实体变更列表
        summary: 操作摘要
    """
    
    operation_id: str = ""
    operation_type: str = ""  # batch_add, batch_update, batch_remove
    entity_changes: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    
    @property
    def event_type(self) -> str:
        return EventType.SCENE_BATCH.value


@dataclass
class MonitorEvent(Event):
    """监控事件
    
    用于监控系统生成的自然语言描述事件。
    
    Attributes:
        monitor_id: 监控器ID
        description_type: 描述类型 (scene_update, entity_change, system_status)
        natural_language_description: 自然语言描述
        related_entities: 相关实体列表
        severity: 严重程度 (info, warning, error)
        context: 上下文信息
    """
    
    monitor_id: str = ""
    description_type: str = ""  # scene_update, entity_change, system_status
    natural_language_description: str = ""
    related_entities: List[str] = field(default_factory=list)
    severity: str = "info"  # info, warning, error
    context: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def event_type(self) -> str:
        return EventType.MONITOR.value


# 事件处理器类型定义
EventHandler = Callable[[Event], None]
AsyncEventHandler = Callable[[Event], asyncio.Future]


class EventSubscription:
    """事件订阅
    
    管理单个事件订阅的信息和处理逻辑。
    """
    
    def __init__(self, 
                 event_type: str,
                 handler: Union[EventHandler, AsyncEventHandler],
                 subscriber_id: str,
                 filter_func: Optional[Callable[[Event], bool]] = None,
                 priority: int = 0,
                 max_retries: int = 0,
                 retry_delay: float = 1.0):
        """初始化事件订阅
        
        Args:
            event_type: 事件类型
            handler: 事件处理器
            subscriber_id: 订阅者ID
            filter_func: 事件过滤函数
            priority: 优先级（数字越大优先级越高）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.event_type = event_type
        self.handler = handler
        self.subscriber_id = subscriber_id
        self.filter_func = filter_func
        self.priority = priority
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.subscription_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.call_count = 0
        self.error_count = 0
        self.last_called = None
        self.last_error = None
    
    async def handle_event(self, event: Event) -> None:
        """处理事件（带重试机制）
        
        Args:
            event: 要处理的事件
        """
        retries = 0
        
        while retries <= self.max_retries:
            try:
                self.call_count += 1
                self.last_called = datetime.now()
                
                if asyncio.iscoroutinefunction(self.handler):
                    await self.handler(event)
                else:
                    # 在线程池中运行同步处理器
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.handler, event)
                
                # 成功处理，退出重试循环
                break
                
            except Exception as e:
                self.error_count += 1
                self.last_error = str(e)
                
                if retries < self.max_retries:
                    retries += 1
                    logger.warning(
                        f"Handler {self.subscription_id} failed (attempt {retries}/{self.max_retries + 1}): {e}"
                    )
                    await asyncio.sleep(self.retry_delay * retries)  # 指数退避
                else:
                    logger.error(
                        f"Handler {self.subscription_id} failed after {self.max_retries + 1} attempts: {e}",
                        exc_info=True
                    )
                    raise
    
    def matches(self, event: Event) -> bool:
        """检查事件是否匹配订阅
        
        Args:
            event: 要检查的事件
            
        Returns:
            是否匹配
        """
        if event.event_type != self.event_type:
            return False
        
        if self.filter_func and not self.filter_func(event):
            return False
        
        return True


class EventBus:
    """事件总线
    
    提供异步事件发布和订阅机制，支持事件过滤、历史记录和统计信息。
    """
    
    def __init__(self, max_queue_size: int = 1000, max_concurrent_handlers: int = 100):
        """初始化事件总线
        
        Args:
            max_queue_size: 事件队列最大大小
            max_concurrent_handlers: 最大并发处理器数量
        """
        self.max_queue_size = max_queue_size
        self.max_concurrent_handlers = max_concurrent_handlers
        self.event_queue = asyncio.Queue(maxsize=max_queue_size)
        self.subscriptions: Dict[str, List[EventSubscription]] = defaultdict(list)
        self.event_history = deque(maxlen=1000)
        
        # 添加信号量来控制并发处理器数量
        self._handler_semaphore = asyncio.Semaphore(max_concurrent_handlers)
        
        self.running = False
        self.processor_task: Optional[asyncio.Task] = None
        
        # 增强的统计信息
        self.stats = {
            'events_published': 0,
            'events_processed': 0,
            'events_failed': 0,
            'active_subscriptions': 0,
            'handler_timeouts': 0,
            'queue_overflows': 0
        }
        
        # 添加性能监控
        self._processing_times: deque = deque(maxlen=100)
        self._last_health_check = datetime.now()
    
    async def _handle_event_with_timeout(self, event: Event, timeout: float = 30.0) -> None:
        """带超时的事件处理
        
        Args:
            event: 要处理的事件
            timeout: 处理超时时间（秒）
        """
        start_time = datetime.now()
        
        try:
            # 添加到历史记录
            self.event_history.append(event)
            
            # 获取匹配的订阅
            matching_subscriptions = []
            for subscription in self.subscriptions.get(event.event_type, []):
                if subscription.matches(event):
                    matching_subscriptions.append(subscription)
            
            # 使用信号量控制并发处理
            if matching_subscriptions:
                async def handle_with_semaphore(subscription: EventSubscription) -> None:
                    async with self._handler_semaphore:
                        try:
                            await asyncio.wait_for(
                                subscription.handle_event(event), 
                                timeout=timeout
                            )
                        except asyncio.TimeoutError:
                            logger.warning(
                                f"Handler timeout for subscription {subscription.subscription_id}"
                            )
                            self.stats['handler_timeouts'] += 1
                        except Exception as e:
                            logger.error(
                                f"Handler error for subscription {subscription.subscription_id}: {e}",
                                exc_info=True
                            )
                
                # 并发处理所有匹配的订阅
                tasks = [
                    handle_with_semaphore(subscription)
                    for subscription in matching_subscriptions
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # 记录处理时间
            processing_time = (datetime.now() - start_time).total_seconds()
            self._processing_times.append(processing_time)
            
            self.stats['events_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error handling event {event.event_id}: {e}", exc_info=True)
            self.stats['events_failed'] += 1
    
    async def publish_batch(self, events: List[Event]) -> None:
        """批量发布事件
        
        Args:
            events: 要发布的事件列表
        """
        if not self.running:
            logger.warning("Event bus not running, events ignored")
            return
        
        successful = 0
        failed = 0
        
        for event in events:
            try:
                await self.event_queue.put(event)
                successful += 1
            except asyncio.QueueFull:
                logger.error(f"Event queue full, dropping event {event.event_id}")
                failed += 1
                self.stats['queue_overflows'] += 1
        
        self.stats['events_published'] += successful
        self.stats['events_failed'] += failed
        
        logger.debug(f"Batch published: {successful} successful, {failed} failed")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标
        
        Returns:
            性能指标字典
        """
        if self._processing_times:
            avg_processing_time = sum(self._processing_times) / len(self._processing_times)
            max_processing_time = max(self._processing_times)
            min_processing_time = min(self._processing_times)
        else:
            avg_processing_time = max_processing_time = min_processing_time = 0
        
        return {
            'average_processing_time': avg_processing_time,
            'max_processing_time': max_processing_time,
            'min_processing_time': min_processing_time,
            'active_handlers': self.max_concurrent_handlers - self._handler_semaphore._value,
            'queue_utilization': self.event_queue.qsize() / self.max_queue_size,
            'last_health_check': self._last_health_check.isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查
        
        Returns:
            健康状态字典
        """
        self._last_health_check = datetime.now()
        
        health_status = {
            'status': 'healthy' if self.running else 'stopped',
            'queue_size': self.event_queue.qsize(),
            'queue_capacity': self.max_queue_size,
            'active_subscriptions': self.stats['active_subscriptions'],
            'processor_running': self.processor_task is not None and not self.processor_task.done(),
            'performance_metrics': self.get_performance_metrics()
        }
        
        # 检查队列是否接近满载
        if self.event_queue.qsize() > self.max_queue_size * 0.8:
            health_status['warnings'] = ['Queue utilization high']
        
        # 检查是否有过多的超时
        if self.stats['handler_timeouts'] > 10:
            health_status.setdefault('warnings', []).append('High handler timeout rate')
        
        return health_status
    
    async def start(self) -> None:
        """启动事件总线"""
        if self.running:
            return
        
        self.running = True
        self.processor_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")
    
    async def stop(self) -> None:
        """停止事件总线"""
        if not self.running:
            return
        
        self.running = False
        
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Event bus stopped")
    
    def subscribe(self, 
                 event_type: str,
                 handler: Union[EventHandler, AsyncEventHandler],
                 subscriber_id: str,
                 filter_func: Optional[Callable[[Event], bool]] = None) -> str:
        """订阅事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理器
            subscriber_id: 订阅者ID
            filter_func: 事件过滤函数
            
        Returns:
            订阅ID
        """
        subscription = EventSubscription(event_type, handler, subscriber_id, filter_func)
        self.subscriptions[event_type].append(subscription)
        self.stats['active_subscriptions'] += 1
        
        logger.debug(f"Subscribed to {event_type}: {subscriber_id}")
        return subscription.subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅
        
        Args:
            subscription_id: 订阅ID
            
        Returns:
            是否成功取消
        """
        for event_type, subscriptions in self.subscriptions.items():
            for i, subscription in enumerate(subscriptions):
                if subscription.subscription_id == subscription_id:
                    del subscriptions[i]
                    self.stats['active_subscriptions'] -= 1
                    logger.debug(f"Unsubscribed: {subscription_id}")
                    return True
        
        return False
    
    def unsubscribe_all(self, subscriber_id: str) -> int:
        """取消指定订阅者的所有订阅
        
        Args:
            subscriber_id: 订阅者ID
            
        Returns:
            取消的订阅数量
        """
        count = 0
        for event_type, subscriptions in self.subscriptions.items():
            original_count = len(subscriptions)
            subscriptions[:] = [
                sub for sub in subscriptions 
                if sub.subscriber_id != subscriber_id
            ]
            removed = original_count - len(subscriptions)
            count += removed
            self.stats['active_subscriptions'] -= removed
        
        if count > 0:
            logger.debug(f"Unsubscribed all for {subscriber_id}: {count} subscriptions")
        
        return count
    
    async def publish(self, event: Event) -> None:
        """发布事件
        
        Args:
            event: 要发布的事件
        """
        if not self.running:
            logger.warning("Event bus not running, event ignored")
            return
        
        try:
            await self.event_queue.put(event)
            self.stats['events_published'] += 1
            logger.debug(f"Event published: {event.event_type} - {event.event_id}")
            
        except asyncio.QueueFull:
            logger.error("Event queue full, dropping event")
            self.stats['events_failed'] += 1
    
    async def publish_sync(self, event: Event) -> None:
        """同步发布事件（立即处理）
        
        Args:
            event: 要发布的事件
        """
        await self._handle_event(event)
    
    async def _process_events(self) -> None:
        """事件处理循环"""
        while self.running:
            try:
                # 等待事件，带超时
                event = await asyncio.wait_for(
                    self.event_queue.get(), timeout=1.0
                )
                
                await self._handle_event(event)
                
            except asyncio.TimeoutError:
                # 超时是正常的，继续循环
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)
                self.stats['events_failed'] += 1
    
    async def _handle_event(self, event: Event) -> None:
        """处理单个事件
        
        Args:
            event: 要处理的事件
        """
        try:
            # 添加到历史记录
            self.event_history.append(event)
            
            # 获取匹配的订阅
            matching_subscriptions = []
            for subscription in self.subscriptions.get(event.event_type, []):
                if subscription.matches(event):
                    matching_subscriptions.append(subscription)
            
            # 并发处理所有匹配的订阅
            if matching_subscriptions:
                tasks = [
                    subscription.handle_event(event)
                    for subscription in matching_subscriptions
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
            
            self.stats['events_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error handling event {event.event_id}: {e}", exc_info=True)
            self.stats['events_failed'] += 1
    
    def get_event_history(self, 
                         event_type: Optional[str] = None,
                         limit: int = 100) -> List[Event]:
        """获取事件历史
        
        Args:
            event_type: 事件类型过滤
            limit: 返回数量限制
            
        Returns:
            事件列表
        """
        events = list(self.event_history)
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            **self.stats,
            'queue_size': self.event_queue.qsize(),
            'history_size': len(self.event_history),
            'subscription_types': list(self.subscriptions.keys())
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息（别名）
        
        Returns:
            统计信息字典
        """
        return self.get_statistics()
    
    def clear_history(self) -> None:
        """清空事件历史"""
        self.event_history.clear()
        logger.info("Event history cleared")


def get_global_event_bus() -> EventBus:
    """获取全局事件总线实例
    
    Returns:
        全局事件总线实例
    """
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def set_global_event_bus(event_bus: EventBus) -> None:
    """设置全局事件总线实例
    
    Args:
        event_bus: 事件总线实例
    """
    global _global_event_bus
    _global_event_bus = event_bus


async def start_global_event_bus() -> None:
    """启动全局事件总线"""
    event_bus = get_global_event_bus()
    await event_bus.start()


async def stop_global_event_bus() -> None:
    """停止全局事件总线"""
    event_bus = get_global_event_bus()
    await event_bus.stop()


async def publish_event(event: Event) -> None:
    """发布事件到全局事件总线
    
    Args:
        event: 要发布的事件
    """
    event_bus = get_global_event_bus()
    await event_bus.publish(event)


def subscribe_event(event_type: str,
                   handler: Union[EventHandler, AsyncEventHandler],
                   subscriber_id: str,
                   filter_func: Optional[Callable[[Event], bool]] = None) -> str:
    """订阅全局事件总线的事件
    
    Args:
        event_type: 事件类型
        handler: 事件处理器
        subscriber_id: 订阅者ID
        filter_func: 事件过滤函数
        
    Returns:
        订阅ID
    """
    event_bus = get_global_event_bus()
    return event_bus.subscribe(event_type, handler, subscriber_id, filter_func)


def unsubscribe_event(subscription_id: str) -> bool:
    """取消订阅全局事件总线的事件
    
    Args:
        subscription_id: 订阅ID
        
    Returns:
        是否成功取消
    """
    event_bus = get_global_event_bus()
    return event_bus.unsubscribe(subscription_id)


# Enhanced Event Bus Bridge Functions
def use_enhanced_event_bus() -> bool:
    """Check if enhanced event bus is available and recommended
    
    Returns:
        True if enhanced event bus should be used
    """
    return ENHANCED_EVENT_BUS_AVAILABLE


def get_recommended_event_bus():
    """Get the recommended event bus (enhanced if available, otherwise standard)
    
    Returns:
        Event bus instance
    """
    if ENHANCED_EVENT_BUS_AVAILABLE:
        return get_enhanced_event_bus()
    else:
        return get_global_event_bus()


async def publish_event_enhanced_compatible(event) -> None:
    """Publish event with enhanced compatibility
    
    This function can handle both standard Event and EnhancedEvent objects.
    
    Args:
        event: Event to publish (Event or EnhancedEvent)
    """
    if ENHANCED_EVENT_BUS_AVAILABLE and hasattr(event, 'target_monitors'):
        # This is an enhanced event
        from .enhanced_event_bus import publish_enhanced_event
        await publish_enhanced_event(event)
    else:
        # This is a standard event or enhanced bus not available
        event_bus = get_global_event_bus()
        await event_bus.publish(event)


def create_bridge_event(event_type: str, 
                       data: dict, 
                       source: str = None,
                       priority: str = "normal") -> 'Event':
    """Create a bridge event that works with both systems
    
    Args:
        event_type: Type of event
        data: Event data
        source: Event source
        priority: Event priority ("low", "normal", "high", "critical")
        
    Returns:
        Event object compatible with current system
    """
    if ENHANCED_EVENT_BUS_AVAILABLE:
        # Create enhanced event based on type
        from .event_bus import (
            SystemDebugEvent, UserInterfaceEvent, SceneChangeEvent,
            SkillExecutionEvent, RobotStateChangeEvent, TaskProgressEvent,
            EventPriority
        )
        
        # Map priority string to enum
        priority_map = {
            "low": EventPriority.LOW,
            "normal": EventPriority.NORMAL,
            "high": EventPriority.HIGH,
            "critical": EventPriority.CRITICAL
        }
        event_priority = priority_map.get(priority, EventPriority.NORMAL)
        
        # Create appropriate enhanced event type
        if event_type.startswith("system") or event_type.startswith("debug"):
            return SystemDebugEvent(
                source=source,
                component=data.get("component", "unknown"),
                operation=data.get("operation", "unknown"),
                details=data.get("details", {}),
                priority=event_priority
            )
        elif event_type.startswith("user") or event_type.startswith("ui"):
            return UserInterfaceEvent(
                source=source,
                title=data.get("title", "Notification"),
                message=data.get("message", ""),
                icon=data.get("icon", "info"),
                priority=event_priority
            )
        elif event_type.startswith("scene") or event_type.startswith("environment"):
            return SceneChangeEvent(
                source=source,
                scene_id=data.get("scene_id", "unknown"),
                change_type=data.get("change_type", "unknown"),
                affected_objects=data.get("affected_objects", []),
                priority=event_priority
            )
        elif event_type.startswith("skill"):
            return SkillExecutionEvent(
                source=source,
                skill_name=data.get("skill_name", "unknown"),
                robot_id=data.get("robot_id", "unknown"),
                execution_status=data.get("status", "unknown"),
                priority=event_priority
            )
        elif event_type.startswith("robot"):
            return RobotStateChangeEvent(
                source=source,
                robot_id=data.get("robot_id", "unknown"),
                change_type=data.get("change_type", "unknown"),
                priority=event_priority
            )
        elif event_type.startswith("task"):
            return TaskProgressEvent(
                source=source,
                task_id=data.get("task_id", "unknown"),
                progress_type=data.get("progress_type", "unknown"),
                priority=event_priority
            )
    
    # Fallback to standard event
    if event_type in [e.value for e in EventType]:
        event_enum = EventType(event_type)
    else:
        event_enum = EventType.SYSTEM
    
    if event_enum == EventType.SYSTEM:
        return SystemEvent(message=data.get("message", ""), data=data, source=source)
    elif event_enum == EventType.TASK:
        return TaskEvent(
            task_id=data.get("task_id", ""),
            action=data.get("action", ""),
            data=data,
            source=source
        )
    elif event_enum == EventType.ROBOT:
        return RobotEvent(
            robot_id=data.get("robot_id", ""),
            action=data.get("action", ""),
            data=data,
            source=source
        )
    elif event_enum == EventType.SKILL:
        return SkillEvent(
            skill_name=data.get("skill_name", ""),
            robot_id=data.get("robot_id", ""),
            action=data.get("action", ""),
            data=data,
            source=source
        )
    else:
        return SystemEvent(message=str(data), data=data, source=source)


@dataclass
class SceneEntityEvent(Event):
    """场景实体事件
    
    用于场景中实体（building、prop、robot等）的变更通知。
    
    Attributes:
        entity_id: 实体ID
        entity_type: 实体类型 (building, prop, robot)
        entity_label: 实体标签
        action: 动作类型 (added, removed, updated, moved, state_changed)
        old_data: 变更前的数据
        new_data: 变更后的数据
        position: 实体位置信息
        affected_entities: 受影响的其他实体ID列表
    """
    
    entity_id: str = ""
    entity_type: str = ""  # building, prop, robot
    entity_label: str = ""
    action: str = ""  # added, removed, updated, moved, state_changed
    old_data: Dict[str, Any] = field(default_factory=dict)
    new_data: Dict[str, Any] = field(default_factory=dict)
    position: Optional[Dict[str, float]] = None
    affected_entities: List[str] = field(default_factory=list)
    
    @property
    def event_type(self) -> str:
        return EventType.SCENE_ENTITY.value


@dataclass
class SceneBatchEvent(Event):
    """场景批量变更事件
    
    用于批量场景变更的通知。
    
    Attributes:
        batch_id: 批量操作ID
        operation_type: 操作类型 (batch_add, batch_remove, batch_update)
        entities_count: 影响的实体数量
        entity_changes: 详细的实体变更列表
        validation_results: 验证结果
    """
    
    batch_id: str = ""
    operation_type: str = ""  # batch_add, batch_remove, batch_update
    entities_count: int = 0
    entity_changes: List[Dict[str, Any]] = field(default_factory=list)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def event_type(self) -> str:
        return EventType.SCENE_BATCH.value
