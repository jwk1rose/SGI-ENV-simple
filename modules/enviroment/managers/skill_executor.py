"""
集成现有技能系统的SkillExecutor

使用modules/entity/skill/中的完整技能实现，
而不是重新创建简化的技能执行逻辑。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from modules.entity.robot.robot import Robot
from modules.entity.skill.skill import Skill
from modules.utils.global_config import GlobalConfig, SkillNameMapping

logger = logging.getLogger(__name__)


class SkillStatus(Enum):
    """技能状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SkillExecution:
    """技能执行状态"""
    skill_id: str
    robot_id: Any
    skill_name: str
    start_time: float
    end_time: float
    duration: float
    status: SkillStatus
    params: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    progress: float = 0.0  # 执行进度 0.0-1.0


class SkillExecutor:
    """集成现有技能系统的执行器"""
    
    def __init__(self, robot_manager, time_manager, task_context):
        """
        初始化技能执行器
        
        Args:
            robot_manager: 机器人管理器
            time_manager: 时间管理器
            task_context: 任务上下文
        """
        self.robot_manager = robot_manager
        self.time_manager = time_manager
        self.task_context = task_context
        
        # 活动技能管理
        self.active_skills: Dict[str, SkillExecution] = {}
        self.skill_counter = 0
        
        # 回调系统
        self.skill_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # 执行状态
        self.is_running = False
    
    def register_skill_callback(self, skill_id: str, event_type: str, callback: Callable):
        """注册技能回调"""
        key = f"{skill_id}_{event_type}"
        self.skill_callbacks[key].append(callback)
    
    def unregister_skill_callback(self, skill_id: str, event_type: str, callback: Callable):
        """注销技能回调"""
        key = f"{skill_id}_{event_type}"
        if key in self.skill_callbacks and callback in self.skill_callbacks[key]:
            self.skill_callbacks[key].remove(callback)
    
    async def start(self):
        """启动技能执行器"""
        self.is_running = True
        asyncio.create_task(self._skill_execution_loop())
        logger.info("集成技能执行器已启动")
    
    async def stop(self):
        """停止技能执行器"""
        self.is_running = False
        logger.info("集成技能执行器已停止")
    
    async def execute_skill(self, robot_id: Any, skill_name: str, 
                          skill_params: Dict[str, Any] = None) -> str:
        """
        执行技能
        
        Args:
            robot_id: 机器人ID
            skill_name: 技能名称
            skill_params: 技能参数
            
        Returns:
            技能执行ID
        """
        skill_params = skill_params or {}
        
        # 验证技能名称
        if not GlobalConfig.validate_skill_name(skill_name):
            raise ValueError(f"无效的技能名称: {skill_name}")
        
        # 生成技能ID
        skill_id = f"skill_{self.skill_counter}_{robot_id}_{skill_name}"
        self.skill_counter += 1
        
        # 验证技能
        if not await self._validate_skill(robot_id, skill_name, skill_params):
            raise ValueError(f"技能验证失败: {robot_id} -> {skill_name}")
        
        # 计算技能持续时间
        duration = await self._calculate_skill_duration(robot_id, skill_name, skill_params)
        current_time = self.time_manager.get_sim_time()
        
        # 创建技能执行记录
        execution = SkillExecution(
            skill_id=skill_id,
            robot_id=robot_id,
            skill_name=skill_name,
            start_time=current_time,
            end_time=current_time + duration,
            duration=duration,
            status=SkillStatus.PENDING,
            params=skill_params
        )
        
        # 添加到活动技能
        self.active_skills[skill_id] = execution
        
        # 触发技能开始回调
        await self._trigger_skill_callbacks(skill_id, "started", execution)
        
        logger.info(f"技能已提交: {skill_id} ({robot_id} -> {skill_name}), 持续时间: {duration:.2f}s")
        return skill_id
    
    async def cancel_skill(self, skill_id: str) -> bool:
        """取消技能执行"""
        if skill_id not in self.active_skills:
            return False
        
        execution = self.active_skills[skill_id]
        execution.status = SkillStatus.CANCELLED
        
        # 从机器人的当前技能中移除
        await self.robot_manager.remove_skill_from_robot(execution.robot_id, skill_id)
        
        # 触发技能取消回调
        await self._trigger_skill_callbacks(skill_id, "cancelled", execution)
        
        logger.info(f"技能已取消: {skill_id}")
        return True
    
    async def get_skill_status(self, skill_id: str) -> Optional[SkillStatus]:
        """获取技能状态"""
        execution = self.active_skills.get(skill_id)
        return execution.status if execution else None
    
    async def get_skill_progress(self, skill_id: str) -> Optional[float]:
        """获取技能执行进度"""
        execution = self.active_skills.get(skill_id)
        if not execution:
            return None
        
        if execution.status == SkillStatus.COMPLETED:
            return 1.0
        elif execution.status == SkillStatus.RUNNING:
            current_time = self.time_manager.get_sim_time()
            elapsed = current_time - execution.start_time
            return min(elapsed / execution.duration, 1.0)
        else:
            return 0.0
    
    async def _validate_skill(self, robot_id: Any, skill_name: str, 
                            skill_params: Dict[str, Any]) -> bool:
        """验证技能"""
        robot = self.robot_manager.get_robot(robot_id)
        if not robot:
            return False
        
        # 使用全局配置验证技能名称
        if not GlobalConfig.validate_skill_name(skill_name):
            logger.warning(f"无效的技能名称: {skill_name}")
            return False
        
        # 检查技能是否存在（使用映射后的名称）
        actual_skill_name = SkillNameMapping.map_scene_to_actual(skill_name)
        if actual_skill_name not in robot.skills:
            logger.warning(f"机器人 {robot_id} 不支持技能: {skill_name} (映射后: {actual_skill_name})")
            return False
        
        # 检查机器人电量
        battery = robot.get_state('battery', 100.0)
        if battery < 5.0:  # 最小电量要求
            return False
        
        return True
    
    async def _calculate_skill_duration(self, robot_id: Any, skill_name: str, 
                                      skill_params: Dict[str, Any]) -> float:
        """计算技能持续时间"""
        # 基础持续时间
        base_duration = 2.0
        
        # 使用全局配置进行技能名称映射
        actual_skill_name = SkillNameMapping.map_scene_to_actual(skill_name)
        
        # 根据技能类型调整
        if actual_skill_name == "navigate":
            # 导航时间基于距离
            robot = self.robot_manager.get_robot(robot_id)
            if robot and 'target_position' in skill_params:
                current_pos = robot.get_state('position', {'x': 0, 'y': 0})
                target_pos = skill_params['target_position']
                distance = ((target_pos[0] - current_pos['x']) ** 2 + 
                           (target_pos[1] - current_pos['y']) ** 2) ** 0.5
                base_duration = max(1.0, distance / 5.0)  # 5m/s速度
        
        elif actual_skill_name == "take_photo":
            base_duration = 1.0
        
        elif actual_skill_name == "load_object":
            base_duration = 3.0
        
        elif actual_skill_name == "unload_object":
            base_duration = 3.0
        
        elif actual_skill_name in ["take_off", "land"]:
            base_duration = 2.0
        
        elif actual_skill_name in ["search_for_target", "identify_anomaly"]:
            base_duration = 4.0
        
        return base_duration
    
    async def _skill_execution_loop(self):
        """技能执行循环"""
        while self.is_running:
            try:
                await self._process_pending_skills()
                await self._update_running_skills()
                await self._cleanup_completed_skills()
                await asyncio.sleep(0.1)  # 100ms执行间隔
            except Exception as e:
                logger.error(f"技能执行循环错误: {e}")
                await asyncio.sleep(1)
    
    async def _process_pending_skills(self):
        """处理待执行的技能"""
        current_time = self.time_manager.get_sim_time()
        pending_skills = [
            skill for skill in self.active_skills.values()
            if skill.status == SkillStatus.PENDING and current_time >= skill.start_time
        ]
        
        for skill in pending_skills:
            await self._start_skill_execution(skill)
    
    async def _start_skill_execution(self, skill: SkillExecution):
        """开始技能执行"""
        robot = self.robot_manager.get_robot(skill.robot_id)
        if not robot:
            skill.status = SkillStatus.FAILED
            skill.error_message = "Robot not found"
            return
        
        # 为机器人添加技能
        await self.robot_manager.add_skill_to_robot(skill.robot_id, skill.skill_id)
        
        # 更新技能状态
        skill.status = SkillStatus.RUNNING
        
        logger.info(f"开始执行技能: {skill.skill_id}")
    
    async def _update_running_skills(self):
        """更新运行中的技能"""
        current_time = self.time_manager.get_sim_time()
        
        for skill in self.active_skills.values():
            if skill.status != SkillStatus.RUNNING:
                continue
            
            # 更新进度
            elapsed = current_time - skill.start_time
            skill.progress = min(elapsed / skill.duration, 1.0)
            
            # 检查是否完成
            if current_time >= skill.end_time:
                await self._complete_skill(skill)
    
    async def _complete_skill(self, skill: SkillExecution):
        """完成技能执行"""
        # 从机器人移除技能
        await self.robot_manager.remove_skill_from_robot(skill.robot_id, skill.skill_id)
        
        # 执行技能逻辑并获取结果
        skill_result = await self._execute_skill_logic(skill)
        
        # 更新技能状态
        skill.status = SkillStatus.COMPLETED
        skill.progress = 1.0
        skill.result = skill_result
        
        # 处理技能执行结果，更新TaskContext
        await self._handle_skill_result(skill)
        
        # 触发技能完成回调
        await self._trigger_skill_callbacks(skill.skill_id, "completed", skill)
        
        logger.info(f"技能执行完成: {skill.skill_id}")
    
    async def _execute_skill_logic(self, skill: SkillExecution) -> Dict[str, Any]:
        """执行技能逻辑 - 使用现有的技能系统"""
        robot = self.robot_manager.get_robot(skill.robot_id)
        if not robot:
            return {'success': False, 'error': 'Robot not found'}
        
        try:
            # 使用全局配置进行技能名称映射
            actual_skill_name = SkillNameMapping.map_scene_to_actual(skill.skill_name)
            
            # 检查技能是否存在
            if actual_skill_name not in robot.skills:
                return {'success': False, 'error': f'Skill {skill.skill_name} (映射后: {actual_skill_name}) not found'}
            
            # 获取技能实例
            skill_instance = robot.skills[actual_skill_name]
            
            # 使用现有技能系统的执行方法
            result = skill_instance.execute_with_logging(robot, **skill.params)
            
            logger.info(f"技能 {skill.skill_name} (映射后: {actual_skill_name}) 执行完成，结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"技能执行异常: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_skill_result(self, skill: SkillExecution):
        """处理技能执行结果，更新TaskContext"""
        if not skill.result or not skill.result.get('success'):
            return
        
        try:
            # 处理执行结果
            execution_result = skill.result.get('execution_result', {})
            effects_result = skill.result.get('effects_result', {})
            
            # 更新机器人状态
            robot_updates = {}
            
            # 处理位置变化
            if 'new_position' in execution_result:
                robot_updates['position'] = execution_result['new_position']
            
            # 处理电量消耗
            if 'battery_consumed' in effects_result:
                robot = self.robot_manager.get_robot(skill.robot_id)
                if robot:
                    current_battery = robot.get_state('battery', 100.0)
                    new_battery = max(0, current_battery - effects_result['battery_consumed'])
                    robot_updates['battery'] = new_battery
            
            # 处理状态变化
            if 'status_change' in effects_result:
                robot_updates['status'] = effects_result['status_change']
            
            # 更新TaskContext
            if robot_updates:
                self.task_context.update_object_properties(skill.robot_id, robot_updates)
            
            # 处理对象状态变化
            if 'object_updates' in execution_result:
                for obj_id, updates in execution_result['object_updates'].items():
                    self.task_context.update_object_properties(obj_id, updates)
            
            logger.debug(f"技能结果已处理: {skill.skill_id}")
            
        except Exception as e:
            logger.error(f"处理技能结果失败: {e}")
    
    async def _cleanup_completed_skills(self):
        """清理已完成的技能"""
        # 保留最近完成的技能用于查询，这里可以设置保留时间
        pass
    
    async def _trigger_skill_callbacks(self, skill_id: str, event_type: str, skill: SkillExecution):
        """触发技能回调"""
        key = f"{skill_id}_{event_type}"
        callbacks = self.skill_callbacks[key]
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(skill)
                else:
                    callback(skill)
            except Exception as e:
                logger.error(f"技能回调执行错误: {e}")
    
    def get_active_skills(self) -> Dict[str, SkillExecution]:
        """获取活动技能"""
        return self.active_skills.copy()
    
    def reset(self):
        """重置技能执行器"""
        self.active_skills.clear()


# 导出类
__all__ = ['SkillExecutor', 'SkillStatus', 'SkillExecution']
SkillExecutor = SkillExecutor 