import json
import os
import argparse

from modules.scenario_builder import EntityTemplateLibrary
from modules.scenario_builder import ScenarioVisualizer
from modules.scenario_builder import UrbanScenarioBuilder

if __name__ == '__main__':
    # --- 0. 解析命令行参数 ---
    parser = argparse.ArgumentParser(description="批量生成城市场景")
    parser.add_argument('-n', '--num', type=int, default=5, help='要生成的场景数量，默认为1')
    args = parser.parse_args()
    num_scenarios = max(1, args.num)

    # --- 1. 初始化真实的实体库 ---
    library = EntityTemplateLibrary()

    # --- 2. 定义一个与 entity_library.py 匹配的、逻辑一致的 COUNTS 字典 ---
    COUNTS = {
        "building": {
            "residential_building": 5,  # 为 ground_vehicle 和 cargo 提供场所
            "power_station": 1,
            "parking_lot": 1,  # 为 car 和 truck 提供场所
            "hospital": 1,  # 一个独立的建筑
            "shopping_mall": 1,  # 一个独立的建筑
            "park": 1,  # 一个独立的建筑
            "robot_base": 1  # 一个独立的基地
        },
        "robot": {
            "drone": 4,
            "ground_vehicle": 2
        },
        "prop": {
            "car": 1,
            "truck": 1,
            "cargo": 5,
            "equipment_failure": 2,
            "security_breach": 2
        }
    }

    WORLD_BOUNDS = {"x_min": 0, "x_max": 5000, "y_min": 0, "y_max": 5000}

    # --- 3. 获取输出目录和下一个编号 ---
    from modules.utils import get_project_root
    output_dir = get_project_root() / "dataset" / "scenarios" / "urban"
    output_dir.mkdir(parents=True, exist_ok=True)
    existing_dirs = [d for d in output_dir.iterdir() if d.is_dir()]
    next_index = len(existing_dirs) + 1

    for i in range(num_scenarios):
        scenario_index = next_index + i
        scenario_dir = output_dir / f"{scenario_index}"
        scenario_dir.mkdir(parents=True, exist_ok=True)

        # --- 4. 实例化并运行构建器 ---
        urban_builder = UrbanScenarioBuilder(
            bounds=WORLD_BOUNDS,
            template_library=library,
            counts=COUNTS
        )
        urban_builder.build()

        # --- 5. 保存 COUNTS ---
        counts_filepath = os.path.join(scenario_dir, "environment_counts.json")
        with open(counts_filepath, "w", encoding="utf-8") as f:
            json.dump(COUNTS, f, indent=2, ensure_ascii=False)
        print(f"Environment counts saved to '{counts_filepath}'.")

        # --- 6. 保存 MapServer 配置 ---
        config_filepath = os.path.join(scenario_dir, "map_server_config.json")
        urban_builder.save_to_file(config_filepath)

        # --- 7. 验证输出 ---
        final_config = urban_builder.get_result()
        total_nodes = len(final_config['scene_config']['nodes'])
        physical_nodes = len(final_config['gridmap_config']['initial_objects'])
        logical_nodes = total_nodes - physical_nodes

        static_count = sum(1 for obj in final_config['gridmap_config']['initial_objects'] if obj['layer_type'] == 'static')
        dynamic_count = sum(
            1 for obj in final_config['gridmap_config']['initial_objects'] if obj['layer_type'] == 'dynamic')

        print(f"[场景{scenario_index}] Total objects in SceneGraph: {total_nodes}")
        print(f"  - Physical objects in GridMap: {physical_nodes} ({static_count} static, {dynamic_count} dynamic)")
        print(f"  - Logical-only objects: {logical_nodes}")

        print(f"\n✅ Success! The builder logic now matches the entity library, counts and configuration have been saved in '{scenario_dir}'.")

        # --- 8. 可视化场景 ---
        viz = ScenarioVisualizer.load_from_file(scenario_dir / "map_server_config.json", library)
        viz.render_and_save(scenario_dir / "scenario_dashboard.png")
