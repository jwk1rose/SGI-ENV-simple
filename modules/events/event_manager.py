"""全局事件管理器

提供全局事件总线的初始化、启动、停止和管理功能。
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from .event_bus import (
    EventBus, get_global_event_bus, set_global_event_bus,
    start_global_event_bus, stop_global_event_bus,
    Event, SystemEvent, EventType
)

logger = logging.getLogger(__name__)


class EventManager:
    """全局事件管理器
    
    负责管理全局事件总线的生命周期，提供统一的事件管理接口。
    """
    
    def __init__(self):
        """初始化事件管理器"""
        if hasattr(self, '_initialized'):
            return
        
        self._event_bus: Optional[EventBus] = None
        self._is_running = False
        self._startup_tasks: List[asyncio.Task] = []
        self._shutdown_tasks: List[asyncio.Task] = []
        self._health_monitor_task: Optional[asyncio.Task] = None
        self._health_check_interval = 60.0  # 60秒健康检查间隔
        self._initialized = True
        
        # 添加优雅关闭支持
        self._shutdown_event = asyncio.Event()
        self._shutdown_timeout = 30.0
        
        logger.info("EventManager initialized")
    
    async def start(self, 
                   max_queue_size: int = 1000, 
                   max_concurrent_handlers: int = 100,
                   enable_health_monitoring: bool = True) -> None:
        """启动事件管理器
        
        Args:
            max_queue_size: 事件队列最大大小
            max_concurrent_handlers: 最大并发处理器数量
            enable_health_monitoring: 是否启用健康监控
        """
        if self._is_running:
            logger.warning("EventManager is already running")
            return
        
        try:
            # 创建或获取事件总线
            if self._event_bus is None:
                self._event_bus = EventBus(
                    max_queue_size=max_queue_size,
                    max_concurrent_handlers=max_concurrent_handlers
                )
                set_global_event_bus(self._event_bus)
            
            # 启动事件总线
            await start_global_event_bus()
            self._is_running = True
            
            # 启动健康监控
            if enable_health_monitoring:
                self._health_monitor_task = asyncio.create_task(
                    self._health_monitor_loop()
                )
            
            # 执行启动任务
            if self._startup_tasks:
                startup_results = await asyncio.gather(
                    *self._startup_tasks, 
                    return_exceptions=True
                )
                
                # 检查启动任务结果
                for i, result in enumerate(startup_results):
                    if isinstance(result, Exception):
                        logger.error(f"Startup task {i} failed: {result}")
                
                self._startup_tasks.clear()
            
            # 发布系统启动事件
            await self._publish_system_event(
                "started", 
                "Event manager started successfully",
                {
                    "max_queue_size": max_queue_size,
                    "max_concurrent_handlers": max_concurrent_handlers,
                    "health_monitoring": enable_health_monitoring
                }
            )
            
            logger.info("EventManager started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start EventManager: {e}")
            self._is_running = False
            raise
    
    async def stop(self, timeout: Optional[float] = None) -> None:
        """优雅停止事件管理器
        
        Args:
            timeout: 停止超时时间（秒）
        """
        if not self._is_running:
            logger.warning("EventManager is not running")
            return
        
        stop_timeout = timeout or self._shutdown_timeout
        
        try:
            # 设置关闭事件
            self._shutdown_event.set()
            
            # 发布系统停止事件
            await self._publish_system_event(
                "stopping", 
                "Event manager is stopping"
            )
            
            # 停止健康监控
            if self._health_monitor_task:
                self._health_monitor_task.cancel()
                try:
                    await asyncio.wait_for(
                        self._health_monitor_task, 
                        timeout=5.0
                    )
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
                self._health_monitor_task = None
            
            # 等待所有启动任务完成
            if self._startup_tasks:
                await asyncio.wait_for(
                    asyncio.gather(*self._startup_tasks, return_exceptions=True),
                    timeout=stop_timeout / 2
                )
                self._startup_tasks.clear()
            
            # 执行关闭任务
            if self._shutdown_tasks:
                await asyncio.wait_for(
                    asyncio.gather(*self._shutdown_tasks, return_exceptions=True),
                    timeout=stop_timeout / 2
                )
                self._shutdown_tasks.clear()
            
            # 停止事件总线
            await stop_global_event_bus()
            self._is_running = False
            
            logger.info("EventManager stopped successfully")
            
        except asyncio.TimeoutError:
            logger.warning(f"EventManager stop timeout after {stop_timeout}s")
            self._is_running = False
        except Exception as e:
            logger.error(f"Failed to stop EventManager: {e}")
            self._is_running = False
            raise
        finally:
            self._shutdown_event.clear()
    
    async def _health_monitor_loop(self) -> None:
        """健康监控循环"""
        while self._is_running and not self._shutdown_event.is_set():
            try:
                if self._event_bus:
                    health_status = await self._event_bus.health_check()
                    
                    # 记录健康状态
                    if health_status.get('warnings'):
                        logger.warning(
                            f"Event bus health warnings: {health_status['warnings']}"
                        )
                    
                    # 如果状态不健康，发布警告事件
                    if health_status['status'] != 'healthy':
                        await self._publish_system_event(
                            "health_warning",
                            f"Event bus health status: {health_status['status']}",
                            health_status
                        )
                
                # 等待下次检查
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self._health_check_interval
                )
                
            except asyncio.TimeoutError:
                # 超时是正常的，继续下一次检查
                continue
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(self._health_check_interval)
    
    async def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态
        
        Returns:
            健康状态字典
        """
        if not self._event_bus:
            return {
                "status": "not_initialized",
                "is_running": self._is_running
            }
        
        return await self._event_bus.health_check()
    
    async def restart(self, max_queue_size: int = 1000) -> None:
        """重启事件管理器
        
        Args:
            max_queue_size: 事件队列最大大小
        """
        await self.stop()
        await self.start(max_queue_size)
    
    def is_running(self) -> bool:
        """检查事件管理器是否正在运行
        
        Returns:
            是否正在运行
        """
        return self._is_running
    
    def get_event_bus(self) -> Optional[EventBus]:
        """获取事件总线实例
        
        Returns:
            事件总线实例
        """
        return self._event_bus
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取事件管理器统计信息
        
        Returns:
            统计信息字典
        """
        if not self._event_bus:
            return {
                "is_running": self._is_running,
                "event_bus_available": False
            }
        
        stats = self._event_bus.get_statistics()
        stats.update({
            "is_running": self._is_running,
            "event_bus_available": True,
            "startup_tasks": len(self._startup_tasks),
            "shutdown_tasks": len(self._shutdown_tasks)
        })
        
        return stats
    
    def add_startup_task(self, coro) -> None:
        """添加启动任务
        
        Args:
            coro: 协程函数
        """
        if self._is_running:
            # 如果已经运行，立即执行任务
            task = asyncio.create_task(coro)
            self._startup_tasks.append(task)
        else:
            # 如果未运行，添加到启动任务列表
            self._startup_tasks.append(coro)
    
    def add_shutdown_task(self, coro) -> None:
        """添加关闭任务
        
        Args:
            coro: 协程函数
        """
        self._shutdown_tasks.append(coro)
    
    async def _publish_system_event(self, action: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """发布系统事件
        
        Args:
            action: 动作类型
            message: 事件消息
            data: 事件数据
        """
        try:
            if self._event_bus and self._event_bus.running:
                event = SystemEvent(
                    message=message,
                    source="event_manager",
                    data=data or {"action": action}
                )
                await self._event_bus.publish(event)
        except Exception as e:
            logger.error(f"Failed to publish system event: {e}")
    
    @asynccontextmanager
    async def managed_lifecycle(self, max_queue_size: int = 1000):
        """事件管理器生命周期上下文管理器
        
        Args:
            max_queue_size: 事件队列最大大小
        
        Usage:
            async with event_manager.managed_lifecycle():
                # 在这里使用事件总线
                pass
        """
        await self.start(max_queue_size)
        try:
            yield self
        finally:
            await self.stop()


# 全局事件管理器实例
_global_event_manager: Optional[EventManager] = None


def get_event_manager() -> EventManager:
    """获取全局事件管理器实例
    
    Returns:
        全局事件管理器实例
    """
    global _global_event_manager
    if _global_event_manager is None:
        _global_event_manager = EventManager()
    return _global_event_manager


async def start_event_system(max_queue_size: int = 1000) -> EventManager:
    """启动事件系统
    
    Args:
        max_queue_size: 事件队列最大大小
        
    Returns:
        事件管理器实例
    """
    manager = get_event_manager()
    await manager.start(max_queue_size)
    return manager


async def stop_event_system() -> None:
    """停止事件系统"""
    manager = get_event_manager()
    await manager.stop()


async def restart_event_system(max_queue_size: int = 1000) -> EventManager:
    """重启事件系统
    
    Args:
        max_queue_size: 事件队列最大大小
        
    Returns:
        事件管理器实例
    """
    manager = get_event_manager()
    await manager.restart(max_queue_size)
    return manager


def is_event_system_running() -> bool:
    """检查事件系统是否正在运行
    
    Returns:
        是否正在运行
    """
    manager = get_event_manager()
    return manager.is_running()


def get_event_system_statistics() -> Dict[str, Any]:
    """获取事件系统统计信息
    
    Returns:
        统计信息字典
    """
    manager = get_event_manager()
    return manager.get_statistics()


@asynccontextmanager
async def event_system_context(max_queue_size: int = 1000):
    """事件系统上下文管理器
    
    Args:
        max_queue_size: 事件队列最大大小
    
    Usage:
        async with event_system_context():
            # 在这里使用事件系统
            pass
    """
    manager = get_event_manager()
    async with manager.managed_lifecycle(max_queue_size):
        yield manager


# 便捷函数
async def publish_system_message(message: str, data: Optional[Dict[str, Any]] = None) -> None:
    """发布系统消息事件
    
    Args:
        message: 消息内容
        data: 事件数据
    """
    from .event_bus import publish_event
    
    event = SystemEvent(
        message=message,
        source="system",
        data=data or {}
    )
    await publish_event(event)


async def publish_system_error(error_message: str, error_data: Optional[Dict[str, Any]] = None) -> None:
    """发布系统错误事件
    
    Args:
        error_message: 错误消息
        error_data: 错误数据
    """
    await publish_system_message(
        f"System Error: {error_message}",
        {"error": True, "error_data": error_data or {}}
    )


async def publish_system_warning(warning_message: str, warning_data: Optional[Dict[str, Any]] = None) -> None:
    """发布系统警告事件
    
    Args:
        warning_message: 警告消息
        warning_data: 警告数据
    """
    await publish_system_message(
        f"System Warning: {warning_message}",
        {"warning": True, "warning_data": warning_data or {}}
    )


async def publish_system_info(info_message: str, info_data: Optional[Dict[str, Any]] = None) -> None:
    """发布系统信息事件
    
    Args:
        info_message: 信息消息
        info_data: 信息数据
    """
    await publish_system_message(
        f"System Info: {info_message}",
        {"info": True, "info_data": info_data or {}}
    )