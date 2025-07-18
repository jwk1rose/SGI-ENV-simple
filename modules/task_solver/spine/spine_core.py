"""
SPINE核心类 - 空间规划智能导航引擎

集成LLM驱动的任务规划和场景理解功能，移植自原始spine.py
"""

import json
import logging
from collections import namedtuple
from datetime import datetime
from typing import Any, Dict, List, Tuple

import numpy as np

from .graph_handler import GraphHandler
from .spine_prompts import get_base_prompt_update_graph, INVALID_JSON

ValidPlanFeedback = namedtuple("ValidPlanFeedback", ["success", "message"])

# 定义有效动作集合
VALID_ACTIONS = set([
    "explore_region",
    "map_region", 
    "inspect",
    "clarify",
    "goto",
    "answer",
    "extend_map",
    "replan",
])

REGION_ACTIONS = set(["explore_region", "map_region", "goto"])
NAVIGATION_ACTIONS = set(["explore_region", "map_region", "goto", "inspect"])
INTERACTION_ACTIONS = set(["explore_region", "map_region", "goto", "inspect"])
OBJECT_ACTIONS = set(["inspect"])
SPATIAL_ACTION = set(["extend_map"])
EXPLORE_ACTIONS = set(["explore_region"])


class SPINE:
    """SPINE核心类 - 空间规划智能导航引擎"""
    
    def __init__(self, graph: GraphHandler, llm_model: str = "gpt-4o") -> None:
        """初始化SPINE
        
        Args:
            graph: 图处理器
            llm_model: LLM模型名称
        """
        self.graph = graph
        self.model = llm_model
        self.n_attempts = 3
        self.base_request = ""
        self.msg_history = []
        self.most_recent_query = []
        
        # 初始化LLM客户端
        self._init_llm_client()
        
        # 初始化日志
        self._init_logger()

    def _init_llm_client(self):
        """初始化LLM客户端"""
        try:
            # 使用您的LLM模块
            from modules.llm.modules.llm.gpt import GPT
            self.llm_client = GPT(model=self.model, memorize=True)
        except ImportError:
            # 如果导入失败，使用OpenAI客户端作为备选
            from openai import OpenAI
            self.llm_client = OpenAI()
            self.use_openai_fallback = True
        else:
            self.use_openai_fallback = False

    def _init_logger(self):
        """初始化日志"""
        now = datetime.now()
        self.logger = logging.getLogger("SPINE")
        self.logger.setLevel(logging.INFO)
        self.logger.disabled = True

    def clean_llm_output(self, s: str) -> str:
        """清理LLM输出"""
        return s.strip("```").strip("json")

    def clean_plan_argument(self, s: str) -> str:
        """清理计划参数，移除额外引号等"""
        return s.strip().strip("'").strip('"')

    def preprocess_cmd_str(self, cmd_list: str) -> List[str]:
        """预处理命令字符串"""
        if isinstance(cmd_list, str):
            cmd_list = cmd_list.strip("[").strip("]")
            cmd_list = cmd_list.split(",")

        if len(cmd_list) == 1:
            smoothed_cmds = cmd_list
        else:
            # 处理可能包含逗号的参数
            smoothed_cmds = []
            current_cmd = ""
            for cmd in cmd_list:
                if cmd.strip().startswith(tuple(VALID_ACTIONS)):
                    if len(current_cmd):
                        smoothed_cmds.append(current_cmd)
                        current_cmd = ""
                    current_cmd = cmd
                else:
                    current_cmd += f",{cmd}"

            if len(current_cmd):
                smoothed_cmds.append(current_cmd.strip())

        return smoothed_cmds

    def try_parse(self, response: str) -> Tuple[Dict[str, Any], ValidPlanFeedback]:
        """尝试解析LLM响应"""
        try:
            if not isinstance(response, str):
                self.logger.info(f"response is of type: {type(response)}")
                response = str(response)
            
            response = self.clean_llm_output(response)
            as_json = json.loads(response, strict=False)
            plan = self.preprocess_cmd_str(as_json["plan"])
            as_json["plan"] = plan
            return as_json, ValidPlanFeedback(True, "")
        except Exception as ex:
            return {}, ValidPlanFeedback(False, str(ex))

    def try_parse_region_arg(self, arg: str) -> Tuple[bool, np.ndarray]:
        """尝试解析区域参数"""
        try:
            parsed_arg = np.array([float(x) for x in arg.split(",")])
            return True, parsed_arg
        except:
            return False, arg

    def try_parse_exploration_arg(self, arg: str) -> Tuple[bool, Tuple[str, float]]:
        """尝试解析探索参数"""
        try:
            arg = arg.split(",")
            region = arg[0].strip()
            radius = float(arg[1].strip())
            return True, (region, radius)
        except:
            return False, (arg, arg)

    def try_parse_inspection_arg(self, arg: str) -> Tuple[bool, Tuple[str, str]]:
        """尝试解析检查参数"""
        try:
            arg = arg.split(",")
            object_name = arg[0].strip()
            query = "".join(arg[1:]).strip()
            return True, (object_name, query)
        except:
            return False, (arg, arg)

    async def query_llm(self, msg: List[Dict[str, str]]) -> Tuple[str, bool]:
        """查询LLM"""
        self.most_recent_query = msg
        try:
            if self.use_openai_fallback:
                # 使用OpenAI客户端
                response = self.llm_client.chat.completions.create(
                    model=self.model,
                    messages=msg,
                    temperature=0.05,
                    max_tokens=2048,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0,
                    response_format={"type": "json_object"},
                )
                top_msg = response.choices[0].message
                return top_msg.content, True
            else:
                # 使用您的LLM模块
                # 将消息列表转换为单个prompt字符串
                prompt = ""
                for message in msg:
                    if message["role"] == "system":
                        prompt += f"System: {message['content']}\n\n"
                    elif message["role"] == "user":
                        prompt += f"User: {message['content']}\n\n"
                    elif message["role"] == "assistant":
                        prompt += f"Assistant: {message['content']}\n\n"
                
                response = await self.llm_client.ask(prompt, temperature=0.05)
                return response, True
        except Exception as ex:
            print(f"got exception: {ex}")
            return "Error: network dropout", False

    def _try_parse_command(self, cmd: str) -> Tuple[Tuple[str, str], bool]:
        """尝试解析单个命令"""
        try:
            if cmd.startswith("answer"):
                function = "answer"
                arg = cmd[7:]
                arg = arg[:-1]
                arg = self.clean_plan_argument(arg)
                return (function, arg), True
            else:
                function, arg = cmd.split("(")
                function = function.strip()
                arg = arg.split(")")[0]
                arg = self.clean_plan_argument(arg)
                return (function, arg), True
        except ValueError as ex:
            return (), False

    def first_element_in_arg(self, arg: str) -> str:
        """获取参数的第一个元素"""
        if "," in arg:
            return arg.split(",")[0].strip()
        else:
            return arg

    def extract_plan(self, plan_as_str: List[str]) -> Tuple[List[Tuple[str, Any]], ValidPlanFeedback]:
        """提取并验证计划"""
        parsed_plan = []

        for step in plan_as_str:
            command, success = self._try_parse_command(step)
            if not success:
                return [], ValidPlanFeedback(
                    False, f"Could not parse step: {step} in plan."
                )
            function, arg = command

            # 导航函数需要第一个参数是区域
            first_arg = self.first_element_in_arg(arg)

            # 检查是否为有效函数
            if function not in VALID_ACTIONS:
                feedback = (
                    f"Feedback: {function} is not a valid command. You must use one of the "
                    f"following commands {list(VALID_ACTIONS)}. Update your plan accordingly."
                )
                return [], ValidPlanFeedback(False, feedback)

            # 检查参数是否在图中
            elif function in INTERACTION_ACTIONS and not self.graph.contains_node(first_arg):
                self.logger.info(
                    f"couldn't find node {first_arg} in graph: {self.graph.graph.nodes}"
                )
                feedback = (
                    f"Feedback: scene does not contain {first_arg}. "
                    f"All plans must reference nodes in the current scene. "
                    f"If your plan depends on potentially discovered regions or objects, consider using `replan()` as a placeholder. "
                    f"Update your plan accordingly."
                )
                return [], ValidPlanFeedback(False, feedback)

            # 检查导航路径是否存在
            elif (
                function in NAVIGATION_ACTIONS
                and not self.graph.path_exists_from_current_loc(first_arg)
            ):
                feedback = (
                    f"Feedback: No path from current location, {self.graph.current_location}, "
                    f"to goal {first_arg}. "
                )
                (
                    closest_reachable_node,
                    target_node,
                ) = self.graph.get_closest_reachable_node(goal_node=first_arg)
                feedback += (
                    f"The closest pair of nodes in the connected components of {self.graph.current_location} and {first_arg}"
                    f" are {closest_reachable_node} and {target_node}. "
                )
                feedback += (
                    f"If you find a connection between that pair via `extend_map()`, you can reach {first_arg}. If there is no connection, you will need to find another path. "
                    "Update your plan accordingly. Note that your relevant_map and long-term goals may stay the same."
                )
                return [], ValidPlanFeedback(False, feedback)

            # 检查导航命令参数是否为区域
            elif (
                function in REGION_ACTIONS
                and not self.graph.get_node_type(first_arg) == "region"
            ):
                node_type = self.graph.get_node_type(first_arg)
                assert node_type == "object", f"Must implement logic for {node_type}"
                feedback = (
                    "Feedback: Only region nodes can be given as arguments for navigation actions: "
                    f"{list(REGION_ACTIONS)}. Got {first_arg} of type {self.graph.get_node_type(first_arg)} for command {function}."
                    f" Consider using one of the following functions: {list(OBJECT_ACTIONS)}. The preceding part of your plan is valid. "
                    f"Update accordingly."
                )
                return [], ValidPlanFeedback(False, feedback)

            elif function in SPATIAL_ACTION and not self.try_parse_region_arg(arg)[0]:
                feedback = (
                    f"Feedback: the extend_map function takes in a coordinate in (x, y) numeric. "
                    f"Got exception when trying to parse {arg}. Update your plan accordingly."
                )
                return [], ValidPlanFeedback(False, feedback)
            elif (
                function in EXPLORE_ACTIONS
                and not self.try_parse_exploration_arg(arg)[0]
            ):
                feedback = (
                    f"Feedback: the explore_region function takes in a region name (str) and radius (float). "
                    f"Got exception when trying to parse {arg}. Update your plan accordingly."
                )
                return [], ValidPlanFeedback(False, feedback)
            elif (
                function in OBJECT_ACTIONS
                and not self.graph.get_node_type(first_arg) == "object"
            ):
                feedback = f"Feedback: inspect requires an object, but {first_arg} is a region. Try calling map_region({first_arg}) or explore_region({first_arg}, 3) to get information about the area, depending on the task"
                return [], ValidPlanFeedback(False, feedback)
            else:
                if function in SPATIAL_ACTION:
                    success, arg = self.try_parse_region_arg(arg)
                elif function in EXPLORE_ACTIONS:
                    success, arg = self.try_parse_exploration_arg(arg)
                elif function in OBJECT_ACTIONS:
                    success, arg = self.try_parse_inspection_arg(arg)

                parsed_plan.append((function, arg))

        return parsed_plan, ValidPlanFeedback(True, "Is valid plan")

    async def _generate_plan(
        self, msg: List[Dict[str, str]]
    ) -> Tuple[Dict[str, Any], bool, List[str]]:
        """生成计划"""
        response = {}
        success = False
        logs = []

        for _ in range(self.n_attempts):
            top_msg, could_query_llm = await self.query_llm(msg)

            if not could_query_llm:
                return {"msg": top_msg}, False, logs

            response, is_valid_json = self.try_parse(top_msg)

            if not is_valid_json.success:
                self.logger.info(
                    f"Not valid json. Got \n\t==\n\t{top_msg}\n"
                    f"=\n\twhich could not be parsed.\n\terror:{is_valid_json.message}.\n\t=="
                )
                msg.append({"role": "assistant", "content": top_msg})
                msg.append(
                    {
                        "role": "user",
                        "content": INVALID_JSON.format(is_valid_json.message),
                    }
                )
                logs.append(is_valid_json.message)
                logs.append(top_msg)
                continue

            plan, is_valid_plan = self.extract_plan(response["plan"])

            if not is_valid_plan.success:
                self.logger.info(
                    f"got: {response}\n\tnot valid plan: {is_valid_plan.message}"
                )
                msg.append({"role": "assistant", "content": top_msg})
                msg.append({"role": "user", "content": is_valid_plan.message})

                logs.append(top_msg)
                logs.append(is_valid_plan.message)

                print(logs[-1], logs[-2])
                continue

            if is_valid_json.success and is_valid_plan.success:
                success = True
                response["plan"] = plan
                break

        self.msg_history.append({"role": "assistant", "content": top_msg})

        return response, success, logs

    async def request(self, request: str) -> Tuple[Dict[str, Any], bool, List[str]]:
        """处理请求"""
        self.logger.info(f"Got Request: {request}")

        # 第一次请求
        if self.base_request == "":
            self.base_request = request
        else:
            current_request = {"role": "user", "content": request}
            self.msg_history.append(current_request)

        msg = (
            get_base_prompt_update_graph(
                request=self.base_request, scene_graph=self.graph.as_json_str
            )
            + self.msg_history
        )

        return await self._generate_plan(msg)

    async def resume_request(self) -> Tuple[Dict[str, Any], bool, List[str]]:
        """恢复请求"""
        assert len(self.most_recent_query), f"must have history to regenerate plan"
        return await self._generate_plan(self.most_recent_query)

    def clear_history(self) -> None:
        """清除历史"""
        self.msg_history = []

    def update(self, content: str) -> None:
        """更新内容"""
        msg = {"role": "user", "content": content}
        self.msg_history.append(msg) 