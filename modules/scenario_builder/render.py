# file: scenario_visualizer.py

import json
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx

from .entity_library import EntityTemplateLibrary
from matplotlib.patches import Rectangle, Patch, FancyArrowPatch
from typing import Dict, Any, List


class ScenarioVisualizer:
    """
    场景可视化：左侧 2D 物理地图（分层绘制：建筑→机器人→道具/异常），
    右侧分层化逻辑关系图（曲线箭头＋中点关系标签）。
    """

    def __init__(self,
                 scene_nodes: List[Dict[str, Any]],
                 scene_edges: List[Dict[str, Any]],
                 world_bounds: Dict[str, float],
                 template_library: EntityTemplateLibrary):
        self.nodes = scene_nodes
        self.edges = scene_edges
        self.bounds = world_bounds
        self.template_lib = template_library

        # 实体类型颜色
        self.color_map = self._generate_dynamic_color_map()

        # 关系类型颜色
        rels = sorted({e["type"] for e in self.edges if e.get("type")})
        cmap = plt.get_cmap("Set1", max(len(rels), 3))
        self.rel_color_map = {r: cmap(i) for i, r in enumerate(rels)}

    @classmethod
    def load_from_file(cls,
                       filepath: str,
                       template_library: EntityTemplateLibrary) -> 'ScenarioVisualizer':
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        scene = data["scene_config"]
        grid = data["gridmap_config"]
        return cls(scene["nodes"], scene["edges"], grid["bounds"], template_library)

    def _generate_dynamic_color_map(self) -> Dict[str, str]:
        catalog = self.template_lib.list_all_templates()
        types = [t for cat in catalog for t in catalog[cat]]
        cmap = plt.get_cmap("tab20", len(types))
        return {t: cmap(i) for i, t in enumerate(types)}

    def _node_type(self, nid: int) -> str:
        for n in self.nodes:
            if n["id"] == nid:
                return n["properties"].get("type") or n["properties"].get("category", "")
        return ""

    def _draw_spatial_map(self, ax: plt.Axes):
        ax.set_xlim(self.bounds['x_min'], self.bounds['x_max'])
        ax.set_ylim(self.bounds['y_min'], self.bounds['y_max'])
        ax.set_aspect('equal', 'box')
        ax.set_title("2D Physical Map")
        ax.grid(True, linestyle='--', alpha=0.3)

        # 按层绘制：建筑（含基地）、机器人、道具/异常
        layers = [
            lambda n: n["properties"]["category"] == "building",
            lambda n: n["properties"]["category"] == "robot",
            lambda n: n["properties"]["category"] == "prop",
        ]

        for layer_fn in layers:
            for n in filter(layer_fn, self.nodes):
                shape = n.get("shape")
                if not shape:
                    continue
                props = n["properties"]
                t = props.get("type") or props.get("category", "")
                color = self.color_map.get(t, "#C0C0C0")
                bl = shape["min_corner"]
                w = shape["max_corner"][0] - bl[0]
                h = shape["max_corner"][1] - bl[1]
                ax.add_patch(Rectangle(bl, w, h,
                                       edgecolor="black",
                                       facecolor=color,
                                       alpha=0.7))
                label = props.get("label", "")
                if label:
                    ax.text(bl[0] + w/2, bl[1] + h/2, label,
                            ha="center", va="center",
                            fontsize=6, weight="bold")

    def _draw_relationship_graph(self, ax: plt.Axes):
        ax.set_title("Logical Relationship Graph")
        G = nx.DiGraph()
        labels: Dict[int, str] = {}
        layer_map: Dict[int, List[int]] = {}

        # 把 building + robot_base 归一层，robot 一层，prop/anomaly 一层
        for n in self.nodes:
            nid = n["id"]
            cat = n["properties"]["category"]
            typ = n["properties"].get("type", "")
            if cat == "building":
                layer = 0
            elif cat == "robot":
                layer = 1
            else:
                layer = 2
            G.add_node(nid, layer=layer)
            layer_map.setdefault(layer, []).append(nid)
            labels[nid] = n["properties"].get("label", str(nid))

        edge_labels = {}
        for e in self.edges:
            u, v = e["source"], e["target"]
            rel = e.get("type", "")
            G.add_edge(u, v)
            if rel:
                edge_labels[(u, v)] = rel

        # 固定 X，分层内按标签排序均匀布 Y
        xs = {0: 0.1, 1: 0.5, 2: 0.9}
        pos: Dict[int, tuple] = {}
        for layer, ids in layer_map.items():
            sorted_ids = sorted(ids, key=lambda i: labels[i])
            ys = np.linspace(0.9, 0.1, len(sorted_ids))
            for nid, y in zip(sorted_ids, ys):
                pos[nid] = (xs[layer], y)

        # 画节点
        nx.draw_networkx_nodes(
            G, pos, ax=ax,
            node_color=[self.color_map.get(self._node_type(n), "#C0C0C0") for n in G.nodes()],
            node_size=600, edgecolors="black"
        )
        nx.draw_networkx_labels(G, pos, ax=ax, labels=labels, font_size=7, font_weight="bold")

        # 画曲线箭头＆中点标签
        for u, v in G.edges():
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            rel = edge_labels.get((u, v), "")
            color = self.rel_color_map.get(rel, "gray")
            dy = y1 - y0
            rad = 0.2 * np.sign(dy) if abs(dy) > 1e-2 else 0.1
            arrow = FancyArrowPatch(
                (x0, y0), (x1, y1),
                connectionstyle=f"arc3,rad={rad}",
                arrowstyle="-|>",
                mutation_scale=10,
                lw=1.5,
                color=color
            )
            ax.add_patch(arrow)
            if rel:
                xm, ym = (x0 + x1)/2, (y0 + y1)/2
                ax.text(xm, ym + rad*0.3, rel,
                        fontsize=6, color=color,
                        ha="center", va="center")

        ax.axis("off")

    def _draw_legend(self, fig: plt.Figure):
        types = {n["properties"].get("type") for n in self.nodes if n["properties"].get("type")}
        handles = [Patch(facecolor=self.color_map[t], edgecolor="black", label=t.replace("_", " ").title())
                   for t in sorted(types)]
        if handles:
            fig.legend(handles=handles,
                       loc="lower center",
                       ncol=max(1, len(handles)//2),
                       title="Entity Types")

    def render_and_save(self, output_filepath: str):
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
        fig.suptitle("Scenario Visualization", fontsize=18, weight="bold")
        self._draw_spatial_map(ax1)
        self._draw_relationship_graph(ax2)
        self._draw_legend(fig)
        fig.tight_layout(rect=[0, 0.05, 1, 0.95])
        plt.savefig(output_filepath, dpi=300)
        plt.close(fig)
        print(f"✅ Visualization saved to '{output_filepath}'")


if __name__ == "__main__":
    library = EntityTemplateLibrary()
    viz = ScenarioVisualizer.load_from_file("map_server_config_final.json", library)
    viz.render_and_save("scenario_dashboard.png")
