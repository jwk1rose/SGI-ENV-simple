"""系统启动模块

提供系统初始化、事件总线启动、热重载配置等功能的统一入口。
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from modules.utils.event_manager import (
    get_event_manager, start_event_system, stop_event_system,
    publish_system_message, publish_system_error, publish_system_info
)
from .hot_reload import (
    get_hot_reloader, start_hot_reload, stop_hot_reload,
    ReloadConfig, add_reload_callback
)
from modules.utils.event_bus import subscribe_event, SystemEvent, ConfigEvent

logger = logging.getLogger(__name__)


@dataclass
class SystemConfig:
    """系统配置
    
    Attributes:
        project_root: 项目根目录
        config_paths: 配置文件路径列表
        module_paths: 模块路径列表
        enable_event_bus: 是否启用事件总线
        enable_hot_reload: 是否启用热重载
        event_queue_size: 事件队列大小
        reload_config: 热重载配置
        startup_callbacks: 启动回调函数列表
        shutdown_callbacks: 关闭回调函数列表
    """
    project_root: str = ""
    config_paths: List[str] = field(default_factory=list)
    module_paths: List[str] = field(default_factory=list)
    enable_event_bus: bool = True
    enable_hot_reload: bool = True
    event_queue_size: int = 1000
    reload_config: Optional[ReloadConfig] = None
    startup_callbacks: List[Callable] = field(default_factory=list)
    shutdown_callbacks: List[Callable] = field(default_factory=list)


class SystemManager:
    """系统管理器
    
    负责系统的启动、停止和管理。
    
    Attributes:
        config: 系统配置
        _is_running: 是否正在运行
        _startup_tasks: 启动任务列表
        _shutdown_tasks: 关闭任务列表
        _event_subscriptions: 事件订阅列表
    """
    
    def __init__(self, config: Optional[SystemConfig] = None):
        """初始化系统管理器
        
        Args:
            config: 系统配置
        """
        self.config = config or self._create_default_config()
        self._is_running = False
        self._startup_tasks: List[asyncio.Task] = []
        self._shutdown_tasks: List[asyncio.Task] = []
        self._event_subscriptions: List[str] = []
        
        logger.info("SystemManager initialized")
    
    def _create_default_config(self) -> SystemConfig:
        """创建默认配置
        
        Returns:
            默认系统配置
        """
        # 获取项目根目录
        current_dir = Path(__file__).parent
        project_root = str(current_dir.parent.parent)
        
        # 默认配置路径
        config_paths = [
            os.path.join(project_root, "config"),
            os.path.join(project_root, "configs"),
            os.path.join(project_root, "settings")
        ]
        
        # 默认模块路径
        module_paths = [
            os.path.join(project_root, "modules"),
            os.path.join(project_root, "src"),
            os.path.join(project_root, "lib")
        ]
        
        # 热重载配置
        reload_config = ReloadConfig(
            watch_paths=[
                project_root
            ],
            file_patterns=['*.py', '*.json', '*.yaml', '*.yml'],
            ignore_patterns=[
                '__pycache__', '*.pyc', '.git', '.DS_Store',
                'node_modules', '.venv', 'venv', '.env'
            ],
            reload_delay=1.0,
            enable_code_reload=True,
            enable_config_reload=True
        )
        
        return SystemConfig(
            project_root=project_root,
            config_paths=[p for p in config_paths if os.path.exists(p)],
            module_paths=[p for p in module_paths if os.path.exists(p)],
            reload_config=reload_config
        )
    
    async def start(self) -> None:
        """启动系统"""
        if self._is_running:
            logger.warning("SystemManager is already running")
            return
        
        try:
            logger.info("Starting system...")
            
            # 启动事件总线
            if self.config.enable_event_bus:
                await self._start_event_bus()
            
            # 设置事件订阅
            await self._setup_event_subscriptions()
            
            # 启动热重载
            if self.config.enable_hot_reload:
                await self._start_hot_reload()
            
            # 执行启动回调
            await self._execute_startup_callbacks()
            
            self._is_running = True
            
            # 发布系统启动事件
            await publish_system_info("System started successfully", {
                "project_root": self.config.project_root,
                "event_bus_enabled": self.config.enable_event_bus,
                "hot_reload_enabled": self.config.enable_hot_reload
            })
            
            logger.info("System started successfully")
            
        except Exception as e:
            error_msg = f"Failed to start system: {e}"
            logger.error(error_msg)
            await publish_system_error(error_msg, {"error": str(e)})
            raise
    
    async def stop(self) -> None:
        """停止系统"""
        if not self._is_running:
            logger.warning("SystemManager is not running")
            return
        
        try:
            logger.info("Stopping system...")
            
            # 发布系统停止事件
            await publish_system_info("System is stopping")
            
            # 执行关闭回调
            await self._execute_shutdown_callbacks()
            
            # 停止热重载
            if self.config.enable_hot_reload:
                await self._stop_hot_reload()
            
            # 清理事件订阅
            await self._cleanup_event_subscriptions()
            
            # 停止事件总线
            if self.config.enable_event_bus:
                await self._stop_event_bus()
            
            # 等待所有任务完成
            await self._wait_for_tasks()
            
            self._is_running = False
            
            logger.info("System stopped successfully")
            
        except Exception as e:
            error_msg = f"Failed to stop system: {e}"
            logger.error(error_msg)
            raise
    
    async def restart(self) -> None:
        """重启系统"""
        await self.stop()
        await self.start()
    
    async def _start_event_bus(self) -> None:
        """启动事件总线"""
        try:
            await start_event_system(self.config.event_queue_size)
            logger.info("Event bus started")
        except Exception as e:
            logger.error(f"Failed to start event bus: {e}")
            raise
    
    async def _stop_event_bus(self) -> None:
        """停止事件总线"""
        try:
            await stop_event_system()
            logger.info("Event bus stopped")
        except Exception as e:
            logger.error(f"Failed to stop event bus: {e}")
            raise
    
    async def _start_hot_reload(self) -> None:
        """启动热重载"""
        try:
            await start_hot_reload(self.config.reload_config)
            
            # 添加重载回调
            add_reload_callback(self._on_config_reload, 'config')
            add_reload_callback(self._on_code_reload, 'code')
            
            logger.info("Hot reload started")
        except Exception as e:
            logger.error(f"Failed to start hot reload: {e}")
            raise
    
    async def _stop_hot_reload(self) -> None:
        """停止热重载"""
        try:
            await stop_hot_reload()
            logger.info("Hot reload stopped")
        except Exception as e:
            logger.error(f"Failed to stop hot reload: {e}")
            raise
    
    async def _setup_event_subscriptions(self) -> None:
        """设置事件订阅"""
        try:
            # 订阅系统事件
            system_sub_id = await subscribe_event(
                SystemEvent,
                self._handle_system_event
            )
            self._event_subscriptions.append(system_sub_id)
            
            # 订阅配置事件
            config_sub_id = await subscribe_event(
                ConfigEvent,
                self._handle_config_event
            )
            self._event_subscriptions.append(config_sub_id)
            
            logger.debug("Event subscriptions set up")
            
        except Exception as e:
            logger.error(f"Failed to setup event subscriptions: {e}")
            raise
    
    async def _cleanup_event_subscriptions(self) -> None:
        """清理事件订阅"""
        try:
            from .event_bus import unsubscribe_event
            
            for sub_id in self._event_subscriptions:
                await unsubscribe_event(sub_id)
            
            self._event_subscriptions.clear()
            logger.debug("Event subscriptions cleaned up")
            
        except Exception as e:
            logger.error(f"Failed to cleanup event subscriptions: {e}")
    
    async def _execute_startup_callbacks(self) -> None:
        """执行启动回调"""
        for callback in self.config.startup_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Error in startup callback: {e}")
    
    async def _execute_shutdown_callbacks(self) -> None:
        """执行关闭回调"""
        for callback in self.config.shutdown_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Error in shutdown callback: {e}")
    
    async def _wait_for_tasks(self) -> None:
        """等待所有任务完成"""
        all_tasks = self._startup_tasks + self._shutdown_tasks
        if all_tasks:
            await asyncio.gather(*all_tasks, return_exceptions=True)
            self._startup_tasks.clear()
            self._shutdown_tasks.clear()
    
    async def _handle_system_event(self, event: SystemEvent) -> None:
        """处理系统事件
        
        Args:
            event: 系统事件
        """
        try:
            logger.debug(f"Received system event: {event.message}")
            
            # 根据事件类型执行相应操作
            if "error" in event.data:
                logger.error(f"System error event: {event.message}")
            elif "warning" in event.data:
                logger.warning(f"System warning event: {event.message}")
            else:
                logger.info(f"System event: {event.message}")
                
        except Exception as e:
            logger.error(f"Error handling system event: {e}")
    
    async def _handle_config_event(self, event: ConfigEvent) -> None:
        """处理配置事件
        
        Args:
            event: 配置事件
        """
        try:
            logger.info(f"Received config event: {event.config_type}")
            
            # 这里可以添加配置变更的处理逻辑
            # 例如：重新加载相关模块、更新系统设置等
            
        except Exception as e:
            logger.error(f"Error handling config event: {e}")
    
    async def _on_config_reload(self, file_path: str, config_data: Any) -> None:
        """配置重载回调
        
        Args:
            file_path: 文件路径
            config_data: 配置数据
        """
        try:
            logger.info(f"Config file reloaded: {file_path}")
            await publish_system_info(f"Configuration reloaded: {file_path}", {
                "file_path": file_path,
                "reload_type": "config"
            })
        except Exception as e:
            logger.error(f"Error in config reload callback: {e}")
    
    async def _on_code_reload(self, file_path: str, module_name: str) -> None:
        """代码重载回调
        
        Args:
            file_path: 文件路径
            module_name: 模块名
        """
        try:
            logger.info(f"Code module reloaded: {module_name}")
            await publish_system_info(f"Module reloaded: {module_name}", {
                "file_path": file_path,
                "module_name": module_name,
                "reload_type": "code"
            })
        except Exception as e:
            logger.error(f"Error in code reload callback: {e}")
    
    def add_startup_callback(self, callback: Callable) -> None:
        """添加启动回调
        
        Args:
            callback: 回调函数
        """
        self.config.startup_callbacks.append(callback)
    
    def add_shutdown_callback(self, callback: Callable) -> None:
        """添加关闭回调
        
        Args:
            callback: 回调函数
        """
        self.config.shutdown_callbacks.append(callback)
    
    def is_running(self) -> bool:
        """检查系统是否正在运行
        
        Returns:
            是否正在运行
        """
        return self._is_running
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取系统统计信息
        
        Returns:
            统计信息字典
        """
        from .event_manager import get_event_system_statistics
        from .hot_reload import get_reload_statistics
        
        stats = {
            "is_running": self._is_running,
            "project_root": self.config.project_root,
            "event_bus_enabled": self.config.enable_event_bus,
            "hot_reload_enabled": self.config.enable_hot_reload,
            "startup_callbacks": len(self.config.startup_callbacks),
            "shutdown_callbacks": len(self.config.shutdown_callbacks),
            "event_subscriptions": len(self._event_subscriptions)
        }
        
        if self.config.enable_event_bus:
            stats["event_bus"] = get_event_system_statistics()
        
        if self.config.enable_hot_reload:
            stats["hot_reload"] = get_reload_statistics()
        
        return stats


# 全局系统管理器实例
_global_system_manager: Optional[SystemManager] = None


def get_system_manager() -> SystemManager:
    """获取全局系统管理器实例
    
    Returns:
        全局系统管理器实例
    """
    global _global_system_manager
    if _global_system_manager is None:
        _global_system_manager = SystemManager()
    return _global_system_manager


async def start_system(config: Optional[SystemConfig] = None) -> SystemManager:
    """启动系统
    
    Args:
        config: 系统配置
        
    Returns:
        系统管理器实例
    """
    global _global_system_manager
    if config:
        _global_system_manager = SystemManager(config)
    else:
        _global_system_manager = get_system_manager()
    
    await _global_system_manager.start()
    return _global_system_manager


async def stop_system() -> None:
    """停止系统"""
    manager = get_system_manager()
    await manager.stop()


async def restart_system() -> SystemManager:
    """重启系统
    
    Returns:
        系统管理器实例
    """
    manager = get_system_manager()
    await manager.restart()
    return manager


def is_system_running() -> bool:
    """检查系统是否正在运行
    
    Returns:
        是否正在运行
    """
    manager = get_system_manager()
    return manager.is_running()


def get_system_statistics() -> Dict[str, Any]:
    """获取系统统计信息
    
    Returns:
        统计信息字典
    """
    manager = get_system_manager()
    return manager.get_statistics()


@asynccontextmanager
async def system_context(config: Optional[SystemConfig] = None):
    """系统上下文管理器
    
    Args:
        config: 系统配置
    
    Usage:
        async with system_context():
            # 在这里使用系统
            pass
    """
    manager = await start_system(config)
    try:
        yield manager
    finally:
        await stop_system()


# 便捷启动函数
async def quick_start(project_root: Optional[str] = None, 
                     enable_hot_reload: bool = True,
                     enable_event_bus: bool = True) -> SystemManager:
    """快速启动系统
    
    Args:
        project_root: 项目根目录
        enable_hot_reload: 是否启用热重载
        enable_event_bus: 是否启用事件总线
        
    Returns:
        系统管理器实例
    """
    config = SystemConfig(
        project_root=project_root or str(Path.cwd()),
        enable_hot_reload=enable_hot_reload,
        enable_event_bus=enable_event_bus
    )
    
    return await start_system(config)


if __name__ == "__main__":
    # 示例用法
    async def main():
        # 快速启动系统
        manager = await quick_start()
        
        try:
            # 系统运行中...
            await asyncio.sleep(10)
        finally:
            # 停止系统
            await stop_system()
    
    asyncio.run(main())