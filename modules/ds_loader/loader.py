import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def _read_json(path: Path) -> Any:
    """Helper function to read and parse a JSON file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to load JSON from {path}: {e}")


class DatasetLoader:
    """
    通用数据集加载器，自动检测并加载完整数据集结构。
    """
    def __init__(self, root: Path):
        self.root = Path(root)
        self.metadata = _read_json(self.root / "metadata.json")
        self.types = self._detect_types()
        self.goals = self._load_goals()
        self.scenarios = self._load_scenarios()
        # 在初始化时预加载所有任务
        self.tasks = self._load_tasks()

    def _detect_types(self) -> List[str]:
        """检测 goals 目录下的所有场景类型"""
        return [p.name for p in (self.root / "goals").iterdir() if p.is_dir()]

    def _load_goals(self) -> Dict[str, List[Dict[str, Any]]]:
        """加载不同类型的目标列表"""
        result: Dict[str, List[Dict[str, Any]]] = {}
        for t in self.types:
            file_path = self.root / "goals" / t / "goals.json"
            if file_path.exists():
                result[t] = _read_json(file_path)
        return result

    def _load_tasks(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        加载不同类型下的所有任务配置文件，并以高效的嵌套字典结构存储。
        如果任务的 JSON 内容中缺少 'scenario_id' 或 'goal_id'，
        会尝试从文件名 (格式如: task_urban_scenario_1_g1.json) 中解析。
        结构为: {type: {scenario_id: {goal_id: task_data}}}
        """
        result: Dict[str, Dict[str, Dict[str, Any]]] = {}
        tasks_base_dir = self.root / "tasks"

        for type_name in self.types:
            result[type_name] = {}
            type_dir = tasks_base_dir / type_name

            if not type_dir.is_dir():
                continue

            for task_file_path in sorted(type_dir.glob("*.json")):
                # 1. 读取 JSON 文件内容
                task_data = _read_json(task_file_path)

                # 2. 优先从 JSON 内容中获取 ID
                scenario_id = task_data.get("scenario")
                goal_id = task_data.get("goal").get("id")

                # 4. 再次检查，如果仍然缺少ID，则发出警告并跳过
                if not scenario_id or not goal_id:
                    print(
                        f"警告: 无法从内容或文件名 {task_file_path.name} 中确定 'scenario_id' 或 'goal_id'。已跳过此文件。")
                    continue

                # 5. 使用高效的嵌套字典结构存储任务
                if scenario_id not in result[type_name]:
                    result[type_name][scenario_id] = {}

                result[type_name][scenario_id][goal_id] = task_data

        return result


    def _load_scenarios(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """加载不同类型下的场景配置"""
        result: Dict[str, Dict[str, Dict[str, Any]]] = {}
        base_dir = self.root / "scenarios"
        for t in self.types:
            result[t] = {}
            type_dir = base_dir / t
            if not type_dir.is_dir():
                continue
            for d in sorted(type_dir.iterdir(), key=lambda p: p.name):
                if not d.is_dir():
                    continue
                data: Dict[str, Any] = {}
                for fname in ["environment_counts.json", "map_server_config.json"]:
                    fpath = d / fname
                    if fpath.exists():
                        data[fname.replace('.json', '')] = _read_json(fpath)
                result[t][d.name] = data
        return result


    def list_types(self) -> List[str]:
        """返回所有可用的场景类型"""
        return self.types

    def get_goals(self, type_name: str) -> List[Dict[str, Any]]:
        """获取指定类型的目标列表"""
        return self.goals.get(type_name, [])

    def list_scenarios(self, type_name: str) -> List[str]:
        """列出指定类型的所有场景 ID"""
        return list(self.scenarios.get(type_name, {}).keys())

    def get_scenario(self, type_name: str, scenario_id: str) -> Dict[str, Any]:
        """获取指定场景的详细配置"""
        scenario_data = self.scenarios.get(type_name, {}).get(str(scenario_id), {})
        
        # 如果场景数据包含map_server_config，直接返回它
        if "map_server_config" in scenario_data:
            return scenario_data["map_server_config"]
        
        # 否则返回原始数据
        return scenario_data

    def get_task(self, type_name: str, scenario_id: str, goal_id: str) -> Dict[str, Any]:
        """
        根据类型、场景ID和目标ID高效地从预加载的字典中检索任务。

        Args:
            type_name (str): 场景类型 (例如 "urban")。
            scenario_id (str): 场景 ID (例如 "scenario_1")。
            goal_id (str): 目标 ID (例如 "g1")。

        Returns:
            Dict[str, Any]: 包含任务定义的字典。如果找不到对应的任务，
                            则返回一个空的字典 `{}`。
        """
        return self.tasks.get(type_name, {}).get(str(scenario_id), {}).get(str(goal_id), {})

    def get_random_task(self, count: int = 1) -> List[Dict[str, Any]]:
        """
        随机获取指定数量的任务，默认返回一个任务。
        如果请求的数量超过可用任务数量，则返回所有可用任务。
        """
        all_tasks = []
        for type_name in self.types:
            for scenario_id, goals in self.tasks.get(type_name, {}).items():
                all_tasks.extend(goals.values())
        if count >= len(all_tasks):
            raise ValueError("请求的数量超过可用任务数量")
        return random.sample(all_tasks, count)




def load_dataset(root: Optional[str] = None) -> DatasetLoader:
    """
    便捷加载函数：加载数据集，默认加载包内 data/dataset
    """
    base = Path(root) if root else Path(__file__).parent.parent.parent / "dataset"
    return DatasetLoader(base)
