# SGI: Swarm General Intelligence Dataset

## 概述

SGI 数据集（Swarm General Intelligence Dataset）是由 Windy Lab 发布的多智能体群体智能基准数据集，旨在验证和推进通用集群智能研究。数据集包含多种城市与乡村场景，以及场景中可能出现的突发新情况，辅助多智能体系统的仿真、规划与协同策略评估。

## 元数据

| 字段       | 值                                                 |
| -------- |---------------------------------------------------|
| **名称**   | SGI Dataset: Swarm General Intelligence Dataset          |
| **版本**   | 1.0.0                                             |
| **作者**   | Windy Lab                                         |
| **许可证**  | MIT                                               |
| **描述**   | 用于验证通用群体智能的基准数据集，涵盖多样化场景及新情况，提供结构化任务定义、环境统计与地图配置。 |
| **创建日期** | 2025-07-02                                        |

## 仓库结构

```plaintext
dataset/                           # 根目录
├── metadata.json                  # 全局元数据
├── README.md                      # 本文件
├── goals/                         # 任务目标定义目录
│   └── {type}/
│       └── goals.json             # 任务目标列表
├── scenarios/                     # 场景配置目录
│   └── {type}/
│       └── {scenario_id}/
│           ├── environment_counts.json  # 场景统计信息
│           ├── map_server_config.json   # 场景配置详细信息
│           └── scenario_dashboard.png   # 场景渲染图片
├── tasks/                         # 任务定义目录 (包括一个场景+目标)
│   └── {type}/
│       └── {task_id}.json         # 不同类型的任务列表
└── loader.py/                          # 外部读取数据集的接口
```


## 使用示例

```python
from dataset.loader import load_dataset

# 使用默认路径
ds = load_dataset()

# 列出所有场景类型
types = ds.list_types()
print(types)

# 获取某类型任务列表
goals = ds.get_goals("urban")
print(goals)

#获取所有的任务列表
tasks=ds.tasks
print(tasks)

# 列出某类型的场景ID
scenarios = ds.list_scenarios("urban")
print(scenarios)

# 获取指定场景的配置
scenario = ds.get_scenario("urban", "1")
print(scenario)
```

