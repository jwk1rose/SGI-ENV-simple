import numpy as np
import copy
from typing import Any, Dict, List, Tuple, Optional


class LayeredGridMap:
    """
    一个以对象为中心、接口明确的分层栅格地图管理器。

    该类旨在提供一个健壮的框架来管理一个多层栅格世界，其中的实体被视为具有一个或多个
    可独立寻址“部件”的“对象”。它提供了明确的增、删、改、查（CRUD）接口来管理这些
    对象的生命周期，并能在初始化时根据配置批量加载对象。
    """

    def __init__(self, config: Dict[str, Any]):
        """
        根据配置初始化地图的边界、分辨率、图层和初始对象。

        Args:
            config (Dict[str, Any]): 一个字典，必须包含以下键:
                - 'resolution' (float): 每个栅格单元代表的真实世界距离（米/单位）。
                - 'bounds' (Dict): 定义地图的世界坐标范围，包含 'x_min', 'x_max', 'y_min', 'y_max'。
                - 'layers_config' (Dict): 定义每个图层的属性，键为图层名。
                - 'initial_objects' (List[Dict], optional): 一个包含初始对象的列表。
        """
        required_keys = {'resolution', 'bounds', 'layers_config'}
        if not required_keys.issubset(config):
            raise ValueError(f"配置字典必须包含以下键: {required_keys}")

        # 保存原始配置以便能够重置到初始状态
        self._original_config = copy.deepcopy(config)

        self.resolution = config['resolution']
        self.bounds = config['bounds']
        self.layers_config = config['layers_config']
        initial_objects = config.get('initial_objects', [])

        self.width_in_cells = int(np.ceil((self.bounds['x_max'] - self.bounds['x_min']) / self.resolution))
        self.height_in_cells = int(np.ceil((self.bounds['y_max'] - self.bounds['y_min']) / self.resolution))

        self.layers: Dict[str, np.ndarray] = {}
        self._objects: Dict[Any, Dict[str, Any]] = {}

        self._init_empty_layers()
        self._populate_initial_objects(initial_objects)

    def reset(self, mode: str = 'full') -> None:
        """
        重置地图状态。

        Args:
            mode (str, optional): 重置模式。默认为 'full'。
                - 'full': 清空所有对象和图层数据，恢复到完全空白的状态。
                - 'initial': 恢复到 `__init__` 方法被调用时由配置定义的初始状态。
        """
        if mode not in {"initial", "full"}:
            raise ValueError("mode 必须是 'initial' 或 'full' 之一。")

        if mode == 'initial':
            # 使用保存的原始配置重新初始化
            self.__init__(self._original_config)
        else:  # full reset
            self._objects.clear()
            self.layers.clear()
            self._init_empty_layers()

    # --- 核心 CRUD API ---

    def add_object(self, obj_id: Any, parts_shapes: Dict[str, Dict], layer_type: str) -> None:
        """
        在地图上新增一个完整的对象。

        如果具有相同 obj_id 的对象已存在，将引发 ValueError。

        Args:
            obj_id (Any): 对象的唯一标识符。
            parts_shapes (Dict[str, Dict]): 描述对象各个部件形状的字典。
            layer_type (str): 对象所属的物理图层类型 ('static' 或 'dynamic')。
        """
        if obj_id in self._objects:
            raise ValueError(f"ID为 '{obj_id}' 的对象已存在。")
        if layer_type not in ['static', 'dynamic']:
            raise ValueError(f"layer_type 必须是 'static' 或 'dynamic'。")

        sid = obj_id
        self._objects[obj_id] = {'semantic_id': sid, 'layer_type': layer_type, 'parts': {}}

        for part_name, shape in parts_shapes.items():
            grid_rect = self._world_to_grid_rect(shape)
            self._draw_footprint(grid_rect, sid, layer_type)
            self._objects[obj_id]['parts'][part_name] = grid_rect

    def delete_object(self, obj_id: Any) -> None:
        """
        从地图上永久删除一个对象及其所有相关的部件和足迹。

        如果对象不存在，该方法将静默返回。

        Args:
            obj_id (Any): 要删除的对象的ID。
        """
        if obj_id not in self._objects:
            return

        obj_info = self._objects[obj_id]
        for part_name, grid_rect in obj_info['parts'].items():
            self._clear_footprint(grid_rect)

        del self._objects[obj_id]

    def update_object_part(self, obj_id: Any, part_name: str, new_shape: Dict) -> None:
        """
        更新对象某个特定部件的形状和位置。

        此方法会先清除旧部件，再绘制新部件。

        Args:
            obj_id (Any): 要修改的对象ID。
            part_name (str): 要修改的部件名称。
            new_shape (Dict): 部件的新形状描述字典。
        """
        if obj_id not in self._objects:
            raise KeyError(f"ID为 '{obj_id}' 的对象未找到。")

        obj_info = self._objects[obj_id]
        if part_name not in obj_info['parts']:
            raise KeyError(f"部件 '{part_name}' 在对象 '{obj_id}' 中未找到。")

        old_grid_rect = obj_info['parts'][part_name]
        self._clear_footprint(old_grid_rect)

        sid = obj_info['semantic_id']
        layer_type = obj_info['layer_type']

        new_grid_rect = self._world_to_grid_rect(new_shape)
        self._draw_footprint(new_grid_rect, sid, layer_type)
        obj_info['parts'][part_name] = new_grid_rect

    # --- 查询 (Read) API ---

    def get_object_info(self, obj_id: Any) -> Dict:
        """
        获取一个对象的全部元数据，包括其语义ID、图层类型和所有部件的栅格坐标。

        Args:
            obj_id (Any): 对象的ID。

        Returns:
            Dict: 对象的元数据字典。
        """
        if obj_id not in self._objects:
            raise KeyError(f"ID为 '{obj_id}' 的对象未找到。")
        return self._objects[obj_id]

    def query_by_position(self, world_pos: List[float]) -> Dict[str, Any]:
        """
        查询单个世界坐标点在所有图层上的值。

        Args:
            world_pos (List[float]): [x, y] 格式的世界坐标。

        Returns:
            Dict[str, Any]: 键为图层名，值为该点对应值的字典。
        """
        gx, gy = self._world_to_grid(world_pos)
        return {name: layer[gy, gx] for name, layer in self.layers.items()}

    def query_local_region(self, center: List[float], size: int) -> Dict[str, np.ndarray]:
        """
        查询以指定世界坐标为中心的方形区域内的所有图层数据。

        如果查询区域超出地图边界，将使用图层的初始值进行填充。

        Args:
            center (List[float]): 中心点的世界坐标 [x, y]。
            size (int): 正方形区域的边长（以栅格为单位）。

        Returns:
            Dict[str, np.ndarray]: 键为图层名，值为该区域数据的Numpy数组字典。
        """
        cx, cy = self._world_to_grid(center)
        half = size // 2
        region_data: Dict[str, np.ndarray] = {}

        for name, layer in self.layers.items():
            x0_src, x1_src = max(0, cx - half), min(self.width_in_cells, cx + half + 1)
            y0_src, y1_src = max(0, cy - half), min(self.height_in_cells, cy + half + 1)
            window = layer[y0_src:y1_src, x0_src:x1_src]

            init_val = self.layers_config[name]['initial_value']
            canvas = np.full((size, size), init_val, dtype=layer.dtype)

            dx_dest, dy_dest = x0_src - (cx - half), y0_src - (cy - half)
            canvas[dy_dest: dy_dest + window.shape[0], dx_dest: dx_dest + window.shape[1]] = window
            region_data[name] = canvas
        return region_data

    # --- 内部辅助方法 ---

    def _init_empty_layers(self) -> None:
        """根据图层配置初始化所有图层为空白状态。"""
        for layer_name, layer_cfg in self.layers_config.items():
            if 'initial_value' not in layer_cfg or 'dtype' not in layer_cfg:
                raise ValueError(f"图层 '{layer_name}' 的配置必须包含 'initial_value' 和 'dtype'。")
            init_val = layer_cfg['initial_value']
            dtype = layer_cfg['dtype']
            self.layers[layer_name] = np.full((self.height_in_cells, self.width_in_cells), init_val, dtype=dtype)

    def _populate_initial_objects(self, initial_objects: List[Dict[str, Any]]) -> None:
        """遍历初始对象列表并将它们添加到地图中。"""
        if not initial_objects:
            return
        for obj_data in initial_objects:
            obj_id = obj_data.get('obj_id')
            parts = obj_data.get('parts_shapes')
            layer_type = obj_data.get('layer_type')
            if all((obj_id, parts, layer_type)):
                self.add_object(obj_id, parts, layer_type)

    def _world_to_grid(self, world_coords: List[float]) -> Tuple[int, int]:
        """将单个世界坐标点 (x, y) 转换为栅格索引 (gx, gy)。"""
        x_w, y_w = world_coords
        x_g = int((x_w - self.bounds['x_min']) / self.resolution)
        y_g = int((y_w - self.bounds['y_min']) / self.resolution)
        x_g = np.clip(x_g, 0, self.width_in_cells - 1)
        y_g = np.clip(y_g, 0, self.height_in_cells - 1)
        return x_g, y_g

    def _world_to_grid_rect(self, shape: Dict[str, Any]) -> Tuple[int, int, int, int]:
        """将世界坐标下的矩形区域转换为栅格索引表示的矩形。"""
        if shape.get('type') != 'rectangle':
            raise NotImplementedError("目前仅支持 'rectangle' 形状。")
        min_c, max_c = shape['min_corner'], shape['max_corner']
        x0, y0 = self._world_to_grid(min_c)
        x1, y1 = self._world_to_grid(max_c)
        return min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)

    def _clear_footprint(self, grid_rect: Tuple[int, int, int, int]):
        """将指定栅格区域在所有图层上的数据恢复为其配置的初始值。"""
        x0, x1, y0, y1 = grid_rect
        for name, layer_cfg in self.layers_config.items():
            init_val = layer_cfg['initial_value']
            self.layers[name][y0:y1 + 1, x0:x1 + 1] = init_val

    def _draw_footprint(self, grid_rect: Tuple[int, int, int, int], semantic_id: Any, layer_type: str):
        """根据 layer_type 在物理层和语义层上“绘制”指定的栅格区域。"""
        x0, x1, y0, y1 = grid_rect
        if layer_type in self.layers:
            fill_val = self.layers_config[layer_type].get('fill_value', 1)
            self.layers[layer_type][y0:y1 + 1, x0:x1 + 1] = fill_val
        if 'semantic' in self.layers:
            self.layers['semantic'][y0:y1 + 1, x0:x1 + 1] = semantic_id