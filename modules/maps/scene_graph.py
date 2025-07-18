import networkx as nx
import numpy as np
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from scipy.spatial.transform import Rotation
import json
import logging


@dataclass
class SpatialTransform:
    """空间变换配置"""
    origin: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0], dtype=np.float64))
    rotation: Optional[Rotation] = None
    scale: float = 1.0
    
    def apply(self, coords: np.ndarray) -> np.ndarray:
        """应用空间变换"""
        coords = coords.copy().astype(np.float64)
        coords -= self.origin
        if self.rotation is not None:
            coords_3d = np.concatenate([coords, np.zeros((coords.shape[0], 1))], axis=1)
            coords_3d = self.rotation.apply(coords_3d)
            coords = coords_3d[:, :2]
        coords *= self.scale
        return coords
    
    def inverse(self, coords: np.ndarray) -> np.ndarray:
        """应用逆变换"""
        coords = coords.copy().astype(np.float64)
        coords /= self.scale
        if self.rotation is not None:
            coords_3d = np.concatenate([coords, np.zeros((coords.shape[0], 1))], axis=1)
            coords_3d = self.rotation.inv().apply(coords_3d)
            coords = coords_3d[:, :2]
        coords += self.origin
        return coords


class SceneGraph:
    """

    核心特性：
    1. 有向图 + 空间坐标支持
    2. 多坐标系变换
    3. 路径规划算法
    4. 类型化节点和边
    5. 灵活的属性系统
    6. 与spine GraphHandler兼容的接口
    """
    
    def __init__(self, 
                 initial_data: Optional[Dict[str, List[Dict]]] = None,
                 spatial_transform: Optional[SpatialTransform] = None,
                 current_location: Optional[str] = None):
        """
        初始化增强版场景图
        
        Args:
            initial_data: 初始数据
            spatial_transform: 空间变换配置
            current_location: 当前位置节点ID
        """
        self.logger = logging.getLogger("enhanced_scene_graph")
        
        # 核心图结构
        self.__graph = nx.DiGraph()
        
        # 空间变换
        self.spatial_transform = spatial_transform or SpatialTransform()
        
        # 当前位置
        self.current_location = current_location
        
        # 节点类型映射
        self.node_types = {
            'object': set(),  # 物体节点
            'region': set(),  # 区域节点
            'robot': set(),   # 机器人节点
            'connection': set()  # 连接节点
        }
        
        # 初始化
        if initial_data:
            self._populate_from_data(initial_data)
    
    # ==================== 基础CRUD操作（兼容现有SceneGraph） ====================
    
    def add_object(self, obj_id: Any, **attrs: Any) -> None:
        """添加对象节点"""
        # 确保有坐标信息
        if 'coords' not in attrs:
            attrs['coords'] = [0.0, 0.0]
        
        # 应用空间变换
        coords = np.array(attrs['coords'], dtype=np.float64)
        transformed_coords = self.spatial_transform.apply(coords.reshape(1, -1))[0]
        attrs['coords'] = transformed_coords.tolist()
        
        # 设置默认类型
        if 'type' not in attrs:
            attrs['type'] = 'object'
        
        # 添加到图
        self.__graph.add_node(obj_id, **attrs)
        
        # 更新类型映射
        node_type = attrs.get('type', 'object')
        if node_type in self.node_types:
            self.node_types[node_type].add(obj_id)
        
        self.logger.debug(f"添加对象: {obj_id} ({node_type})")
    
    def remove_object(self, obj_id: Any) -> None:
        """删除对象节点"""
        if not self.__graph.has_node(obj_id):
            raise KeyError(f"Object '{obj_id}' does not exist.")
        
        # 从类型映射中移除
        for type_set in self.node_types.values():
            type_set.discard(obj_id)
        
        self.__graph.remove_node(obj_id)
        self.logger.debug(f"删除对象: {obj_id}")
    
    def update_object(self, obj_id: Any, **attrs: Any) -> None:
        """更新对象属性"""
        if not self.__graph.has_node(obj_id):
            raise KeyError(f"Object '{obj_id}' does not exist.")
        
        # 如果更新坐标，应用空间变换
        if 'coords' in attrs:
            coords = np.array(attrs['coords'], dtype=np.float64)
            transformed_coords = self.spatial_transform.apply(coords.reshape(1, -1))[0]
            attrs['coords'] = transformed_coords.tolist()
        
        # 如果更新类型，更新类型映射
        if 'type' in attrs:
            old_type = self.__graph.nodes[obj_id].get('type', 'object')
            new_type = attrs['type']
            
            if old_type in self.node_types:
                self.node_types[old_type].discard(obj_id)
            if new_type in self.node_types:
                self.node_types[new_type].add(obj_id)
        
        self.__graph.nodes[obj_id].update(attrs)
        self.logger.debug(f"更新对象: {obj_id}")
    
    def get_object(self, obj_id: Any) -> Dict[str, Any]:
        """获取对象属性"""
        if not self.__graph.has_node(obj_id):
            raise KeyError(f"Object '{obj_id}' does not exist.")
        return dict(self.__graph.nodes[obj_id])
    
    def add_relation(self, source: Any, target: Any, **attrs: Any) -> None:
        """添加有向关系"""
        if not self.__graph.has_node(source) or not self.__graph.has_node(target):
            raise KeyError(f"Source '{source}' or Target '{target}' node does not exist.")
        
        # 计算距离权重
        if 'weight' not in attrs:
            source_coords = np.array(self.__graph.nodes[source].get('coords', [0, 0]), dtype=np.float64)
            target_coords = np.array(self.__graph.nodes[target].get('coords', [0, 0]), dtype=np.float64)
            distance = np.linalg.norm(source_coords - target_coords)
            attrs['weight'] = distance
        
        self.__graph.add_edge(source, target, **attrs)
        self.logger.debug(f"添加关系: {source} -> {target}")
    
    def remove_relation(self, source: Any, target: Any) -> None:
        """删除关系"""
        self.__graph.remove_edge(source, target)
        self.logger.debug(f"删除关系: {source} -> {target}")
    
    def update_relation(self, source: Any, target: Any, **attrs: Any) -> None:
        """更新关系属性"""
        if not self.__graph.has_edge(source, target):
            raise KeyError(f"Relation from '{source}' to '{target}' does not exist.")
        self.__graph.edges[source, target].update(attrs)
    
    def get_relations(self, obj_id: Any, direction: str = 'all') -> List[Tuple[Any, Any, Dict[str, Any]]]:
        """获取关系"""
        if not self.__graph.has_node(obj_id):
            raise KeyError(f"Object '{obj_id}' does not exist.")
        
        edges = []
        if direction in ('all', 'out'):
            edges.extend(self.__graph.out_edges(obj_id, data=True))
        if direction in ('all', 'in'):
            edges.extend(self.__graph.in_edges(obj_id, data=True))
        return [e for e in edges]
    
    # ==================== 查询操作（兼容现有SceneGraph） ====================
    
    def find_objects_by_property(self, key: str, value: Any) -> List[Any]:
        """按属性查找对象"""
        return [n for n, attrs in self.__graph.nodes(data=True) if attrs.get(key) == value]
    
    def find_objects_by_nested_property(self, keys: List[str], value: Any) -> List[Any]:
        """按嵌套属性查找对象"""
        results = []
        for n, attrs in self.__graph.nodes(data=True):
            d = attrs
            try:
                for k in keys:
                    d = d[k]
                if d == value:
                    results.append(n)
            except (KeyError, TypeError):
                continue
        return results
    
    # ==================== 空间操作（融合spine优点） ====================
    
    def get_node_coords(self, node: str) -> Tuple[np.ndarray, bool]:
        """获取节点坐标（兼容spine接口）"""
        if self.contains_node(node):
            coords = self.__graph.nodes[node].get('coords', [0.0, 0.0])
            return np.array(coords, dtype=np.float64), True
        return np.zeros(2, dtype=np.float64), False
    
    def get_node_type(self, node: str) -> str:
        """获取节点类型（兼容spine接口）"""
        node_info, success = self.lookup_node(node)
        if success and "type" in node_info:
            return node_info["type"]
        return ""
    
    def contains_node(self, node: str) -> bool:
        """检查节点是否存在（兼容spine接口）"""
        return self.__graph.has_node(node)
    
    def lookup_node(self, node: str) -> Tuple[Dict, bool]:
        """查找节点（兼容spine接口）"""
        if self.contains_node(node):
            return dict(self.__graph.nodes[node]), True
        return {}, False
    
    def get_neighbors(self, node_name: str) -> List[str]:
        """获取邻居节点（兼容spine接口）"""
        if not self.contains_node(node_name):
            return []
        return list(self.__graph.neighbors(node_name))
    
    def get_neighbors_by_type(self, node: str, node_type: Optional[str] = "") -> Dict[str, List[str]]:
        """按类型获取邻居（兼容spine接口）"""
        ret_val = {}
        if node in self.__graph.nodes:
            neighbors = list(self.__graph.neighbors(node))
            
            for neighbor in neighbors:
                if node_type == "":
                    ret_val[neighbor] = self.lookup_node(neighbor)[0]
                elif node_type != "" and self.lookup_node(neighbor)[0].get("type") == node_type:
                    ret_val[neighbor] = self.lookup_node(neighbor)[0]
        
        return ret_val
    
    # ==================== 路径规划（融合spine算法） ====================
    
    def get_path(self, start_node: str, end_node: str, only_regions: Optional[bool] = False) -> List[str]:
        """获取最短路径（兼容spine接口）"""
        try:
            if only_regions:
                # 只考虑区域节点的路径
                subgraph = self.__graph.subgraph([
                    n for n in self.__graph.nodes 
                    if self.get_node_type(n) == "region"
                ])
                return nx.shortest_path(subgraph, start_node, end_node)
            else:
                return nx.shortest_path(self.__graph, start_node, end_node)
        except nx.NetworkXNoPath:
            return []
    
    def path_exists_from_current_loc(self, target: str) -> bool:
        """检查从当前位置到目标是否有路径（兼容spine接口）"""
        if self.current_location is None:
            raise ValueError("current location is unknown")
        return nx.has_path(self.__graph, self.current_location, target)
    
    def get_closest_reachable_node(self, goal_node: str, current_node: Optional[str] = None) -> Tuple[str, str]:
        """获取最近可达节点（兼容spine接口）"""
        if current_node is None:
            if self.current_location is None:
                raise ValueError("current_location must be set")
            current_node = self.current_location
        
        # 获取连通分量
        nodes_reachable_from_curr_loc = list(nx.node_connected_component(self.__graph.to_undirected(), current_node))
        nodes_reachable_from_goal = list(nx.node_connected_component(self.__graph.to_undirected(), goal_node))
        
        # 只考虑区域节点
        nodes_reachable_from_curr_loc = [
            n for n in nodes_reachable_from_curr_loc
            if self.get_node_type(n) == "region"
        ]
        nodes_reachable_from_goal = [
            n for n in nodes_reachable_from_goal 
            if self.get_node_type(n) == "region"
        ]
        
        if not nodes_reachable_from_curr_loc or not nodes_reachable_from_goal:
            return current_node, goal_node
        
        # 计算距离
        coords_of_nodes_reachable_curr_loc = np.array([
            self.get_node_coords(n)[0] for n in nodes_reachable_from_curr_loc
        ], dtype=np.float64)
        
        closest_node_dist = np.inf
        closest_node_id = current_node
        target_node_id = goal_node
        
        for node_reachable_from_goal in nodes_reachable_from_goal:
            goal_coords = self.get_node_coords(node_reachable_from_goal)[0]
            node_dists = np.linalg.norm(
                coords_of_nodes_reachable_curr_loc - goal_coords,
                axis=-1
            )
            
            if node_dists.min() < closest_node_dist:
                closest_node_dist = node_dists.min()
                closest_node_id = nodes_reachable_from_curr_loc[node_dists.argmin()]
                target_node_id = node_reachable_from_goal
        
        return closest_node_id, target_node_id
    
    # ==================== 空间变换操作 ====================
    
    def set_spatial_transform(self, transform: SpatialTransform):
        """设置空间变换"""
        self.spatial_transform = transform
        self.logger.info("空间变换已更新")
    
    def transform_coords(self, coords: np.ndarray, inverse: bool = False) -> np.ndarray:
        """变换坐标"""
        if inverse:
            return self.spatial_transform.inverse(coords)
        else:
            return self.spatial_transform.apply(coords)
    
    # ==================== 位置管理 ====================
    
    def update_location(self, new_location: str) -> bool:
        """更新当前位置（兼容spine接口）"""
        if not self.contains_node(new_location):
            return False
        self.current_location = new_location
        self.logger.info(f"当前位置已更新: {new_location}")
        return True
    
    def get_current_location(self) -> Optional[str]:
        """获取当前位置"""
        return self.current_location
    
    # ==================== 数据导入导出 ====================
    
    def _populate_from_data(self, data: Dict[str, List[Dict]]) -> None:
        """从数据填充图"""
        nodes = data.get('nodes', [])
        for node_data in nodes:
            if 'id' not in node_data:
                continue
            obj_id = node_data['id']
            attrs = {k: v for k, v in node_data.items() if k != 'id'}
            self.add_object(obj_id, **attrs)
        
        edges = data.get('edges', [])
        for edge_data in edges:
            source = edge_data.get('source')
            target = edge_data.get('target')
            if not source or not target:
                continue
            attrs = {k: v for k, v in edge_data.items() if k not in ['source', 'target']}
            self.add_relation(source, target, **attrs)
    
    def to_json_str(self, extra_data: Dict = None) -> str:
        """导出为JSON字符串（兼容spine格式）"""
        extra_data = extra_data or {}
        
        # 按类型组织节点
        objects = []
        regions = []
        robots = []
        
        for node, attrs in self.__graph.nodes(data=True):
            node_type = attrs.get('type', 'object')
            coords = attrs.get('coords', [0.0, 0.0])
            coords_str = f"[{coords[0]:.1f}, {coords[1]:.1f}]"
            
            node_data = {"name": node, "coords": coords_str}
            
            if node_type == 'object':
                objects.append(node_data)
            elif node_type == 'region':
                regions.append(node_data)
            elif node_type == 'robot':
                robots.append(node_data)
            else:
                objects.append(node_data)  # 默认归类为object
        
        # 收集边
        object_connections = []
        region_connections = []
        added_edges = set()
        
        for edge in self.__graph.edges():
            edge_tuple = tuple(sorted(edge))
            if edge_tuple not in added_edges:
                source_type = self.get_node_type(edge[0])
                target_type = self.get_node_type(edge[1])
                
                if source_type == 'region' and target_type == 'region':
                    region_connections.append(sorted([edge[0], edge[1]]))
                else:
                    object_connections.append(sorted([edge[0], edge[1]]))
                
                added_edges.add(edge_tuple)
        
        # 构建输出
        graph_dict = {
            "objects": objects,
            "regions": regions,
            "robots": robots,
            "object_connections": object_connections,
            "region_connections": region_connections,
        }
        
        if self.current_location:
            graph_dict["current_location"] = self.current_location
        
        graph_dict.update(extra_data)
        
        return json.dumps(graph_dict, indent=2)
    
    def export_graph(self) -> nx.DiGraph:
        """导出底层图"""
        return self.__graph.copy()
    
    # ==================== 兼容性接口 ====================
    
    def __contains__(self, obj_id: Any) -> bool:
        return self.__graph.has_node(obj_id)
    
    def __len__(self) -> int:
        return self.__graph.number_of_nodes()
    
    def __str__(self) -> str:
        out = f"EnhancedSceneGraph (Nodes: {len(self)}, Current: {self.current_location})\n"
        out += "Nodes:\n"
        for node, attrs in self.__graph.nodes(data=True):
            node_type = attrs.get('type', 'object')
            coords = attrs.get('coords', [0, 0])
            out += f"  {node} ({node_type}): {coords}\n"
        
        out += "Edges:\n"
        for edge in self.__graph.edges():
            out += f"  {edge[0]} -> {edge[1]}\n"
        
        return out
    
    def __repr__(self) -> str:
        return f"EnhancedSceneGraph(nodes={len(self)}, current_location={self.current_location})" 