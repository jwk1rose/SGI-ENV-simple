from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

from modules.tasks.task_context import TaskContext
from modules.entities.skills import Skill
from modules.entities.robot.robot import Robot


class ExecutionStatus(Enum):
    """技能执行状态枚举"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"        # 执行失败
    SKIPPED = "skipped"      # 跳过执行

