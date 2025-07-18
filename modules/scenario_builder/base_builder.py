# file: base_scenario_builder.py

import json
import random
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

# 从我们的框架中导入实体库
from .entity_library import EntityTemplateLibrary


class BaseScenarioBuilder(ABC):
    """
    场景构建器的抽象基类。
    v2.0: 采用依赖注入模式，在初始化时接收一个实体模板库。

    它为所有具体的场景构建器提供了一套通用的核心功能和标准化的接口。
    其核心职责包括：
    - 接收一个模板库作为“零件”来源。
    - 管理和存储生成的节点(nodes)和关系(edges)。
    - 提供唯一的ID生成器和基础的随机布局策略。
    - 定义一个所有子类都必须实现的 `build()` 方法契约。
    """

    def __init__(self, bounds: Dict[str, float], template_library: EntityTemplateLibrary, start_id: int = 1):
        """
        初始化构建器基类。

        :param bounds: 一个描述世界边界的字典, e.g., {"x_min": 0, "x_max": 1000, ...}。
        :param template_library: 一个 EntityTemplateLibrary 的实例。
        :param start_id: 节点ID的起始编号。
        """
        if not all(k in bounds for k in ['x_min', 'x_max', 'y_min', 'y_max']):
            raise ValueError("Bounds dictionary is missing required keys.")

        self.bounds = bounds
        self.template_lib = template_library  # 存储传入的模板库实例
        self.nodes: List[Dict] = []
        self.edges: List[Dict] = []

        self._next_id = start_id
        self._placed_areas: List[Dict] = []

    def _get_unique_id(self) -> int:
        """获取并递增一个唯一的整数ID。"""
        uid = self._next_id
        self._next_id += 1
        return uid

    def _create_node_from_template(self, category: str, key: str, label: str, custom_props: Optional[Dict] = None) -> \
    Optional[Dict]:
        """
        **[新增]** 一个便利的辅助方法，用于从模板库创建并放置一个节点。

        这个方法封装了获取模板、分配ID、计算形状和位置的通用逻辑，
        极大地简化了子类的 `build` 方法。

        :param category: 实体的主类别 (e.g., 'building', 'robot').
        :param key: 该类别下的具体模板名 (e.g., 'hospital', 'drone').
        :param label: 实例的唯一人类可读标签.
        :param custom_props: (可选) 需要覆盖或添加到模板属性中的自定义属性。
        :return: 创建成功的节点字典，如果无法放置则返回 None。
        """
        try:
            template = self.template_lib.get_template(category, key)
        except KeyError as e:
            print(f"Error: {e}")
            return None

        width, height = template.get("size", template.get("shape_size", (1, 1)))
        shape = self._find_random_unoccupied_area(width, height)
        if not shape:
            return None  # 找不到放置位置

        node_id = self._get_unique_id()

        # 从模板复制基础属性，并添加唯一信息
        properties = template.copy()
        properties['label'] = label

        # 应用任何自定义或覆盖的属性
        if custom_props:
            properties.update(custom_props)

        node = {
            "id": node_id,
            "properties": properties,
            "shape": shape
        }
        self.nodes.append(node)
        return node

    def _find_random_unoccupied_area(self, width: float, height: float, max_attempts: int = 100) -> Optional[Dict]:
        """在世界中寻找一个随机的、不与现有实体重叠的矩形区域。"""
        for _ in range(max_attempts):
            x_min = random.uniform(self.bounds['x_min'], self.bounds['x_max'] - width)
            y_min = random.uniform(self.bounds['y_min'], self.bounds['y_max'] - height)
            x_max = x_min + width
            y_max = y_min + height
            new_area = {'x_min': x_min, 'x_max': x_max, 'y_min': y_min, 'y_max': y_max}
            is_overlapping = any(
                not (new_area['x_max'] < p['x_min'] or new_area['x_min'] > p['x_max'] or
                     new_area['y_max'] < p['y_min'] or new_area['y_min'] > p['y_max'])
                for p in self._placed_areas
            )
            if not is_overlapping:
                self._placed_areas.append(new_area)
                return {"type": "rectangle", "min_corner": [x_min, y_min], "max_corner": [x_max, y_max]}
        print(
            f"Warning: Could not find an unoccupied area for an object of size ({width}x{height}) after {max_attempts} attempts.")
        return None

    @abstractmethod
    def build(self) -> Dict[str, List[Dict]]:
        """**契约方法**: 构建场景的核心逻辑。子类必须实现此方法。"""
        raise NotImplementedError("Subclasses must implement the 'build' method.")

    def get_result(self) -> Dict[str, List[Dict]]:
        """获取当前已构建的场景数据。"""
        return {"nodes": self.nodes, "edges": self.edges}

    def save_to_file(self, filepath: str):
        """将最终生成的场景数据保存到JSON文件。"""
        scenario_data = self.get_result()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(scenario_data, f, indent=2, ensure_ascii=False)
        print(f"Scenario successfully saved to '{filepath}'")
