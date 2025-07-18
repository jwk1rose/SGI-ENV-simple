"""
空间查询工具类

提供基于 TaskContext 的空间查询功能，包括位置查询、碰撞检测、路径规划等。
这个工具类保持纯净，不修改 TaskContext 的状态，只提供查询功能。
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set
import math


def calculate_distance(pos1: Dict[str, float], pos2: Dict[str, float]) -> float:
    """
    计算两个位置点之间的欧几里得距离
    
    Args:
        pos1: 第一个位置字典，包含 'x' 和 'y' 键
        pos2: 第二个位置字典，包含 'x' 和 'y' 键
        
    Returns:
        两点间的欧几里得距离
    """
    x1, y1 = pos1.get('x', 0), pos1.get('y', 0)
    x2, y2 = pos2.get('x', 0), pos2.get('y', 0)
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


class SpatialQueryUtils:
    """
    空间查询工具类
    
    提供基于 TaskContext 的空间查询功能，包括：
    - 位置查询
    - 碰撞检测
    - 距离计算
    - 空间关系判断
    - 路径规划辅助
    """
    
    def __init__(self, task_context: "TaskContext"):
        """
        初始化空间查询工具
        
        Args:
            task_context: TaskContext 实例，提供场景数据
        """
        self.task_context = task_context
        
    def get_object_position(self, object_id: Any) -> Optional[Tuple[float, float]]:
        """
        获取对象的位置坐标
        
        Args:
            object_id: 对象ID
            
        Returns:
            对象中心位置坐标 (x, y)，如果对象不存在或没有位置信息则返回 None
        """
        obj = self.task_context.get_object(object_id)
        if not obj:
            return None
            
        shape = obj.get('shape')
        if not shape:
            return None
            
        if shape.get('type') == 'rectangle':
            min_corner = shape.get('min_corner', [0, 0])
            max_corner = shape.get('max_corner', [0, 0])
            return (
                (min_corner[0] + max_corner[0]) / 2,
                (min_corner[1] + max_corner[1]) / 2
            )
        elif shape.get('type') == 'circle':
            center = shape.get('center', [0, 0])
            return (center[0], center[1])
            
        return None
        
    def get_object_bounds(self, object_id: Any) -> Optional[Dict[str, float]]:
        """
        获取对象的边界框
        
        Args:
            object_id: 对象ID
            
        Returns:
            边界框字典 {'x_min', 'x_max', 'y_min', 'y_max'}，如果对象不存在则返回 None
        """
        obj = self.task_context.get_object(object_id)
        if not obj:
            return None
            
        shape = obj.get('shape')
        if not shape:
            return None
            
        if shape.get('type') == 'rectangle':
            min_corner = shape.get('min_corner', [0, 0])
            max_corner = shape.get('max_corner', [0, 0])
            return {
                'x_min': min_corner[0],
                'x_max': max_corner[0],
                'y_min': min_corner[1],
                'y_max': max_corner[1]
            }
        elif shape.get('type') == 'circle':
            center = shape.get('center', [0, 0])
            radius = shape.get('radius', 0)
            return {
                'x_min': center[0] - radius,
                'x_max': center[0] + radius,
                'y_min': center[1] - radius,
                'y_max': center[1] + radius
            }
            
        return None
        
    def calculate_distance(self, obj1_id: Any, obj2_id: Any) -> Optional[float]:
        """
        计算两个对象中心点之间的距离
        
        Args:
            obj1_id: 第一个对象ID
            obj2_id: 第二个对象ID
            
        Returns:
            欧几里得距离，如果任一对象不存在则返回 None
        """
        pos1 = self.get_object_position(obj1_id)
        pos2 = self.get_object_position(obj2_id)
        
        if pos1 is None or pos2 is None:
            return None
            
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
        
    def is_colliding(self, obj1_id: Any, obj2_id: Any) -> bool:
        """
        检查两个对象是否发生碰撞
        
        Args:
            obj1_id: 第一个对象ID
            obj2_id: 第二个对象ID
            
        Returns:
            如果对象碰撞则返回 True，否则返回 False
        """
        bounds1 = self.get_object_bounds(obj1_id)
        bounds2 = self.get_object_bounds(obj2_id)
        
        if bounds1 is None or bounds2 is None:
            return False
            
        # 检查边界框是否重叠
        return not (bounds1['x_max'] < bounds2['x_min'] or 
                   bounds1['x_min'] > bounds2['x_max'] or
                   bounds1['y_max'] < bounds2['y_min'] or
                   bounds1['y_min'] > bounds2['y_max'])
                   
    def find_objects_in_radius(self, center_id: Any, radius: float, 
                              object_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        查找指定半径内的对象
        
        Args:
            center_id: 中心对象ID
            radius: 搜索半径
            object_type: 可选的对象类型过滤
            
        Returns:
            在指定半径内的对象列表，每个对象包含距离信息
        """
        center_pos = self.get_object_position(center_id)
        if center_pos is None:
            return []
            
        nearby_objects = []
        
        # 获取所有对象
        config = self.task_context.get_config()
        environment = config.get('environment', {})
        scene_config = environment.get('scene_config', {})
        nodes = scene_config.get('nodes', [])
        
        for node in nodes:
            obj_id = node.get('id')
            if obj_id == center_id:
                continue
                
            # 类型过滤
            if object_type:
                node_type = node.get('properties', {}).get('type')
                if node_type != object_type:
                    continue
                    
            # 计算距离
            obj_pos = self.get_object_position(obj_id)
            if obj_pos is None:
                continue
                
            distance = math.sqrt((center_pos[0] - obj_pos[0])**2 + (center_pos[1] - obj_pos[1])**2)
            
            if distance <= radius:
                nearby_objects.append({
                    'object': node,
                    'distance': distance,
                    'object_id': obj_id
                })
                
        # 按距离排序
        nearby_objects.sort(key=lambda x: x['distance'])
        return nearby_objects
        
    def find_objects_in_rectangle(self, x_min: float, y_min: float, 
                                 x_max: float, y_max: float,
                                 object_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        查找指定矩形区域内的对象
        
        Args:
            x_min, y_min, x_max, y_max: 矩形区域边界
            object_type: 可选的对象类型过滤
            
        Returns:
            在指定区域内的对象列表
        """
        objects_in_area = []
        
        # 获取所有对象
        config = self.task_context.get_config()
        environment = config.get('environment', {})
        scene_config = environment.get('scene_config', {})
        nodes = scene_config.get('nodes', [])
        
        for node in nodes:
            obj_id = node.get('id')
            
            # 类型过滤
            if object_type:
                node_type = node.get('properties', {}).get('type')
                if node_type != object_type:
                    continue
                    
            # 检查是否在区域内
            bounds = self.get_object_bounds(obj_id)
            if bounds is None:
                continue
                
            # 检查边界框是否与搜索区域重叠
            if not (bounds['x_max'] < x_min or bounds['x_min'] > x_max or
                   bounds['y_max'] < y_min or bounds['y_min'] > y_max):
                objects_in_area.append(node)
                
        return objects_in_area
        
    def get_nearest_object(self, target_id: Any, object_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取距离指定对象最近的对象
        
        Args:
            target_id: 目标对象ID
            object_type: 可选的对象类型过滤
            
        Returns:
            最近的对象信息，包含距离，如果没有找到则返回 None
        """
        nearby = self.find_objects_in_radius(target_id, float('inf'), object_type)
        return nearby[0] if nearby else None
        
    def check_path_clearance(self, start_pos: Tuple[float, float], 
                           end_pos: Tuple[float, float], 
                           clearance_radius: float = 0.0) -> bool:
        """
        检查路径是否畅通（无碰撞）
        
        Args:
            start_pos: 起始位置 (x, y)
            end_pos: 结束位置 (x, y)
            clearance_radius: 路径周围的清除半径
            
        Returns:
            如果路径畅通则返回 True，否则返回 False
        """
        # 简化的路径检查：检查路径线段与所有对象的碰撞
        config = self.task_context.get_config()
        environment = config.get('environment', {})
        scene_config = environment.get('scene_config', {})
        nodes = scene_config.get('nodes', [])
        
        for node in nodes:
            obj_id = node.get('id')
            bounds = self.get_object_bounds(obj_id)
            
            if bounds is None:
                continue
                
            # 检查路径线段是否与对象边界框相交
            if self._line_intersects_rectangle(start_pos, end_pos, bounds, clearance_radius):
                return False
                
        return True
        
    def _line_intersects_rectangle(self, start: Tuple[float, float], 
                                 end: Tuple[float, float],
                                 bounds: Dict[str, float], 
                                 clearance: float = 0.0) -> bool:
        """
        检查线段是否与矩形相交（内部方法）
        
        Args:
            start: 线段起始点
            end: 线段结束点
            bounds: 矩形边界
            clearance: 清除距离
            
        Returns:
            如果相交则返回 True，否则返回 False
        """
        # 扩展边界以包含清除距离
        x_min = bounds['x_min'] - clearance
        x_max = bounds['x_max'] + clearance
        y_min = bounds['y_min'] - clearance
        y_max = bounds['y_max'] + clearance
        
        # 使用分离轴定理检查线段与矩形的相交
        # 简化的实现：检查线段端点是否在矩形内，或者线段是否与矩形边相交
        
        # 检查端点是否在矩形内
        if (x_min <= start[0] <= x_max and y_min <= start[1] <= y_max) or \
           (x_min <= end[0] <= x_max and y_min <= end[1] <= y_max):
            return True
            
        # 检查线段是否与矩形边相交（简化版本）
        # 这里可以添加更复杂的线段-矩形相交检测算法
        
        return False
        
    def get_spatial_summary(self) -> Dict[str, Any]:
        """
        获取空间摘要信息
        
        Returns:
            包含空间统计信息的字典
        """
        config = self.task_context.get_config()
        environment = config.get('environment', {})
        scene_config = environment.get('scene_config', {})
        nodes = scene_config.get('nodes', [])
        
        # 统计信息
        total_objects = len(nodes)
        object_types = {}
        spatial_bounds = {'x_min': float('inf'), 'x_max': float('-inf'),
                         'y_min': float('inf'), 'y_max': float('-inf')}
        
        for node in nodes:
            obj_type = node.get('properties', {}).get('type', 'unknown')
            object_types[obj_type] = object_types.get(obj_type, 0) + 1
            
            bounds = self.get_object_bounds(node.get('id'))
            if bounds:
                spatial_bounds['x_min'] = min(spatial_bounds['x_min'], bounds['x_min'])
                spatial_bounds['x_max'] = max(spatial_bounds['x_max'], bounds['x_max'])
                spatial_bounds['y_min'] = min(spatial_bounds['y_min'], bounds['y_min'])
                spatial_bounds['y_max'] = max(spatial_bounds['y_max'], bounds['y_max'])
                
        return {
            'total_objects': total_objects,
            'object_types': object_types,
            'spatial_bounds': spatial_bounds if spatial_bounds['x_min'] != float('inf') else None
        } 