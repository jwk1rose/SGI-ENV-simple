# 文件: modules/tasks/task_manager.py
import time
import logging
from enum import Enum, auto
from typing import Any, Dict, List, Optional

# --- 从项目的其他模块导入依赖 ---
from .task_context import TaskContext
from .workflow import Workflow, WorkflowResult
from ..env.task_env import IntegratedTaskEnv as TaskEnv
from modules.entities.goal import Goal, GoalFactory
from ..monitor.monitor import Monitor


class TaskStatus(Enum):
    """定义任务的生命周期状态。"""
    CREATED = auto()
    READY = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    ABORTED = auto()


class TaskManager:
    """
    任务管理器，作为顶层协调者，负责任务从初始化到完成的整个生命周期。
    它通过依赖注入接收所有必要的组件，并负责驱动它们。
    """

    def __init__(
            self,
            context: TaskContext,
            env: TaskEnv,
            workflow: Workflow,
            monitor: Monitor,
            goal_factory: GoalFactory,
            logger: logging.Logger,
    ):
        """
        通过依赖注入初始化管理器。

        Args:
            context: 包含任务静态配置的上下文对象。
            env: 任务执行的模拟环境。
            workflow: 负责执行核心任务逻辑的工作流引擎。
            monitor: 用于监控环境和任务状态的监控器。
            goal_factory: 用于根据配置创建具体 Goal 实例的工厂。
            logger: 用于记录日志的、已配置的 logger 实例。
        """
        self.logger = logger

        if not context.is_loaded() or not context.validate():
            self.logger.error("传入的 TaskContext 未加载或配置非法。")
            raise ValueError("Invalid TaskContext provided.")

        self.context = context
        self.env = env
        self.workflow = workflow
        self.monitor = monitor
        self.goal_factory = goal_factory

        # 运行时数据
        self.goal: Optional[Goal] = None
        self.status: TaskStatus = TaskStatus.CREATED
        self.task_graph: Optional[List[Dict]] = None
        self.error_message: Optional[str] = None

        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.total_duration: Optional[float] = None
        self.workflow_duration: Optional[float] = None

        self.logger.info(f"TaskManager created for task: {self.context.get_id()}")

    def setup(self):
        """
        根据 TaskContext 中的配置，准备所有运行时组件。
        这是执行任务前的必要步骤。
        """
        if self.status != TaskStatus.CREATED:
            self.logger.warning(f"Task already set up. Current status: {self.status.name}")
            return

        self.logger.info("Setting up task environment and components...")

        try:
            robots_config = self.context.get_robots_config()
            self.env.initialize(robots_config=robots_config)

            goal_config = self.context.get_goal_config()
            self.goal = self.goal_factory.create_goal(goal_config)

            self.monitor.start(self.env)

            self.status = TaskStatus.READY
            self.logger.info("Task setup complete. Manager is ready to execute.")
        except Exception as e:
            self.logger.exception("Failed to setup task.")
            self.status = TaskStatus.FAILED
            self.error_message = f"Setup failed: {e}"
            raise

    def execute(self):
        """
        执行已准备好的任务，主要通过驱动工作流（Workflow）来完成。
        """
        if self.status != TaskStatus.READY:
            self.logger.error(f"Cannot execute. Task is not ready. Current status: {self.status.name}")
            return

        self.logger.info("Executing task workflow...")
        self.status = TaskStatus.RUNNING
        self.start_time = time.time()

        try:
            workflow_start_time = time.time()
            result = self.workflow.execute(self.env, self.goal)
            self.workflow_duration = time.time() - workflow_start_time

            self._process_workflow_result(result)

        except Exception as e:
            self.logger.exception("Workflow execution failed.")
            self.status = TaskStatus.FAILED
            self.error_message = f"Execution failed: {e}"
        finally:
            self.end_time = time.time()
            self.total_duration = self.end_time - self.start_time
            self.monitor.stop()
            self.logger.info(f"Task execution finished. Final status: {self.status.name}")

    def _process_workflow_result(self, result: WorkflowResult):
        """私有方法，用于处理工作流返回的结果。"""
        self.task_graph = result.steps
        self.logger.info(f"Generated task graph with {len(self.task_graph)} steps from workflow result.")

        if result.status == "SUCCESS":
            self.status = TaskStatus.COMPLETED
        else:
            self.status = TaskStatus.FAILED
            self.error_message = result.message

    def reset(self):
        """重置管理器的运行时状态，以便可以重新执行。"""
        self.logger.info("Resetting TaskManager state.")
        self.goal = None
        self.status = TaskStatus.CREATED
        self.task_graph = None
        self.error_message = None
        self.start_time = None
        self.end_time = None
        self.total_duration = None
        self.workflow_duration = None

    def get_summary(self) -> Dict[str, Any]:
        """返回任务执行的详细摘要。"""
        return {
            "task_id": self.context.get_id(),
            "status": self.status.name,
            "total_duration_sec": self.total_duration,
            "workflow_duration_sec": self.workflow_duration,
            "error_message": self.error_message,
            "generated_task_graph": self.task_graph,
        }