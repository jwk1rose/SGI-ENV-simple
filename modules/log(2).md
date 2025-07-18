***
# <span style="color: blue;">Current Stage: *[2025-07-16 10:11:58:077895]:Mission starting...*</span>
***
# <span style="color: blue;">Current Stage: *[2025-07-16 10:11:58:078285]:Starting Main Workflow...*</span>
***
# <span style="color: blue;">Current Stage: *[2025-07-16 10:11:58:078407]:Executing Decomposition Stage...*</span>
#### <span style="color: black;">info: </span>
[2025-07-16 10:11:58:078515]:Decomp Step 1: Initial planning
## <span style="color: purple;">Current Action: *[2025-07-16 10:11:58:078680]:Action: TaskPlan*</span>
#### <span style="color: black;">debug: </span>
[2025-07-16 10:11:58:079000]:Prompt:
 ## Master Context for Multi-Robot Task Planning ##
This Context serves as the single source of truth for all AI agents in the system. All agents MUST strictly adhere to the definitions and rules outlined here.

### 1. Environment Model
This section defines the **types** (or blueprints) of objects available in Cybertown and their default properties. The world is populated by specific instances of these types, each with a unique ID.

#### Building Types (Static Structures)
These are large, immovable structures that define the main areas of the map.

- `hospital`
  - **category**: building

- `power_station`
  - **category**: building

- `shopping_mall`
  - **category**: building

- `park`
  - **category**: building

- `parking_lot`
  - **category**: building

- `residential_building`
  - **category**: building

#### Prop Types (Interactive Objects)
These are smaller, often movable or interactable objects within the environment.

- `item_cargo`
  - **category**: prop
  - **weight_kg**: 10          

- `vehicle_car`
  - **category**: prop
  - **license_plate**: "00001"  

- `vehicle_truck`
  - **category**: prop
  - **license_plate**: "00002"

- `anomaly_equipment_failure`
  - **category**: prop
  - **status**: string # Possible values: undiscovered, discovered, resolving, resolved
  - **severity**: string # Possible values: low, medium, high, critical

- `anomaly_security_breach`
  - **category**: prop
  - **status**: string # Possible values: undiscovered, discovered, resolving, resolved
  - **severity**: string # Possible values: low, medium, high, critical

### 2. Robot Skill Library
This is the complete and definitive set of skills available. All plans MUST be grounded in this library.
## Drone

**Basic Skills:**
- **takeoff:** Ascending vertically from the ground to a safe, standard operational altitude.
  - *Precondition:* The drone is on a stable, flat surface with clear vertical space. System status is nominal.
  - *Effect:* The drone is airborne and hovering, ready to receive further commands.
- **land:** Descends vertically from its current altitude to land on a designated ground surface or rooftop platform.
  - *Precondition:* The drone is in a stable hover state, and the designated landing zone is flat.
  - *Effect:* The drone is safely landed and enters a standby mode.
- **navigate_to<location>:** Flies from the current position to a specific 3D coordinate.
  - *Precondition:* A reasonably clear flight path exists.
  - *Effect:* The drone's position is updated to the specified <location>.
- **take_photo<area>:** Captures a wide-angle aerial image of a specified <area> to provide a general overview and situational awareness. Ideal for mapping, searching large zones, or assessing a scene from above.
  - *Precondition:* The drone is at a safe operational altitude and the camera is functional.
  - *Effect:* A high-altitude, wide-field-of-view digital image is created and stored, tagged with metadata (e.g., GPS coordinates, feasible path).
- **load<object>:** Uses an onboard gripper or winch to pick up and secure a specified <object>.
  - *Precondition:* The drone is hovering accurately above the <object>, its weight is within the drone's 'max_payload_kg' (3kg) limit, and its size is compatible with the loading mechanism.
  - *Effect:* The specified <object> is securely attached to the drone.
- **unload<object>:** Releases a currently attached <object> at the drone's current position.
  - *Precondition:* The drone is currently carrying an <object> and is positioned over a safe and valid drop-off zone.
  - *Effect:* The attached <object> is released, and the drone's loading mechanism is now free.

## Ground Vehicle

**Basic Skills:**
- **move_to<location>:** Drives autonomously along Cybertown's road network to a specified ground-level <location>.
  - *Precondition:* A navigable ground path exists between the current position and the target <location>.
  - *Effect:* The vehicle's position is updated to the target <location>.
- **take_photo<target>:** Captures a high-resolution, ground-level image of a specific <target> for close-range inspection, identification, or detailed analysis.
  - *Precondition:* The vehicle has an established, unobstructed line-of-sight to the <target> within effective camera range. The vehicle must be stationary to ensure image clarity.
  - *Effect:* A high-resolution, detailed digital image file is created and stored.
- **load<object>:** Uses a robotic arm or conveyor system to move an <object> into the vehicle's cargo bay.
  - *Precondition:* The vehicle is positioned adjacent to the <object>, its weight is within the vehicle's 'max_payload_kg' (150kg) limit, and the cargo bay has sufficient space.
  - *Effect:* The specified <object> is securely stored inside the vehicle's cargo bay.
- **unload<object>:** Removes a specified <object> from its cargo bay and places it on the ground adjacent to the vehicle.
  - *Precondition:* The vehicle is carrying the specified <object>, and there is a clear, stable surface for unloading.
  - *Effect:* The specified <object> is placed on the ground, and the corresponding space in the cargo bay is now free.


### 3. Core Ontological Definitions
- **Atomic Task**: A self-contained, logically complete, goal-directed objective. It is the direct result of decomposing a high-level instruction into meaningful steps. Each atomic task MUST have a unique task_id (e.g., "T1", "T2").
  - **Guiding Principle**: An Atomic Task must correspond to a "complete thought" or a "finished action" in the real world (e.g., "Transport cargo_01 to hospital", "Search for vehicle_car_0001" are complete, meaningful goals. "Unload cargo_01" is a step within a larger goal, not a complete goal.)
- **Task Location Rules**: A task without an explicit location is considered invalid.
  - **Rule 1 (Movement Tasks)**: For tasks like "Carry object A to location B", the primary location is the destination. (e.g., For Task: "Carry cargo to hospital", the location is hospital).
  - **Rule 2 (Area-based Tasks)**: For tasks like "Search area A for target B", the primary location is the specified area of operation. If no area is given, the location may be the largest reasonable search scope. For example, the location for "Search something in the park" is the park, while for "Search something", it defaults to the "cybertown".
  - **Rule 3 (Target-oriented Tasks)**: For tasks that observe or act on a specific, static target, the primary location is the target of the action. (e.g., For Task: "Photograph the power_station", the location is power_station).
- **Multi-Robot Configuration**: A single, unified object that describes how one or more robots execute a task. It defines the composition of the robot team and the strategy they use to work together.
  - **Mode**: Describes how multiple robots work together on a single atomic task.
    - **None**: The task is performed by a single robot.
    - **Homogeneous**: The task requires multiple robots of the SAME type.
    - **Heterogeneous**: The task requires multiple robots of DIFFERENT types.
  - **Execution Strategy**: Describes how the robots in a multi-robot team work together.
    - **null**: The mode is None.
    - **concurrent**: All robots work together in a tightly coupled manner on the same, indivisible action at the same time. (e.g., Lifting a single heavy object that exceeds one robot's capacity).
    - **partitioned**: The task's overall workload is distributed among the robots, allowing each to operate on a distinct portion of the total scope. (e.g., Searching a large area where each robot covers a different sub-region).
- **Parameter Types**:
  - **<location>**: Refers to a specific 3D coordinate (e.g., [x, y, z]) or a predefined named location (e.g., "power_station", "hospital").
  - **<area>**: Refers to a defined polygon or bounding box representing a region to be searched or monitored (e.g., "park").
  - **<target>**: Refers to a specific object instance with a unique ID (e.g., "item_cargo_01").
- **Task Nature Principle (for internal reasoning)**: To construct a valid plan, you must internally differentiate between two natures of tasks:
  - **Information-Gathering Tasks (IGTs)**: These are tasks whose primary purpose is to collect information about the environment's state. Their output is data (e.g., locations of objects, status of a target, a map of an area).
  - **Execution Tasks (ETs)**: These are tasks that change the state of the environment based on known, concrete parameters. Their purpose is to act, not to learn. Skills like `load`, `unload`, `move_to<specific_target>` are examples.

### 4. Universal Output Rules
All AI agent outputs that produce JSON MUST follow these rules:
1. The response must be composed of two parts: a `### Reasoning:` section with natural language thoughts, followed immediately by a `### Result:` section.
2. The `### Result:` section must contain ONLY a single, valid JSON code block and nothing else.
3. There must be no text or commentary before `### Reasoning:` or after the final closing brace `}` of the JSON.

## Master Context ends here ##

## Skill Usage Grammar and Constraints
To ensure the plan can be parsed correctly, every skill you list in the `required_skills` array MUST conform to the patterns like:

1.  **Verb-Only:** `verb`
2.  **Verb-Parameter:** `verb<parameter>`
3.  **Verb-Parameter-For-Parameter:** `verb<parameter1>_for<parameter2>`
4. ...

You MUST replace generic placeholders like `<location>` or `<target>` with specific, concrete entity IDs from the `Environment Model`.

### Current Available Robots
The number of robots of each type available for this plan. You MUST NOT assign more robots than are available.
{'drone': 3, 'ground_vehicle': 3}


### High-Level Instruction
This is the user's origin goal.
"Take a close-range photo of the cars with license plates '00001' and '00002'."

## Persona and Goal
You are "Phased Task Planner", a world-class expert in multi-robot task planning. Your operational doctrine is: **"Plan the entire sequence of foreseeable, high-confidence tasks."**
Your primary goal is to decompose a high-level instruction into a **multi-step phase of atomic tasks**, planning as far as possible until you reach a point of uncertainty.

A task is considered **high-confidence (fine-grained)** if and only if you can determine its required skills, robot types, and robot counts with certainty based on the available information (`Environment Model`, `Mission History`). A task is **low-confidence (coarse-grained)** if any of these elements cannot be precisely determined without new information.

## Step-by-Step Instructions for You

### **Phase 1: Determine Planning Mode**
First, determine your mode by checking for the `### Real-time Feedback Context` section.
- If feedback exists, proceed to **Path A: Re-planning from Feedback**.
- If no feedback exists, this is a new mission. Proceed to **Path B: Initial Phased Planning**.

---
### Path A: Re-planning from Feedback (Follow if feedback exists)
1.  **CRITICAL - Review Full Mission Context**: Before making any decisions, you MUST synthesize all available information in the following order:
    -   **A. The Unchanging Goal**: First, re-read the `High-Level Instruction`. This is your ultimate objective that remains constant.
    -   **B. The Progress So Far**: Second, review the `### Mission History`. This tells you what has already been successfully accomplished.
    -   **C. The Immediate Event**: Third, analyze the `### Real-time Feedback Context` (`triggering_event`, `world_state_update`, `failed_tasks`). This tells you what just happened.
2.  **Define the New Planning Horizon**: Based on your complete understanding from Step 1, determine the most logical *sequence* of high-confidence tasks to advance the mission. 
    -   Your new goal should build upon the `Mission History` and respond to the `Immediate Event`, all while moving closer to the `High-Level Instruction`.
    -   This sequence constitutes the new planning phase. Your goal is to generate all atomic tasks until you reach a point of uncertainty (e.g., needing to know the result of a search task before planning the subsequent pickup task).
3.  **Proceed to Phase 2: Plan Generation.**

---
### Path B: Initial Phased Planning (Follow for new instructions)
1.  **Analyze High-Level Instruction**: Understand the user's ultimate goal.
2.  **CRITICAL - The Horizon Decision**: Assess the available information (`Environment Model`) against the instruction's requirements. Ask yourself these key questions:
    - Do I have the **exact and confirmed locations** for all necessary targets or points of interest?
    - Do I know the **exact quantity** of items to be interacted with (e.g., number of survivors, number or weight of packages)?
    - Is the path or area of operation fully mapped and known to be safe?
3.  **Define the Initial Planning Horizon**:
    - **If the answer to any question in Step 2 is NO**, then your planning horizon is limited to **Information Gathering**. Your goal is to formulate a phase of tasks to resolve these uncertainties (e.g., "Scout the area to locate all targets"). You MUST stop planning right after the information is gathered, as any subsequent steps (like `transport`) depend on this unknown information.
    - **If the answers to all questions in Step 2 are YES**, then your planning horizon is **Complete Execution**. Your goal is to create a complete, multi-step plan that fulfills the entire user instruction, as all necessary parameters for every step are known.
4.  **Proceed to Phase 2: Plan Generation.**

---
### **Phase 2: Plan Generation (The output of Path A or B flows here)**
*This is the decomposition and formatting phase, based on the planning horizon defined above.*
1.  **Decompose the Horizon**: Break down the goal for the current planning horizon into a sequence of new atomic tasks. Use new task IDs.
2.  **Define Atomic Tasks**: Specify the `name`, `description`, and `location` for each task. Ensure they are high-confidence (fine-grained).
3.  **Map to Skills**: Identify the necessary one or more skills from the provided `Robot Skill Library`.
4.  **Determine Dependencies**: Establish the `dependencies` between the new tasks you've just created within this phase.
5.  **Define Multi-Robot Config**: Specify the collaboration strategy for tasks requiring multiple robots.
6.  **Justify Strategic Decisions**: In the `Reasoning` section, explain your logic. 
    - **Crucially, you MUST explicitly state the extent of your plan and justify why the plan stops where it does.** Reference the specific piece of information that is currently unknown and prevents further high-confidence planning.
    - If re-planning, explain how the feedback shaped the new plan.
    - If doing initial planning, explicitly state why you chose an Information-Gathering or Complete Execution horizon.


## Output Format Specification
Your entire response MUST consist of the ### Reasoning: section immediately followed by the ### Result: section containing a single, valid JSON code block. There must be NO text, notes, or apologies before ### Reasoning: or after the final closing brace } of the JSON.

### Reasoning:
**Provide a step-by-step thinking process here, following the instructions above. Explain your decomposition logic. Crucially, justify the extent and endpoint of your planning horizon.**

### Result:
```json
{
  "atomic_tasks": [
    {
      "task_id": "T1",
      "name": "Name of the first atomic task",
      "description": "A clear, concise description of what this task aims to achieve.",
      "location": "<The specific execution location, e.g., 'parking_lot'>",
      "required_skills": [
        {
          "skill_name": "skill_name_from_library", 
          "assigned_robot_type": ["robot_type_1", "robot_type_2"],
          "assigned_robot_count": "<integer>"
        },
        {
          "skill_name": "another_skill_name", 
          "assigned_robot_type": ["robot_type_1"],
          "assigned_robot_count": "<integer>"
        }
      ],
      "dependencies": [],
      "multi_robot_config": {
        "mode": "<'None' | 'Homogeneous' | 'Heterogeneous'>",
        "total_robot_count": "<integer>",
        "execution_strategy": "<'partitioned' | 'concurrent' | null>",
        "description": "A brief explanation of how robots collaborate, if applicable."
      }
    },
    ... (more atomic tasks)
  ]
}
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:18:639575]:Response:
 ### Reasoning:
**1. Initial Phased Planning Analysis**

Following the "Phased Task Planner" protocol, I am performing an initial analysis as there is no `### Real-time Feedback Context`.

*   **Instruction Analysis**: The user wants "close-range" photos of two specific vehicles identified by license plates '00001' and '00002'. The `ground_vehicle`'s `take_photo<target>` skill is designed for this specific purpose.
*   **Horizon Decision**: I have checked the `Environment Model` and other available information. The critical missing piece of information is the **location** of the target vehicles (`vehicle_car` '00001' and `vehicle_truck` '00002'). Without their confirmed coordinates, I cannot plan the final execution task of moving a ground vehicle to them and taking a photo.
*   **Planning Horizon Definition**: Because the target locations are unknown, my planning horizon is limited to **Information Gathering**. The goal of this phase is to resolve this uncertainty. I will generate a plan to systematically search for the vehicles. The plan will stop after this search phase, as any subsequent actions are dependent on the results of the search.

**2. Plan Generation**

*   **Task Decomposition**: I have decomposed the high-level goal "find the vehicles" into six discrete, parallelizable atomic tasks. Each task focuses on surveying a major named location within Cybertown where vehicles are likely to be present. This approach is more concrete and actionable than a single, vague "search Cybertown" task. The locations are derived from the `Building Types` in the environment model.
*   **Robot and Skill Assignment**: Drones are the ideal choice for this information-gathering phase. Their aerial vantage point and `take_photo<area>` skill are superior for efficiently surveying large areas compared to ground-based alternatives. Each search task requires one drone to first `navigate_to` the specified location and then `take_photo` of the area.
*   **Multi-Robot Strategy**: The plan creates six independent tasks. Since there are three drones available, a scheduler can distribute these tasks among them, allowing for up to three areas to be searched in parallel. Each individual task is self-contained and performed by a single robot, so its multi-robot `mode` is 'None'. The overall mission strategy relies on parallel execution of these single-robot tasks.
*   **Plan Endpoint Justification**: This plan deliberately concludes after the survey tasks are defined. Planning the subsequent "take close-range photo" action is impossible without the output from this search phase (i.e., the confirmed locations of the vehicles). Attempting to plan further would be low-confidence speculation.

### Result:
```json
{
  "atomic_tasks": [
    {
      "task_id": "T1",
      "name": "Survey parking_lot for target vehicles",
      "description": "Survey the parking_lot from the air to gather imagery that can be analyzed to locate the target vehicles (license plates '00001', '00002').",
      "location": "parking_lot",
      "required_skills": [
        {
          "skill_name": "navigate_to<parking_lot>",
          "assigned_robot_type": [
            "drone"
          ],
          "assigned_robot_count": 1
        },
        {
          "skill_name": "take_photo<parking_lot>",
          "assigned_robot_type": [
            "drone"
          ],
          "assigned_robot_count": 1
        }
      ],
      "dependencies": [],
      "multi_robot_config": {
        "mode": "None",
        "total_robot_count": 1,
        "execution_strategy": null,
        "description": "A single drone will perform this survey task."
      }
    },
    {
      "task_id": "T2",
      "name": "Survey shopping_mall for target vehicles",
      "description": "Survey the shopping_mall from the air to gather imagery that can be analyzed to locate the target vehicles (license plates '00001', '00002').",
      "location": "shopping_mall",
      "required_skills": [
        {
          "skill_name": "navigate_to<shopping_mall>",
          "assigned_robot_type": [
            "drone"
          ],
          "assigned_robot_count": 1
        },
        {
          "skill_name": "take_photo<shopping_mall>",
          "assigned_robot_type": [
            "drone"
          ],
          "assigned_robot_count": 1
        }
      ],
      "dependencies": [],
      "multi_robot_config": {
        "mode": "None",
        "total_robot_count": 1,
        "execution_strategy": null,
        "description": "A single drone will perform this survey task."
      }
    },
    {
      "task_id": "T3",
      "name": "Survey hospital for target vehicles",
      "description": "Survey the hospital and its surrounding area from the air to gather imagery that can be analyzed to locate the target vehicles (license plates '00001', '00002').",
      "location": "hospital",
      "required_skills": [
        {
          "skill_name": "navigate_to<hospital>",
          "assigned_robot_type": [
            "drone"
          ],
          "assigned_robot_count": 1
        },
        {
          "skill_name": "take_photo<hospital>",
          "assigned_robot_type": [
            "drone"
          ],
          "assigned_robot_count": 1
        }
      ],
      "dependencies": [],
      "multi_robot_config": {
        "mode": "None",
        "total_robot_count": 1,
        "execution_strategy": null,
        "description": "A single drone will perform this survey task."
      }
    },
    {
      "task_id": "T4",
      "name": "Survey power_station for target vehicles",
      "description": "Survey the power_station and its surrounding area from the air to gather imagery that can be analyzed to locate the target vehicles (license plates '00001', '00002').",
      "location": "power_station",
      "required_skills": [
        {
          "skill_name": "navigate_to<power_station>",
          "assigned_robot_type": [
            "drone"
          ],
          "assigned_robot_count": 1
        },
        {
          "skill_name": "take_photo<power_station>",
          "assigned_robot_type": [
            "drone"
          ],
          "assigned_robot_count": 1
        }
      ],
      "dependencies": [],
      "multi_robot_config": {
        "mode": "None",
        "total_robot_count": 1,
        "execution_strategy": null,
        "description": "A single drone will perform this survey task."
      }
    },
    {
      "task_id": "T5",
      "name": "Survey residential_building for target vehicles",
      "description": "Survey the residential_building and its surrounding streets from the air to gather imagery to locate the target vehicles (license plates '00001', '00002').",
      "location": "residential_building",
      "required_skills": [
        {
          "skill_name": "navigate_to<residential_building>",
          "assigned_robot_type": [
            "drone"
          ],
          "assigned_robot_count": 1
        },
        {
          "skill_name": "take_photo<residential_building>",
          "assigned_robot_type": [
            "drone"
          ],
          "assigned_robot_count": 1
        }
      ],
      "dependencies": [],
      "multi_robot_config": {
        "mode": "None",
        "total_robot_count": 1,
        "execution_strategy": null,
        "description": "A single drone will perform this survey task."
      }
    },
    {
      "task_id": "T6",
      "name": "Survey park for target vehicles",
      "description": "Survey the park and its access roads from the air to gather imagery that can be analyzed to locate the target vehicles (license plates '00001', '00002').",
      "location": "park",
      "required_skills": [
        {
          "skill_name": "navigate_to<park>",
          "assigned_robot_type": [
            "drone"
          ],
          "assigned_robot_count": 1
        },
        {
          "skill_name": "take_photo<park>",
          "assigned_robot_type": [
            "drone"
          ],
          "assigned_robot_count": 1
        }
      ],
      "dependencies": [],
      "multi_robot_config": {
        "mode": "None",
        "total_robot_count": 1,
        "execution_strategy": null,
        "description": "A single drone will perform this survey task."
      }
    }
  ]
}
```
#### <span style="color: gold;">Success: [2025-07-16 10:13:19:185013]:Output Task Decomposition Success</span>
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:19:185394]:Decomp Step 4: Generating final output
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:19:185546]:Workflow completed after 1 iteration(s)
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:19:185810]:Final flow documentation written to: /home/zhugb/Software/miniconda3/envs/SGI/SGI-TP/UserInterface/results/2025-07-16_10-11-57/flow.md
***
# <span style="color: blue;">Current Stage: *[2025-07-16 10:13:19:185914]:Executing Allocation Stage...*</span>
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:19:186037]:Alloc Step 1: Translating plan for CTAS algorithm
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:19:187165]:CTAS Translation Results:
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:19:187758]:Task math descriptions: {
  "T1": {
    "skills": {
      "navigate_to<location>": {
        "capId": 2,
        "capReq": 1
      },
      "take_photo<area>": {
        "capId": 3,
        "capReq": 1
      }
    },
    "time_cost": 1
  },
  "T2": {
    "skills": {
      "navigate_to<location>": {
        "capId": 2,
        "capReq": 1
      },
      "take_photo<area>": {
        "capId": 3,
        "capReq": 1
      }
    },
    "time_cost": 1
  },
  "T3": {
    "skills": {
      "navigate_to<location>": {
        "capId": 2,
        "capReq": 1
      },
      "take_photo<area>": {
        "capId": 3,
        "capReq": 1
      }
    },
    "time_cost": 1
  },
  "T4": {
    "skills": {
      "navigate_to<location>": {
        "capId": 2,
        "capReq": 1
      },
      "take_photo<area>": {
        "capId": 3,
        "capReq": 1
      }
    },
    "time_cost": 1
  },
  "T5": {
    "skills": {
      "navigate_to<location>": {
        "capId": 2,
        "capReq": 1
      },
      "take_photo<area>": {
        "capId": 3,
        "capReq": 1
      }
    },
    "time_cost": 1
  },
  "T6": {
    "skills": {
      "navigate_to<location>": {
        "capId": 2,
        "capReq": 1
      },
      "take_photo<area>": {
        "capId": 3,
        "capReq": 1
      }
    },
    "time_cost": 1
  }
}
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:19:187872]:Task dependencies: []
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:19:187990]:Task locations: {
  "T1": "parking_lot",
  "T2": "shopping_mall",
  "T3": "hospital",
  "T4": "power_station",
  "T5": "residential_building",
  "T6": "park"
}
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:19:188178]:Robot capabilities: {
  "drone": {
    "robot_num": 3,
    "capability": [
      1,
      1,
      1,
      1,
      1,
      1,
      0,
      0,
      0,
      0
    ]
  },
  "ground_vehicle": {
    "robot_num": 3,
    "capability": [
      0,
      0,
      0,
      0,
      0,
      0,
      1,
      1,
      1,
      1
    ]
  }
}
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:19:188323]:Skill mapping: {
  "0": "takeoff@drone",
  "1": "land@drone",
  "2": "navigate_to<location>@drone",
  "3": "take_photo<area>@drone",
  "4": "load<object>@drone",
  "5": "unload<object>@drone",
  "6": "move_to<location>@ground_vehicle",
  "7": "take_photo<target>@ground_vehicle",
  "8": "load<object>@ground_vehicle",
  "9": "unload<object>@ground_vehicle"
}
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:19:188475]:Plan successfully translated for CTAS algorithm
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:19:188559]:Alloc Step 2: Adjusting parameters...
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:19:188713]:Alloc Step 3: Calling CTAS allocator...
#### <span style="color: gold;">Success: [2025-07-16 10:13:19:532560]:Allocation successful. Result: /home/zhugb/Software/miniconda3/envs/SGI/SGI-TP/UserInterface/results/2025-07-16_10-11-57/test_log.yaml</span>
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:19:532830]:Alloc Step 4: Post-processing results...
#### <span style="color: black;">info: </span>
[2025-07-16 10:13:19:567209]:Allocation results: {
  "robot_view": {
    "drone_1": {
      "T2": [
        "navigate_to<shopping_mall>",
        "take_photo<shopping_mall>"
      ],
      "T4": [
        "navigate_to<power_station>",
        "take_photo<power_station>"
      ]
    },
    "drone_2": {
      "T6": [
        "navigate_to<park>",
        "take_photo<park>"
      ],
      "T3": [
        "navigate_to<hospital>",
        "take_photo<hospital>"
      ]
    },
    "drone_3": {
      "T1": [
        "navigate_to<parking_lot>",
        "take_photo<parking_lot>"
      ],
      "T5": [
        "navigate_to<residential_building>",
        "take_photo<residential_building>"
      ]
    }
  },
  "task_view": {
    "T2": [
      "drone_1"
    ],
    "T4": [
      "drone_1"
    ],
    "T6": [
      "drone_2"
    ],
    "T3": [
      "drone_2"
    ],
    "T1": [
      "drone_3"
    ],
    "T5": [
      "drone_3"
    ]
  }
}
***
# <span style="color: blue;">Current Stage: *[2025-07-16 10:13:19:567540]:Main Workflow Completed Successfully!*</span>
