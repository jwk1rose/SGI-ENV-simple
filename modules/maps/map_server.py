"""
MapServer - 统一的场景图服务接口

设计目标：
1. 提供统一的API，兼容现有map系统和spine系统
2. 支持多模态数据管理（空间+语义+物理）
3. 提供spine GraphHandler的兼容接口
4. 支持多机器人/多视角地图融合
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

import numpy as np
from scipy.spatial.transform import Rotation

from .scene_graph import SceneGraph, SpatialTransform
from .layered_map import LayeredGridMap


@dataclass
class MapConfig:
    """地图配置"""
    # 场景图配置
    scene_graph_config: Dict[str, Any] = None
    
    # 栅格地图配置
    grid_map_config: Optional[Dict[str, Any]] = None

    # 空间变换配置
    spatial_transform: Optional[SpatialTransform] = None

    # 当前位置
    current_location: Optional[str] = None


class MapServer:
    """
    统一的场景图服务接口
    
    核心功能：
    1. 管理增强版场景图（EnhancedSceneGraph）
    2. 管理分层栅格地图（LayeredGridMap）
    3. 提供spine GraphHandler兼容接口
    4. 支持多模态数据同步
    5. 提供统一的事件通知系统
    """
    
    def __init__(self, config: MapConfig):
        """
        初始化增强版地图服务器
        
        Args:
            config: 地图配置
        """
        self.logger = logging.getLogger("enhanced_map_server")
        self.config = config
        
        # 核心组件
        self.scene_graph = SceneGraph(
            initial_data=config.scene_graph_config,
            spatial_transform=config.spatial_transform,
            current_location=config.current_location
        )
        
        # 栅格地图（可选）
        self.grid_map = None
        if config.grid_map_config:
            self.grid_map = LayeredGridMap(config.grid_map_config)
        
        # 事件订阅者
        self._subscribers: List[callable] = []
        
        # 同步状态
        self._sync_enabled = True
        
        self.logger.info("增强版地图服务器已初始化")
    
    # ==================== 事件系统 ====================
    
    def subscribe(self, callback: callable):
        """订阅地图事件"""
        if callback not in self._subscribers:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: callable):
        """取消订阅"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
    
    def _notify_subscribers(self, event: Dict[str, Any]):
        """通知订阅者"""
        for callback in self._subscribers:
            try:
                callback(event)
            except Exception as e:
                self.logger.error(f"事件回调执行失败: {e}")
    
    # ==================== 场景图操作（兼容现有SceneGraph） ====================
    
    def add_object(self, obj_id: Any, **attrs: Any) -> None:
        """添加对象"""
        self.scene_graph.add_object(obj_id, **attrs)
        
        # 同步到栅格地图
        if self.grid_map and self._sync_enabled:
            self._sync_object_to_grid(obj_id, attrs)
        
        # 通知事件
        self._notify_subscribers({
            "type": "OBJECT_ADDED",
            "object_id": obj_id,
            "data": attrs
        })
    
    def remove_object(self, obj_id: Any) -> None:
        """删除对象"""
        self.scene_graph.remove_object(obj_id)
        
        # 同步到栅格地图
        if self.grid_map and self._sync_enabled:
            self._sync_remove_from_grid(obj_id)
        
        # 通知事件
        self._notify_subscribers({
            "type": "OBJECT_REMOVED",
            "object_id": obj_id
        })
    
    def update_object(self, obj_id: Any, **attrs: Any) -> None:
        """更新对象"""
        self.scene_graph.update_object(obj_id, **attrs)
        
        # 同步到栅格地图
        if self.grid_map and self._sync_enabled:
            self._sync_object_to_grid(obj_id, attrs)
        
        # 通知事件
        self._notify_subscribers({
            "type": "OBJECT_UPDATED",
            "object_id": obj_id,
            "data": attrs
        })
    
    def get_object(self, obj_id: Any) -> Dict[str, Any]:
        """获取对象"""
        return self.scene_graph.get_object(obj_id)
    
    def add_relation(self, source: Any, target: Any, **attrs: Any) -> None:
        """添加关系"""
        self.scene_graph.add_relation(source, target, **attrs)
        
        # 通知事件
        self._notify_subscribers({
            "type": "RELATION_ADDED",
            "source": source,
            "target": target,
            "data": attrs
        })
    
    def remove_relation(self, source: Any, target: Any) -> None:
        """删除关系"""
        self.scene_graph.remove_relation(source, target)
        
        # 通知事件
        self._notify_subscribers({
            "type": "RELATION_REMOVED",
            "source": source,
            "target": target
        })
    
    # ==================== 查询操作 ====================
    
    def find_objects_by_property(self, key: str, value: Any) -> List[Any]:
        """按属性查找对象"""
        return self.scene_graph.find_objects_by_property(key, value)
    
    def find_objects_by_nested_property(self, keys: List[str], value: Any) -> List[Any]:
        """按嵌套属性查找对象"""
        return self.scene_graph.find_objects_by_nested_property(keys, value)
    
    def query_by_position(self, world_pos: List[float]) -> Dict[str, Any]:
        """按位置查询"""
        result = {}
        
        # 场景图查询
        result["scene_graph"] = self._query_scene_graph_by_position(world_pos)
        
        # 栅格地图查询
        if self.grid_map:
            result["grid_map"] = self.grid_map.query_by_position(world_pos)
        
        return result
    
    def _query_scene_graph_by_position(self, world_pos: List[float]) -> Dict[str, Any]:
        """在场景图中按位置查询"""
        result = {"objects": [], "regions": [], "robots": []}
        
        for node, attrs in self.scene_graph.export_graph().nodes(data=True):
            coords = attrs.get('coords', [0, 0])
            distance = np.linalg.norm(np.array(coords) - np.array(world_pos))
            
            # 在5米范围内认为是同一位置
            if distance <= 5.0:
                node_type = attrs.get('type', 'object')
                if node_type == 'object':
                    result["objects"].append({"id": node, "attrs": attrs, "distance": distance})
                elif node_type == 'region':
                    result["regions"].append({"id": node, "attrs": attrs, "distance": distance})
                elif node_type == 'robot':
                    result["robots"].append({"id": node, "attrs": attrs, "distance": distance})
        
        return result
    
    # ==================== 路径规划（兼容spine） ====================
    
    def get_path(self, start_node: str, end_node: str, only_regions: bool = False) -> List[str]:
        """获取路径"""
        return self.scene_graph.get_path(start_node, end_node, only_regions)
    
    def path_exists_from_current_loc(self, target: str) -> bool:
        """检查路径是否存在"""
        return self.scene_graph.path_exists_from_current_loc(target)
    
    def get_closest_reachable_node(self, goal_node: str, current_node: Optional[str] = None) -> Tuple[str, str]:
        """获取最近可达节点"""
        return self.scene_graph.get_closest_reachable_node(goal_node, current_node)
    
    # ==================== 位置管理（兼容spine） ====================
    
    def update_location(self, new_location: str) -> bool:
        """更新当前位置"""
        success = self.scene_graph.update_location(new_location)
        if success:
            self._notify_subscribers({
                "type": "LOCATION_UPDATED",
                "location": new_location
            })
        return success
    
    def get_current_location(self) -> Optional[str]:
        """获取当前位置"""
        return self.scene_graph.get_current_location()
    
    # ==================== 空间变换（兼容spine） ====================
    
    def set_spatial_transform(self, transform: SpatialTransform):
        """设置空间变换"""
        self.scene_graph.set_spatial_transform(transform)
        self._notify_subscribers({
            "type": "SPATIAL_TRANSFORM_UPDATED",
            "transform": transform
        })
    
    def transform_coords(self, coords: np.ndarray, inverse: bool = False) -> np.ndarray:
        """变换坐标"""
        return self.scene_graph.transform_coords(coords, inverse)
    
    # ==================== 栅格地图操作 ====================
    
    def add_object_to_grid(self, obj_id: Any, parts_shapes: Dict[str, Dict], layer_type: str) -> None:
        """添加对象到栅格地图"""
        if not self.grid_map:
            raise RuntimeError("栅格地图未初始化")
        
        self.grid_map.add_object(obj_id, parts_shapes, layer_type)
        
        # 同步到场景图
        if self._sync_enabled:
            self._sync_grid_to_scene_graph(obj_id, parts_shapes, layer_type)
    
    def query_local_region(self, center: List[float], size: int) -> Dict[str, np.ndarray]:
        """查询局部区域"""
        if not self.grid_map:
            return {}
        return self.grid_map.query_local_region(center, size)
    
    # ==================== 数据同步 ====================
    
    def _sync_object_to_grid(self, obj_id: Any, attrs: Dict[str, Any]):
        """同步对象到栅格地图"""
        if not self.grid_map:
            return
        
        # 从场景图属性提取形状信息
        shape = attrs.get('shape')
        if not shape:
            return
        
        # 转换为栅格地图格式
        parts_shapes = {"main": shape}
        layer_type = attrs.get('layer_type', 'dynamic')
        
        try:
            # 如果对象已存在，先删除
            if obj_id in self.grid_map._objects:
                self.grid_map.delete_object(obj_id)
            
            # 添加对象
            self.grid_map.add_object(obj_id, parts_shapes, layer_type)
        except Exception as e:
            self.logger.warning(f"同步对象到栅格地图失败: {e}")
    
    def _sync_remove_from_grid(self, obj_id: Any):
        """从栅格地图同步删除"""
        if not self.grid_map:
            return
        
        try:
            self.grid_map.delete_object(obj_id)
        except Exception as e:
            self.logger.warning(f"从栅格地图删除对象失败: {e}")
    
    def _sync_grid_to_scene_graph(self, obj_id: Any, parts_shapes: Dict[str, Dict], layer_type: str):
        """从栅格地图同步到场景图"""
        # 这里可以实现从栅格地图到场景图的同步逻辑
        # 目前简化处理，主要依赖场景图作为主数据源
        pass
    
    # ==================== 数据导入导出 ====================
    
    def to_json_str(self, extra_data: Dict = None) -> str:
        """导出为JSON字符串（兼容spine格式）"""
        return self.scene_graph.to_json_str(extra_data)
    
    def export_scene_graph(self):
        """导出场景图"""
        return self.scene_graph.export_graph()
    
    def export_grid_map(self):
        """导出栅格地图"""
        return self.grid_map
    
    # ==================== 兼容性接口（spine GraphHandler） ====================
    
    # 以下方法提供与spine GraphHandler完全兼容的接口
    
    def contains_node(self, node: str) -> bool:
        """检查节点是否存在（兼容spine）"""
        return self.scene_graph.contains_node(node)
    
    def get_node_coords(self, node: str) -> Tuple[np.ndarray, bool]:
        """获取节点坐标（兼容spine）"""
        return self.scene_graph.get_node_coords(node)
    
    def get_node_type(self, node: str) -> str:
        """获取节点类型（兼容spine）"""
        return self.scene_graph.get_node_type(node)
    
    def lookup_node(self, node: str) -> Tuple[Dict, bool]:
        """查找节点（兼容spine）"""
        return self.scene_graph.lookup_node(node)
    
    def get_neighbors(self, node_name: str) -> List[str]:
        """获取邻居（兼容spine）"""
        return self.scene_graph.get_neighbors(node_name)
    
    def get_neighbors_by_type(self, node: str, node_type: Optional[str] = "") -> Dict[str, List[str]]:
        """按类型获取邻居（兼容spine）"""
        return self.scene_graph.get_neighbors_by_type(node, node_type)
    
    def update_with_node(self, node: str, edges: List[str], attrs: Dict[str, Any] = {}) -> None:
        """更新节点（兼容spine）"""
        # 添加节点
        self.scene_graph.add_object(node, **attrs)
        
        # 添加边
        for edge in edges:
            self.scene_graph.add_relation(node, edge)
    
    def update_with_edge(self, edge: Tuple[str, str], attrs: Dict[str, Any] = {}) -> None:
        """更新边（兼容spine）"""
        self.scene_graph.add_relation(edge[0], edge[1], **attrs)
    
    def remove_edge(self, start: str, end: str) -> None:
        """删除边（兼容spine）"""
        self.scene_graph.remove_relation(start, end)
    
    def update_node_description(self, node: str, **attrs: Any) -> None:
        """更新节点描述（兼容spine）"""
        self.scene_graph.update_object(node, **attrs)
    
    # ==================== 高级功能 ====================
    
    def get_region_nodes_and_locs(self) -> Tuple[np.ndarray, np.ndarray]:
        """获取区域节点和位置（兼容spine）"""
        region_nodes = []
        region_locs = []
        
        for node in self.scene_graph.export_graph().nodes():
            if self.scene_graph.get_node_type(node) == "region":
                coords, success = self.scene_graph.get_node_coords(node)
                if success:
                    region_nodes.append(node)
                    region_locs.append(coords)
        
        return np.array(region_nodes), np.array(region_locs)
    
    def reset(self, graph_as_json: str = None, current_location: str = None, 
              rotation: Rotation = None, utm_origin: np.ndarray = None) -> bool:
        """重置地图（兼容spine）"""
        try:
            if graph_as_json:
                # 解析JSON并重新初始化场景图
                import json
                data = json.loads(graph_as_json)
                
                # 创建新的空间变换
                spatial_transform = SpatialTransform(
                    origin=utm_origin if utm_origin is not None else np.array([0.0, 0.0]),
                    rotation=rotation
                )
                
                # 重新初始化场景图
                self.scene_graph = SceneGraph(
                    initial_data=data,
                    spatial_transform=spatial_transform,
                    current_location=current_location
                )
            else:
                # 只更新位置和变换
                if current_location:
                    self.scene_graph.update_location(current_location)
                if rotation or utm_origin is not None:
                    new_transform = SpatialTransform(
                        origin=utm_origin if utm_origin is not None else self.scene_graph.spatial_transform.origin,
                        rotation=rotation if rotation is not None else self.scene_graph.spatial_transform.rotation
                    )
                    self.scene_graph.set_spatial_transform(new_transform)
            
            self._notify_subscribers({
                "type": "MAP_RESET",
                "data": {"current_location": current_location}
            })
            
            return True
            
        except Exception as e:
            self.logger.error(f"重置地图失败: {e}")
            return False
    
    # ==================== 统计信息 ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        graph = self.scene_graph.export_graph()
        
        stats = {
            "total_nodes": len(graph.nodes),
            "total_edges": len(graph.edges),
            "node_types": {},
            "current_location": self.scene_graph.get_current_location(),
            "has_grid_map": self.grid_map is not None
        }
        
        # 统计节点类型
        for node, attrs in graph.nodes(data=True):
            node_type = attrs.get('type', 'object')
            stats["node_types"][node_type] = stats["node_types"].get(node_type, 0) + 1
        
        return stats
    
    # ==================== 调试和日志 ====================
    
    def __str__(self) -> str:
        stats = self.get_statistics()
        return f"EnhancedMapServer(nodes={stats['total_nodes']}, edges={stats['total_edges']}, current={stats['current_location']})"
    
    def __repr__(self) -> str:
        return self.__str__() 