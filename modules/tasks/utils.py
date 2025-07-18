from typing import Dict, Any


def perform_feasibility_check(task_goal: Dict[str, Any], scenario_data: Dict[str, Any]) -> bool:
    """
    执行具体的合法性检查。
    这是一个纯函数，接收目标和场景数据，返回布尔值。
    """
    # 1. 目标对象存在性检查
    target = task_goal.get("target", {})
    cat = target.get("category")
    typ = target.get("type")
    # 从完整的场景数据中获取环境物件数量
    env_counts = scenario_data.get("environment_counts", {})
    if not cat or env_counts.get(cat, {}).get(typ, 0) < 1:
        print(f"合法性检查失败：目标 {cat}/{typ} 在场景中不存在。")
        return False

    # 2. 成功条件中的定位检查
    success_value = task_goal.get("success_condition", {}).get("value")
    if isinstance(success_value, dict):
        loc_cat, loc_typ = success_value.get("category"), success_value.get("type")
        # 从完整的场景数据中获取地图节点
        nodes = scenario_data.get("map_server_config", {}) \
            .get("scene_config", {}) \
            .get("nodes", [])
        if not any(n.get("properties", {}).get("category") == loc_cat and
                   n.get("properties", {}).get("type") == loc_typ for n in nodes):
            print(f"合法性检查失败：定位点 {loc_cat}/{loc_typ} 在场景地图中不存在。")
            return False

    return True