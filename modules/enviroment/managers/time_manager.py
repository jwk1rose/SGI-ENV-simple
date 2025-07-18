"""
时间管理器模块

负责管理模拟时间、时间倍率、时间更新循环等功能。
"""

import asyncio
import time
import logging
from typing import Callable, List

logger = logging.getLogger(__name__)


class TimeManager:
    """时间管理器"""
    
    def __init__(self, time_scale: float = 1.0):
        """
        初始化时间管理器
        
        Args:
            time_scale: 时间倍率，1.0表示正常速度，2.0表示2倍速
        """
        self.time_scale = time_scale
        self.sim_time = 0.0
        self.real_start_time = time.time()
        self.is_running = False
        
        # 时间更新回调
        self.time_update_callbacks: List[Callable[[float], None]] = []
    
    def get_sim_time(self) -> float:
        """获取当前模拟时间"""
        return self.sim_time
    
    def set_time_scale(self, time_scale: float):
        """设置时间倍率"""
        self.time_scale = time_scale
        logger.info(f"时间倍率已设置为: {time_scale}")
    
    def add_time_update_callback(self, callback: Callable[[float], None]):
        """添加时间更新回调"""
        self.time_update_callbacks.append(callback)
    
    async def start(self):
        """启动时间管理器"""
        self.is_running = True
        asyncio.create_task(self._time_update_loop())
        logger.info(f"时间管理器已启动，时间倍率: {self.time_scale}")
    
    async def stop(self):
        """停止时间管理器"""
        self.is_running = False
        logger.info("时间管理器已停止")
    
    async def _time_update_loop(self):
        """时间更新循环"""
        while self.is_running:
            try:
                # 更新模拟时间
                real_time = time.time() - self.real_start_time
                self.sim_time = real_time * self.time_scale
                
                for callback in self.time_update_callbacks:
                    try:
                        callback(self.sim_time)
                    except Exception as e:
                        logger.error(f"时间更新回调执行错误: {e}")
                
                await asyncio.sleep(0.1)  # 100ms更新间隔
            except Exception as e:
                logger.error(f"时间更新错误: {e}")
                await asyncio.sleep(1)
    
    def reset(self):
        """重置时间"""
        self.sim_time = 0.0
        self.real_start_time = time.time()
        logger.info("时间已重置") 