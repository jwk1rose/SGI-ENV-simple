import json
import random
from typing import Dict, List, Optional

# 导入框架基础
from modules.scenario_builder import EntityTemplateLibrary
from modules.scenario_builder import BaseScenarioBuilder

import networkx as nx


class UrbanScenarioBuilder(BaseScenarioBuilder):
    """
    一个具体的场景构建器，其输出格式直接满足 MapServer 的初始化需求。
    """

    def __init__(self,
                 bounds: Dict[str, float],
                 template_library: EntityTemplateLibrary,
                 counts: Dict[str, Dict[str, int]]):
        super().__init__(bounds, template_library, start_id=101)
        self.counts = counts
        # 修正此处，使用空字典而非列表
        self._buildings_by_type: Dict[str, List[Dict]] = {}

    def _create_child_node(self,
                           category: str,
                           key: str,
                           label: str,
                           parent_node: Dict,
                           custom_props: Optional[Dict] = None) -> Optional[Dict]:
        """在父节点内部创建和放置新节点。"""
        try:
            template = self.template_lib.get_template(category, key)
        except KeyError as e:
            print(f"Error: {e}")
            return None

        width, height = template.get("shape_size", (1, 1))
        parent_shape = parent_node['shape']
        if not parent_shape:
            return None

        buffer = 1.0
        pos_x = random.uniform(
            parent_shape['min_corner'][0] + buffer,
            parent_shape['max_corner'][0] - width - buffer
        )
        pos_y = random.uniform(
            parent_shape['min_corner'][1] + buffer,
            parent_shape['max_corner'][1] - height - buffer
        )
        shape = {
            "type": "rectangle",
            "min_corner": [pos_x, pos_y],
            "max_corner": [pos_x + width, pos_y + height]
        }

        node_id = self._get_unique_id()
        properties = template.copy()
        properties['label'] = label
        if custom_props:
            properties.update(custom_props)

        node = {"id": node_id, "properties": properties, "shape": shape}
        self.nodes.append(node)
        return node

    def _generate_buildings(self):
        """生成所有建筑物节点。"""
        print("--> Step 1: Generating all building nodes...")
        building_counts = self.counts.get("building", {})
        for key, count in building_counts.items():
            for i in range(count):
                label = f"{key.replace('_', ' ').title()}-{i + 1}"
                node = self._create_node_from_template("building", key, label)
                if node:
                    # 使用 setdefault 将 key 初始化为列表
                    self._buildings_by_type.setdefault(key, []).append(node)

    def _generate_robots_and_props(self):
        """统一生成所有子节点（机器人和道具）。"""
        print("--> Step 2: Generating robots and props inside buildings...")

        # --- 生成机器人 ---
        robot_counts = self.counts.get("robot", {})
        # 所有机器人都从 'robot_base' 出发
        home_base_map = {key: "robot_base" for key in robot_counts.keys()}

        for key, count in robot_counts.items():
            for i in range(count):
                home_base_type = home_base_map[key]
                parents = self._buildings_by_type.get(home_base_type, [])
                if not parents:
                    print(
                        f"  [Warning] Cannot create '{key}' because its required "
                        f"parent building '{home_base_type}' was not generated. Skipping."
                    )
                    continue
                home_base_node = random.choice(parents)

                # 强制机器人带上初始 status=idle
                tmpl = self.template_lib.get_template("robot", key)
                tmpl_label = f"{tmpl['type']}-{i + 1}"
                custom_props = {"status": "idle"}

                robot_node = self._create_child_node(
                    "robot",
                    key,
                    tmpl_label,
                    home_base_node,
                    custom_props=custom_props
                )
                if robot_node:
                    self.edges.append({
                        "source": robot_node['id'],
                        "target": home_base_node['id'],
                        "type": "stationed_at"
                    })

        # --- 生成道具 ---
        prop_counts = self.counts.get("prop", {})

        # 放置车辆 (car, truck)
        for key in ("car", "truck"):
            for i in range(prop_counts.get(key, 0)):
                parking_nodes = self._buildings_by_type.get("parking_lot", [])
                if not parking_nodes:
                    print(f"  [Warning] Cannot create '{key}' because 'parking_lot' missing. Skipping.")
                    continue
                parking = random.choice(parking_nodes)
                plate = f"F-{random.randint(1000, 9999)}"
                prop_node = self._create_child_node(
                    "prop", key, f"{key}-{plate}", parking, {"license_plate": plate}
                )
                if prop_node:
                    self.edges.append({
                        "source": prop_node['id'],
                        "target": parking['id'],
                        "type": "parked_at"
                    })

        # 放置货物 (cargo)
        for i in range(prop_counts.get("cargo", 0)):
            rb_nodes = self._buildings_by_type.get("residential_building", [])
            if not rb_nodes:
                print("  [Warning] Cannot create 'cargo' because 'residential_building' missing. Skipping.")
                continue
            parent = random.choice(rb_nodes)
            weight = round(random.uniform(5, 50), 2)
            cargo_node = self._create_child_node(
                "prop", "cargo", f"Cargo-{i+1}", parent, {"weight_kg": weight}
            )
            if cargo_node:
                self.edges.append({
                    "source": cargo_node['id'],
                    "target": parent['id'],
                    "type": "stored_at"
                })

        # 放置逻辑异常 (equipment_failure, security_breach)
        for key in ("equipment_failure", "security_breach"):
            for i in range(prop_counts.get(key, 0)):
                if not self._buildings_by_type:
                    print(f"  [Warning] No buildings exist; cannot place anomaly '{key}'. Skipping.")
                    continue
                btype = random.choice(list(self._buildings_by_type.keys()))
                parent = random.choice(self._buildings_by_type[btype])
                anomaly_id = self._get_unique_id()
                props = self.template_lib.get_template("prop", key)
                props['label'] = f"{key.replace('_', ' ').title()}-{anomaly_id}"
                node = {"id": anomaly_id, "properties": props, "shape": None}
                self.nodes.append(node)
                self.edges.append({
                    "source": anomaly_id,
                    "target": parent['id'],
                    "type": "located_at"
                })

    def _generate_connectivity_edges(self):
        """创建连通的建筑网络。"""
        print("--> Step 3: Generating building connectivity graph...")
        all_buildings = [n for typ in self._buildings_by_type.values() for n in typ]
        if len(all_buildings) < 2:
            return

        G = nx.Graph()
        for b in all_buildings:
            center_x = (b['shape']['min_corner'][0] + b['shape']['max_corner'][0]) / 2
            center_y = (b['shape']['min_corner'][1] + b['shape']['max_corner'][1]) / 2
            G.add_node(b['id'], pos=(center_x, center_y))

        for i in range(len(all_buildings)):
            for j in range(i + 1, len(all_buildings)):
                u, v = all_buildings[i], all_buildings[j]
                pu, pv = G.nodes[u['id']]['pos'], G.nodes[v['id']]['pos']
                dist = ((pu[0] - pv[0]) ** 2 + (pu[1] - pv[1]) ** 2) ** 0.5
                G.add_edge(u['id'], v['id'], weight=dist)

        T = nx.minimum_spanning_tree(G)
        for u, v in T.edges():
            self.edges.append({"source": u, "target": v, "type": "reachable_from"})
            self.edges.append({"source": v, "target": u, "type": "reachable_from"})

    def build(self):
        """实现构建城市场景的核心逻辑。"""
        print("--- Building Urban Scenario ---")
        self._generate_buildings()
        self._generate_robots_and_props()
        self._generate_connectivity_edges()
        print(f"--- Raw Data Generation Complete: {len(self.nodes)} nodes and {len(self.edges)} edges. ---")

    def get_result(self) -> Dict[str, Dict]:
        """获取场景数据，并将其格式化为 MapServer 所需的配置。"""
        print("--> Final Step: Formatting data for MapServer with layering info...")
        scene_config = {"nodes": self.nodes, "edges": self.edges}

        initial_physical_objects = []
        STATIC_TYPES = {tpl['type'] for tpl in self.template_lib._templates['building'].values()}

        for node in self.nodes:
            shape = node.get("shape")
            if not shape:
                continue
            ntype = node["properties"]["type"]
            layer = "static" if ntype in STATIC_TYPES else "dynamic"
            initial_physical_objects.append({
                "obj_id": node["id"],
                "parts_shapes": {"body": shape},
                "layer_type": layer
            })

        gridmap_config = {
            "resolution": 1.0,
            "bounds": self.bounds,
            "layers_config": {
                "static":   {"initial_value": 0, "dtype": "uint8"},
                "dynamic":  {"initial_value": 0, "dtype": "uint8"},
                "semantic": {"initial_value": 0, "dtype": "uint32"}
            },
            "initial_objects": initial_physical_objects
        }

        return {"scene_config": scene_config, "gridmap_config": gridmap_config}

    def save_to_file(self, filepath: str):
        """将最终生成的 MapServer 配置保存到 JSON 文件。"""
        cfg = self.get_result()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        print(f"MapServer config saved to '{filepath}'.")
