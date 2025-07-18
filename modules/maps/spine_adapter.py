"""
Spine适配器 - 提供spine GraphHandler的完全兼容接口

设计目标：
1. 提供与spine GraphHandler完全兼容的接口
2. 内部使用增强版地图系统
3. 确保spine代码无需修改即可使用
4. 支持所有spine功能，包括空间变换、路径规划等
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from scipy.spatial.transform import Rotation

from .map_server import MapServer, MapConfig, SpatialTransform


class SpineGraphHandlerAdapter:
    """
    Spine GraphHandler适配器
    
    提供与spine GraphHandler完全兼容的接口，内部使用增强版地图系统
    """
    
    def __init__(self, graph_path: str = None, init_node: str = None):
        """
        初始化适配器
        
        Args:
            graph_path: 图文件路径（可选）
            init_node: 初始节点（可选）
        """
        self.logger = logging.getLogger("spine_adapter")
        
        # 内部使用增强版地图服务器
        config = MapConfig(
            scene_graph_config=None,
            current_location=init_node
        )
        self._map_server = MapServer(config)
        
        # 兼容spine的属性
        self.graph = self._map_server.scene_graph.export_graph()
        self.current_location = init_node
        self.as_json_str = self._map_server.to_json_str()
        
        # 如果提供了图文件路径，加载图
        if graph_path:
            self._load_from_file(graph_path)
        
        self.logger.info(f"Spine适配器已初始化，当前节点: {self.current_location}")
    
    # ==================== 核心接口（完全兼容spine GraphHandler） ====================
    
    def reset(self, graph_as_json: str, current_location: str = "", 
              rotation: Rotation = None, utm_origin: np.ndarray = None,
              custom_data: Dict[str, Dict[str, str]] = None, flip_coords: bool = False) -> bool:
        """
        重置图（完全兼容spine接口）
        """
        try:
            # 解析JSON数据
            import json
            data = json.loads(graph_as_json)
            
            # 转换为内部格式
            internal_data = self._convert_spine_format_to_internal(data)
            
            # 创建空间变换
            spatial_transform = SpatialTransform(
                origin=utm_origin if utm_origin is not None else np.array([0.0, 0.0], dtype=np.float64),
                rotation=rotation
            )
            
            # 重新配置地图服务器
            config = MapConfig(
                scene_graph_config=internal_data,
                spatial_transform=spatial_transform,
                current_location=current_location if current_location else None
            )
            
            # 重新初始化地图服务器
            self._map_server = MapServer(config)
            
            # 更新兼容属性
            self.graph = self._map_server.scene_graph.export_graph()
            self.current_location = current_location if current_location else None
            self.as_json_str = self._map_server.to_json_str()
            
            self.logger.info(f"图已重置，当前节点: {self.current_location}")
            return True
            
        except Exception as e:
            self.logger.error(f"重置图失败: {e}")
            return False
    
    def to_json_str(self, extra_data: Dict = None) -> str:
        """导出为JSON字符串（兼容spine）"""
        return self._map_server.to_json_str(extra_data)
    
    def update_location(self, new_location: str) -> bool:
        """更新当前位置（兼容spine）"""
        success = self._map_server.update_location(new_location)
        if success:
            self.current_location = new_location
        return success
    
    def get_neighbors_by_type(self, node: str, node_type: str = "") -> Dict[str, List[str]]:
        """按类型获取邻居（兼容spine）"""
        return self._map_server.get_neighbors_by_type(node, node_type)
    
    def get_edges(self, node: str) -> Dict[str, List[str]]:
        """获取边（兼容spine）"""
        out = {}
        for edge in self.graph.edges(node):
            out[edge] = self.graph.edges[edge]
        return out
    
    def lookup_object(self, node: str) -> Tuple[Tuple[str, Dict], Tuple[str, Dict], bool]:
        """查找对象（兼容spine）"""
        if node in self.graph.nodes and self.graph.nodes[node]["type"] == "object":
            node_attr = self.graph.nodes[node]
            neighbors = list(self.graph.neighbors(node))
            
            if len(neighbors) >= 1:
                region_attr = self.graph.nodes[neighbors[0]]
                return (node, node_attr), (neighbors[0], region_attr), True
            else:
                return (node, node_attr), (None, None), False
        
        return (None, None), (None, None), False
    
    def get_neighbors(self, node_name: str) -> List[str]:
        """获取邻居（兼容spine）"""
        return self._map_server.get_neighbors(node_name)
    
    def get_path(self, start_node: str, end_node: str, only_regions: bool = False) -> List[str]:
        """获取路径（兼容spine）"""
        return self._map_server.get_path(start_node, end_node, only_regions)
    
    def contains_node(self, node: str) -> bool:
        """检查节点是否存在（兼容spine）"""
        return self._map_server.contains_node(node)
    
    def path_exists_from_current_loc(self, target: str) -> bool:
        """检查路径是否存在（兼容spine）"""
        return self._map_server.path_exists_from_current_loc(target)
    
    def lookup_node(self, node: str) -> Tuple[Dict, bool]:
        """查找节点（兼容spine）"""
        return self._map_server.lookup_node(node)
    
    def get_node_coords(self, node: str) -> Tuple[np.ndarray, bool]:
        """获取节点坐标（兼容spine）"""
        return self._map_server.get_node_coords(node)
    
    def update_node_description(self, node: str, **attrs: Any) -> None:
        """更新节点描述（兼容spine）"""
        self._map_server.update_node_description(node, **attrs)
        # 更新内部图引用
        self.graph = self._map_server.scene_graph.export_graph()
    
    def get_node_type(self, node: str) -> str:
        """获取节点类型（兼容spine）"""
        return self._map_server.get_node_type(node)
    
    def update_with_node(self, node: str, edges: List[str], attrs: Dict[str, Any] = None) -> None:
        """更新节点（兼容spine）"""
        attrs = attrs or {}
        self._map_server.update_with_node(node, edges, attrs)
        # 更新内部图引用
        self.graph = self._map_server.scene_graph.export_graph()
    
    def update_with_edge(self, edge: Tuple[str, str], attrs: Dict[str, Any] = None) -> None:
        """更新边（兼容spine）"""
        attrs = attrs or {}
        self._map_server.update_with_edge(edge, attrs)
        # 更新内部图引用
        self.graph = self._map_server.scene_graph.export_graph()
    
    def remove_edge(self, start: str, end: str) -> None:
        """删除边（兼容spine）"""
        self._map_server.remove_edge(start, end)
        # 更新内部图引用
        self.graph = self._map_server.scene_graph.export_graph()
    
    def get_region_nodes_and_locs(self) -> Tuple[np.ndarray, np.ndarray]:
        """获取区域节点和位置（兼容spine）"""
        return self._map_server.get_region_nodes_and_locs()
    
    def get_closest_reachable_node(self, goal_node: str, current_node: str = None) -> Tuple[str, str]:
        """获取最近可达节点（兼容spine）"""
        return self._map_server.get_closest_reachable_node(goal_node, current_node)
    
    # ==================== 文件加载支持 ====================
    
    def _load_from_file(self, graph_path: str) -> bool:
        """从文件加载图"""
        try:
            import json
            with open(graph_path, 'r') as f:
                data = json.load(f)
            
            # 转换为内部格式
            internal_data = self._convert_spine_format_to_internal(data)
            
            # 重新配置地图服务器
            config = MapConfig(
                scene_graph_config=internal_data,
                current_location=self.current_location
            )
            
            self._map_server = MapServer(config)
            
            # 更新兼容属性
            self.graph = self._map_server.scene_graph.export_graph()
            self.as_json_str = self._map_server.to_json_str()
            
            self.logger.info(f"从文件加载图成功: {graph_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"从文件加载图失败: {e}")
            return False
    
    def _convert_spine_format_to_internal(self, spine_data: Dict) -> Dict:
        """转换spine格式到内部格式"""
        internal_data = {
            "nodes": [],
            "edges": []
        }
        
        # 处理对象
        for obj in spine_data.get("objects", []):
            node_data = {
                "id": obj["name"],
                "type": "object",
                "coords": self._parse_coords(obj["coords"])
            }
            internal_data["nodes"].append(node_data)
        
        # 处理区域
        for region in spine_data.get("regions", []):
            node_data = {
                "id": region["name"],
                "type": "region",
                "coords": self._parse_coords(region["coords"])
            }
            internal_data["nodes"].append(node_data)
        
        # 处理机器人
        for robot in spine_data.get("robots", []):
            node_data = {
                "id": robot["name"],
                "type": "robot",
                "coords": self._parse_coords(robot["coords"])
            }
            internal_data["nodes"].append(node_data)
        
        # 处理对象连接
        for connection in spine_data.get("object_connections", []):
            if len(connection) >= 2:
                edge_data = {
                    "source": connection[0],
                    "target": connection[1],
                    "type": "object_connection"
                }
                internal_data["edges"].append(edge_data)
        
        # 处理区域连接
        for connection in spine_data.get("region_connections", []):
            if len(connection) >= 2:
                edge_data = {
                    "source": connection[0],
                    "target": connection[1],
                    "type": "region_connection"
                }
                internal_data["edges"].append(edge_data)
        
        return internal_data
    
    def _parse_coords(self, coords_str: str) -> List[float]:
        """解析坐标字符串"""
        try:
            # 移除方括号和空格
            coords_str = coords_str.strip("[]").replace(" ", "")
            # 分割并转换为浮点数
            coords = [float(x) for x in coords_str.split(",")]
            return coords
        except:
            return [0.0, 0.0]
    
    # ==================== 增强功能（非spine兼容） ====================
    
    def get_map_server(self) -> MapServer:
        """获取增强版地图服务器实例"""
        return self._map_server
    
    def subscribe_to_events(self, callback: callable):
        """订阅地图事件"""
        self._map_server.subscribe(callback)
    
    def unsubscribe_from_events(self, callback: callable):
        """取消订阅地图事件"""
        self._map_server.unsubscribe(callback)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self._map_server.get_statistics()
    
    # ==================== 兼容性方法 ====================
    
    def __str__(self) -> str:
        return f"SpineGraphHandlerAdapter(nodes={len(self.graph.nodes)}, current={self.current_location})"
    
    def __repr__(self) -> str:
        return self.__str__()


# 为了完全兼容spine，提供别名
GraphHandler = SpineGraphHandlerAdapter 