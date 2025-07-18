"""
GraphHandler - 场景图处理器

负责管理场景图的数据结构、节点关系、路径规划等功能。
移植自原始spine的graph_util.py
"""

import json
from typing import Any, Dict, List, Optional, Tuple, Union
import networkx as nx
import numpy as np
from scipy.spatial.transform import Rotation


EMPTY_GRAPH = {
    "objects": [],
    "regions": [{"name": "ground_1", "coords": [0, 0]}],
    "region_connections": [],
    "object_connections": [],
}


def to_list(x):
    """将字符串或列表转换为列表"""
    if isinstance(x, list):
        return x
    else:
        return x.replace("[", "").replace("]", "").split(",")


def to_float_list(x: str):
    """将字符串转换为浮点数列表"""
    return [float(y) for y in to_list(x)]


def parse_graph_coord(
    coord_as_str: str, origin: np.ndarray, rotation: Optional[Rotation] = None
) -> List[float]:
    """解析图坐标，应用SE2变换
    
    Args:
        coord_as_str: 坐标字符串 `[x, y]`
        origin: 坐标系原点
        rotation: 坐标系旋转
        
    Returns:
        变换后的坐标 `[x, y]`
    """
    coords = np.array(to_float_list(coord_as_str))
    coords = apply_transform(coords, origin=origin, rotation=rotation)
    return [round(float(coords[0]), 1), round(float(coords[1]), 1)]


def apply_transform(
    x: np.ndarray, origin: np.ndarray, rotation: Optional[Rotation] = None
) -> np.ndarray:
    """应用SE2变换到向量x
    
    Args:
        x: R2中的向量
        origin: R2中的原点
        rotation: SO3中的旋转
        
    Returns:
        变换后的向量
    """
    x -= origin
    if rotation is not None:
        x = np.concatenate([x, np.zeros(1)])
        x = rotation.apply(x)
        x = x[:2]
    return x


def parse_graph(
    data: Dict[str, Dict[str, str]],
    custom_data: Optional[Dict[str, Dict[str, str]]] = {},
    rotation: Optional[Rotation] = None,
    utm_origin: Optional[np.ndarray] = None,
    flip_coords=False,
) -> Tuple[nx.Graph, str]:
    """解析场景图数据为NetworkX图对象
    
    Args:
        data: 图数据字典
        custom_data: 自定义数据
        rotation: 当前机器人旋转
        utm_origin: UTM原点
        flip_coords: 是否翻转坐标
        
    Returns:
        NetworkX图和JSON字符串
    """
    origin = np.array([0, 0])
    if utm_origin is not None:
        origin = utm_origin

    if len(custom_data):
        add_keys = ["regions", "region_connections", "objects", "object_connections"]
        for key in add_keys:
            if key in data and key in custom_data:
                data[key].extend(custom_data[key])

    G = nx.Graph()
    
    # 添加对象节点
    for node in data["objects"]:
        coords = parse_graph_coord(node["coords"], origin=origin, rotation=rotation)
        if flip_coords:
            coords = [coords[0], -coords[1]]
        G.add_node(node["name"], coords=coords, type="object")

    # 添加区域节点
    for node in data["regions"]:
        assert "coords" in node, node
        coords = parse_graph_coord(node["coords"], origin=origin, rotation=rotation)
        if flip_coords:
            coords = [coords[0], -coords[1]]
        G.add_node(node["name"], coords=coords, type="region")

    # 添加对象连接边
    for edge in data["object_connections"]:
        c1 = G.nodes[edge[0]]["coords"]
        c2 = G.nodes[edge[1]]["coords"]
        dist = np.linalg.norm(np.array(c1) - np.array(c2))
        G.add_edge(edge[0], edge[1], type="object", weight=dist)

    # 添加区域连接边
    for edge in data["region_connections"]:
        c1 = G.nodes[edge[0]]["coords"]
        c2 = G.nodes[edge[1]]["coords"]
        dist = np.linalg.norm(np.array(c1) - np.array(c2))
        G.add_edge(edge[0], edge[1], type="region", weight=dist)

    return G, str(data)


class GraphHandler:
    """场景图处理器，管理图结构、节点关系和路径规划"""
    
    def __init__(self, graph_path: str = "", init_node: Union[None, str] = None) -> None:
        """初始化图处理器
        
        Args:
            graph_path: 图文件路径，空字符串则创建空图
            init_node: 初始节点名称
        """
        if graph_path == "":
            self.graph = nx.Graph()
            self.as_json_str = "{}"
            self.current_location = ""
        else:
            with open(graph_path) as f:
                data = json.load(f)
            self.graph, self.as_json_str = parse_graph(data)
            self.current_location = init_node

    def reset(
        self,
        graph_as_json: str,
        current_location: Optional[str] = "",
        rotation: Optional[Rotation] = None,
        utm_origin: Optional[np.ndarray] = None,
        custom_data: Optional[Dict[str, Dict[str, str]]] = {},
        flip_coords=False,
    ) -> bool:
        """重置图数据
        
        Args:
            graph_as_json: JSON格式的图数据
            current_location: 当前位置
            rotation: 旋转
            utm_origin: UTM原点
            custom_data: 自定义数据
            flip_coords: 是否翻转坐标
            
        Returns:
            是否成功重置
        """
        try:
            data = json.loads(graph_as_json)

            if self.current_location is None or self.current_location == "":
                self.current_location = current_location

            self.graph, self.as_json_str = parse_graph(
                data,
                rotation=rotation,
                utm_origin=utm_origin,
                custom_data=custom_data,
                flip_coords=flip_coords,
            )
            self.as_json_str = self.to_json_str()
        except Exception as ex:
            print(f"\nexception: {ex}")
            return False
        return True

    def to_json_str(self, extra_data={}) -> str:
        """将图转换为JSON字符串
        
        Args:
            extra_data: 额外数据
            
        Returns:
            JSON字符串
        """
        added_edges = set()
        graph_dict = {
            "objects": [],
            "regions": [],
            "object_connections": [],
            "region_connections": [],
        }
        
        for node in self.graph.nodes:
            node_type = self.graph.nodes[node]["type"]
            coords = self.graph.nodes[node]["coords"]
            coords = f"[{coords[0]:0.1f}, {coords[1]:0.1f}]"
            graph_dict[f"{node_type}s"].append({"name": node, "coords": coords})

            for neighbor in self.get_neighbors(node):
                if tuple(sorted((node, neighbor))) not in added_edges:
                    graph_dict[f"{node_type}_connections"].append(
                        sorted([node, neighbor])
                    )
                    added_edges.add(tuple(sorted((node, neighbor))))

        if self.current_location is not None:
            graph_dict["current_location"] = self.current_location

        graph_dict.update(extra_data)
        return json.dumps(graph_dict, indent=2)

    def update_location(self, new_location: str) -> bool:
        """更新当前位置
        
        Args:
            new_location: 新位置
            
        Returns:
            是否成功更新
        """
        if not self.contains_node(new_location):
            return False
        self.current_location = new_location
        return True

    def get_neighbors_by_type(
        self, node: str, node_type: Optional[str] = ""
    ) -> Dict[str, List[str]]:
        """获取指定类型的邻居节点
        
        Args:
            node: 节点名称
            node_type: 节点类型，空字符串表示所有类型
            
        Returns:
            邻居节点字典
        """
        ret_val = {}
        if node in self.graph.nodes:
            neighbors = list(self.graph.neighbors(node))

            for neighbor in neighbors:
                if node_type == "":
                    ret_val[neighbor] = self.lookup_node(neighbor)[0]
                elif (
                    node_type != "" and self.lookup_node(neighbor)[0]["type"] == node_type
                ):
                    ret_val[neighbor] = self.lookup_node(neighbor)[0]

        return ret_val

    def get_edges(self, node: str) -> Dict[str, List[str]]:
        """获取节点的边
        
        Args:
            node: 节点名称
            
        Returns:
            边字典
        """
        out = {}
        for edge in self.graph.edges(node):
            out[edge] = self.graph.edges[edge]
        return out

    def lookup_object(
        self, node: str
    ) -> Tuple[Tuple[str, Dict], Tuple[str, Dict], bool]:
        """查找对象及其连接的区域
        
        Args:
            node: 节点名称
            
        Returns:
            (对象名称, 对象属性), (区域名称, 区域属性), 是否找到完整信息
        """
        if node in self.graph.nodes and self.graph.nodes[node]["type"] == "object":
            node_attr = self.graph.nodes[node]
            neighbors = list(self.graph.neighbors(node))

            if len(neighbors) >= 1:
                region_attr = self.graph.nodes[neighbors[0]]
                return (
                    (node, node_attr),
                    (neighbors[0], region_attr),
                    True,
                )
            else:
                return (node, node_attr), (None, None), False

        return (None, None), (None, None), False

    def get_neighbors(self, node_name: str) -> List[str]:
        """获取邻居节点
        
        Args:
            node_name: 节点名称
            
        Returns:
            邻居节点列表
        """
        if not self.contains_node(node_name):
            return []
        return list(nx.neighbors(self.graph, node_name))

    def get_path(
        self, start_node, end_node, only_regions: Optional[bool] = False
    ) -> List[str]:
        """获取最短路径
        
        Args:
            start_node: 起始节点
            end_node: 目标节点
            only_regions: 是否只考虑区域节点
            
        Returns:
            路径节点列表
        """
        return nx.shortest_path(self.graph, start_node, end_node)

    def contains_node(self, node: str) -> bool:
        """检查节点是否存在
        
        Args:
            node: 节点名称
            
        Returns:
            是否存在
        """
        return node in self.graph.nodes

    def path_exists_from_current_loc(self, target: str) -> bool:
        """检查从当前位置到目标是否存在路径
        
        Args:
            target: 目标节点
            
        Returns:
            是否存在路径
        """
        assert self.current_location is not None, "current location is unknown"
        return nx.has_path(self.graph, self.current_location, target)

    def lookup_node(self, node: str) -> Tuple[Dict, bool]:
        """查找节点
        
        Args:
            node: 节点名称
            
        Returns:
            (节点属性, 是否找到)
        """
        if self.contains_node(node):
            return self.graph.nodes[node], True
        else:
            return {}, False

    def get_node_coords(self, node: str) -> Tuple[np.ndarray, bool]:
        """获取节点坐标
        
        Args:
            node: 节点名称
            
        Returns:
            (坐标, 是否找到)
        """
        if self.contains_node(node):
            return self.graph.nodes[node]["coords"], True
        else:
            return np.zeros(2), False

    def update_node_description(self, node, **attrs) -> None:
        """更新节点描述
        
        Args:
            node: 节点名称
            **attrs: 要更新的属性
        """
        self.graph.nodes[node].update(attrs)

    def get_node_type(self, node: str) -> str:
        """获取节点类型
        
        Args:
            node: 节点名称
            
        Returns:
            节点类型
        """
        node_info, success = self.lookup_node(node)
        if success and "type" in node_info:
            return node_info["type"]
        else:
            return ""

    def update_with_node(
        self,
        node: str,
        edges: List[str],
        attrs: Dict[str, Any] = {},
    ) -> None:
        """更新节点及其边
        
        Args:
            node: 节点名称
            edges: 连接的边
            attrs: 节点属性
        """
        assert "type" in attrs and "coords" in attrs
        self.graph.add_node(node, **attrs)
        for edge in edges:
            c1 = self.graph.nodes[node]["coords"]
            c2 = self.graph.nodes[edge]["coords"]
            dist = np.linalg.norm(np.array(c1) - np.array(c2))
            self.graph.add_edge(
                node, edge, type=self.graph.nodes[node]["type"], weight=dist
            )

    def update_with_edge(self, edge: Tuple[str, str], attrs: Dict[str, Any] = {}):
        """更新边
        
        Args:
            edge: 边元组
            attrs: 边属性
        """
        self.graph.add_edge(edge[0], edge[1], **attrs)

    def remove_edge(self, start: str, end: str) -> None:
        """删除边
        
        Args:
            start: 起始节点
            end: 结束节点
        """
        try:
            self.graph.remove_edge(start, end)
        except Exception as ex:
            return

    def get_region_nodes_and_locs(self) -> Tuple[np.ndarray, np.ndarray]:
        """获取区域节点及其位置
        
        Returns:
            (区域节点数组, 区域位置数组)
        """
        region_nodes_locs = []
        region_nodes = []

        for node in self.graph.nodes:
            if self.graph.nodes[node]["type"] == "region":
                node_loc = self.graph.nodes[node]["coords"]
                region_nodes_locs.append(node_loc)
                region_nodes.append(node)

        self.region_nodes = np.array(region_nodes)
        self.region_node_locs = np.array(region_nodes_locs)

        return self.region_nodes, self.region_node_locs

    def get_closest_reachable_node(
        self, goal_node: str, current_node: Optional[str] = None
    ) -> Tuple[str, str]:
        """获取从当前节点到目标节点的最近可达节点
        
        Args:
            goal_node: 目标节点
            current_node: 当前节点，None则使用当前位置
            
        Returns:
            (最近可达节点, 目标节点)
        """
        if current_node is None:
            assert self.current_location is not None, "current_location must be set"
            current_node = self.current_location

        nodes_reachable_from_curr_loc = list(
            nx.node_connected_component(self.graph, current_node)
        )
        nodes_reachable_from_goal = list(
            nx.node_connected_component(self.graph, goal_node)
        )

        # 只考虑区域节点
        nodes_reachable_from_curr_loc = [
            n
            for n in nodes_reachable_from_curr_loc
            if self.get_node_type(n) == "region"
        ]
        nodes_reachable_from_goal = [
            n for n in nodes_reachable_from_goal if self.get_node_type(n) == "region"
        ]

        coords_of_nodes_reachable_curr_loc = np.array(
            [self.get_node_coords(n)[0] for n in nodes_reachable_from_curr_loc]
        )

        closest_node_dist = np.inf
        closest_node_id = current_node
        target_node_id = goal_node
        
        for node_reachable_from_goal in nodes_reachable_from_goal:
            node_dists = np.linalg.norm(
                coords_of_nodes_reachable_curr_loc
                - np.array(self.get_node_coords(node_reachable_from_goal)[0]),
                axis=-1,
            )

            if node_dists.min() < closest_node_dist:
                closest_node_dist = node_dists.min()
                closest_node_id = nodes_reachable_from_curr_loc[node_dists.argmin()]
                target_node_id = node_reachable_from_goal

        return closest_node_id, target_node_id

    def __str__(self) -> str:
        """字符串表示"""
        out = f"Nodes\n---\n"
        for node in self.graph.nodes:
            attrs, _ = self.lookup_node(node)
            out += f"\t{node}: {attrs}\n"

        object_edges = ""
        region_edges = ""
        for edge in self.graph.edges:
            if "object" in [self.get_node_type(e) for e in edge]:
                object_edges += f"\t[{edge[0]}, {edge[1]}]\n"
            else:
                region_edges += f"\t[{edge[0]}, {edge[1]}]\n"

        out += f"\nObject edges\n---\n"
        out += object_edges + "\n"

        out += f"Region edges:\n---\n"
        out += region_edges
        return out 