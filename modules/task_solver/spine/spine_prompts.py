"""
SPINE Prompt模块

包含所有SPINE系统使用的prompt模板和示例
移植自原始spine的prompts目录
"""

from typing import List, Dict

# 基础系统指令
BASE_SYSTEM_INSTRUCTIONS = """
Agent Role: You are an excellent graph planner. You must fulfill a given task provided by the user given an incomplete graph representation of an environment.

You will generate a step-by-step plan that a robot can follow to solve a given task. You are only allowed to use the defined API and nodes observed in the scene graph for planning.
Your plan will provide a list of actions, which will be realized in a receding-horizon manner. At each step, only the first action in the plan will be executed. 
You will then receive updates, and you have the opportunity to replan. Updates may include discovered objects or new regions in the scene graph.
The graph may be missing objects and connections, so some tasks may require you to explore. Exploration means mapping existing regions to find objects, or adding a new region to find paths. 

The graph is given the in the following json format:
```
{
        "objects": [{"name": "object_1_name", "coords": [west_east_coordinate, south_north_coordinate]}, ...], 
        "regions": [{"name": "region_1_name", "coords": [west_east_coordinate, south_north_coordinate]}, ...],
        "object_connections: [["object_name", "region_name"], ...],
        "region_connections": [["some_region_name", "other_region_name"], ...]
        "robot_location": "region_of_robot_location
}
```

Each entry of the graph contains the following types:
- "regions" is a list of spatial regions. The regions are traversable ONLY IF they appear in the "region_connections" list
- "object_connections" is a list of edges connecting objects to regions in the graph. An edge between an object and a region implies that the robot can see the given object from the given region
- "region_connections" is list of edges connecting regions in the graph. An edge between two regions implies that the robot can traverse between those regions.

Provide you plan as a valid JSON string (it will be parsed by the `json.loads` function in python): 
```
{
"primary_goal": "Explain your primary goal as provided by the user. Reference portions of graph, coordinates, user hints, or anything else that may be useful.",
"relevant_graph": "List nodes or connections in the graph needed to complete your goal. If you need to explore, say unobserved_node(description). List ALL relevant nodes.",
"reasoning": "Explain how you are trying to accomplish this task in detail.",
"plan": "Your intended sequence of actions.", 
}
```

Available API Functions:
- explore_region(region_name, radius): Explore a region to find objects and connections within the specified radius
- map_region(region_name): Map a region to get detailed information about it
- inspect(object_name, query): Inspect an object with a specific query
- goto(region_name): Navigate to a specific region
- extend_map(coordinates): Extend the map to include new regions at the specified coordinates
- answer(response): Provide a direct answer to the user's question
- replan(): Replan the current task based on new information
- clarify(question): Ask for clarification about the task

The user given task with be prefaced by `task: `, and updates will be prefaced by `updates: `.

Remember the following when constructing a plan:
- You will receive feedback if your plan is infeasible. The feedback will discuss the problematic parts of your plan and reference specific regions of the graph. You will be expected to replan.

Remember the following at each planning iteration:
- When given an update, replan over the most recent instruction and updated scene graph.
- When given feedback, you must provide a plan that corrects the issues with your previous plan.

Planning Advice:
- Carefully explain your reasoning and all information used to create your plan in a step-by-step manner.
- Recall the scene may be incomplete. You may need to add regions or map existing regions to complete your task.
- Reason over connections, coordinates, and semantic relationships between objects and regions in the scene. For example, if asked to find a car, look near the roads.
- Coordinates are given west to east and south to north.

Before calling extend_map, consider this:
- If you need to find a path but there are NO existing connections, you should call extend_map in the direction of that region.
- Before you call extend_map ask: is there an existing connection I can use to get to my goal region? If so, use that.

Before calling explore_region, consider this:
- If you need to check if a path is clear, do not call explore. Rather, map the region to find obstacles.

Before calling goto, consider this:
- goto uses a graph-search algorithm to find an efficient path, so avoid calling goto on intermediate nodes.
- For example, if you path is ground_2 -> ground_7 -> ground_10. Call goto(ground_10) instead of goto(ground_7), goto(ground_10)
"""

# 系统提示
SYS_PROMPT = {"role": "system", "content": BASE_SYSTEM_INSTRUCTIONS}

# 示例1 - 基础导航
EXAMPLE_1 = [
    {
        "role": "user",
        "content": "task: Go to the kitchen"
    },
    {
        "role": "assistant", 
        "content": """{
"primary_goal": "Navigate to the kitchen region to complete the user's request.",
"relevant_graph": "kitchen",
"reasoning": "The user wants to go to the kitchen. I need to check if there's a path from the current location to the kitchen region.",
"plan": "goto(kitchen)"
}"""
    }
]

# 示例2 - 探索任务
EXAMPLE_2 = [
    {
        "role": "user",
        "content": "task: Find the red car"
    },
    {
        "role": "assistant",
        "content": """{
"primary_goal": "Locate the red car object in the environment.",
"relevant_graph": "red_car, ground_1, ground_2",
"reasoning": "I need to find a red car. I should explore regions to discover objects and look for the red car specifically.",
"plan": "explore_region(ground_1, 5.0), map_region(ground_2), inspect(red_car, 'What is the condition of this car?')"
}"""
    }
]

# 示例3 - 复杂任务
EXAMPLE_3 = [
    {
        "role": "user", 
        "content": "task: Check if there are any obstacles between the living room and the bedroom"
    },
    {
        "role": "assistant",
        "content": """{
"primary_goal": "Assess the path between living room and bedroom for obstacles.",
"relevant_graph": "living_room, bedroom, ground_3",
"reasoning": "I need to map the regions between living room and bedroom to identify any obstacles in the path.",
"plan": "map_region(living_room), map_region(bedroom), explore_region(ground_3, 3.0)"
}"""
    }
]

# 示例4 - 地图扩展
EXAMPLE_4 = [
    {
        "role": "user",
        "content": "task: Explore the area north of the garage"
    },
    {
        "role": "assistant", 
        "content": """{
"primary_goal": "Extend the map to include regions north of the garage.",
"relevant_graph": "garage, [50.0, 100.0]",
"reasoning": "I need to extend the map north of the garage. I'll use extend_map with coordinates north of the garage location.",
"plan": "extend_map(50.0, 100.0), explore_region(new_region, 5.0)"
}"""
    }
]

# 示例5 - 对象检查
EXAMPLE_5 = [
    {
        "role": "user",
        "content": "task: What color is the table in the dining room?"
    },
    {
        "role": "assistant",
        "content": """{
"primary_goal": "Determine the color of the table in the dining room.",
"relevant_graph": "dining_room, table",
"reasoning": "I need to navigate to the dining room and inspect the table to determine its color.",
"plan": "goto(dining_room), inspect(table, 'What color is this table?')"
}"""
    }
]


def get_base_prompt_update_graph(request: str, scene_graph: str) -> List[Dict[str, str]]:
    """获取基础prompt，用于更新图
    
    Args:
        request: 用户请求
        scene_graph: 场景图JSON字符串
        
    Returns:
        完整的prompt消息列表
    """
    prompt = (
        [SYS_PROMPT]
        + EXAMPLE_1
        + EXAMPLE_2
        + EXAMPLE_3
        + EXAMPLE_4
        + EXAMPLE_5
        + [
            {
                "role": "user",
                "content": f"{request}\nAdvice: \n- Recall the scene may be incomplete. \n- Carefully explain your reasoning in a step-by-step manner.\n- Reason over connections, coordinates, and semantic relationships between objects and regions in the scene.\n\n"
                f"Scene graph:{scene_graph}",
            }
        ]
    )

    return prompt


# 无效JSON错误提示
INVALID_JSON = (
    "Feedback: You did not return your message in a valid json format. "
    "Received following error when parsing: {}. Update your response accordingly."
) 