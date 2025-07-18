import math
import time
from typing import Dict, Any
from modules.entity.robot.robot import Robot
from modules.entity.robot.drone import Drone
from modules.entity.robot.ground_vehicle import GroundVehicle
from modules.entity.robot.capabilities import Capability
from .skill import Skill
from .preconditions import has_capability, battery_above, has_target_position
from .effects import BatteryConsumptionEffect, PositionChangeEffect, StatusChangeEffect
from .descriptions import SkillDescription, SkillCategory, SkillRequirement, SkillPrecondition, SkillOutput, SkillDescriptionRegistry
from modules.utils.spatial_utils import calculate_distance

class NavigateSkill(Skill):
    """导航技能 - 统一的移动技能实现"""
    
    required_capabilities = {Capability.NAVIGATE}

    def __init__(self):
        super().__init__()
        self._register_description()

    def _register_description(self):
        """注册技能描述"""
        description = SkillDescription(
            name="navigate",
            display_name="导航移动",
            category=SkillCategory.MOVEMENT,
            description="让机器人移动到指定位置，支持路径规划和避障",
            capabilities=["导航能力", "路径规划", "避障"],
            requirements=[
                SkillRequirement(
                    capability="导航能力",
                    min_battery=10.0,
                    description="机器人需要具备导航和移动能力"
                )
            ],
            preconditions=[
                SkillPrecondition(
                    condition="机器人具备导航能力",
                    check_type="capability",
                    description="检查机器人是否安装了导航模块"
                ),
                SkillPrecondition(
                    condition="电量充足",
                    check_type="battery",
                    description="电量需要≥10%才能执行导航"
                ),
                SkillPrecondition(
                    condition="目标位置有效",
                    check_type="position",
                    description="目标位置必须在有效范围内"
                )
            ],
            input_params={
                "target_position": "目标位置坐标 [x, y]",
                "altitude": "飞行高度（无人机专用）",
                "route_type": "路径类型（地面车辆专用）",
                "terrain_type": "地形类型（地面车辆专用）"
            },
            outputs=[
                SkillOutput(
                    output_type="position",
                    description="机器人新位置",
                    data_format="{'x': float, 'y': float}"
                ),
                SkillOutput(
                    output_type="status",
                    description="执行状态",
                    data_format="'success' | 'failed'"
                ),
                SkillOutput(
                    output_type="distance",
                    description="移动距离",
                    data_format="float (meters)"
                )
            ],
            execution_time="基于距离计算，约1-30秒",
            examples=[
                "navigate(target_position=[10, 20]) - 移动到坐标(10, 20)",
                "navigate(target_position=[5, 15], altitude=50) - 无人机飞到高度50米",
                "navigate(target_position=[8, 12], route_type='optimal') - 使用最优路径"
            ],
            notes=[
                "移动过程中会消耗电量",
                "支持实时避障",
                "可根据机器人类型选择不同移动模式"
            ]
        )
        SkillDescriptionRegistry.register("navigate", description)

    def _setup(self):
        """设置前置条件和效果"""
        # 添加前置条件
        self.preconditions.add(has_capability(Capability.NAVIGATE))
        self.preconditions.add(battery_above(10.0))
        self.preconditions.add(has_target_position())

        # 添加效果
        self.effects.append(BatteryConsumptionEffect(rate=0.02))  # 默认消耗率
        self.effects.append(PositionChangeEffect())
        self.effects.append(StatusChangeEffect('idle'))  # 完成后恢复空闲状态

    def _default_execute(self, robot: Robot, **kwargs) -> Dict[str, Any]:
        """默认导航逻辑"""
        current_pos = robot.get_state('position', {'x': 0, 'y': 0})
        target_pos = kwargs['target_position']
        distance = calculate_distance(current_pos, target_pos)

        # 设置移动状态
        robot.set_state('status', 'moving')

        # 模拟移动过程
        self.logger.info(f"机器人 {robot.label} 开始移动，距离: {distance:.2f}m")
        time.sleep(0.1)  # 简化模拟

        # 更新机器人位置到目标位置
        robot.set_state('position', target_pos)

        return {
            'distance': distance,
            'start_position': current_pos,
            'new_position': target_pos,
            'target_position': target_pos,
            'robot_type': robot.get_state('type', 'unknown')
        }

    def _drone_execute(self, robot: Drone, **kwargs) -> Dict[str, Any]:
        """无人机导航逻辑"""
        result = self._default_execute(robot, **kwargs)
        
        # 添加无人机特有逻辑
        altitude = kwargs.get('altitude', 50)
        result['flight_altitude'] = altitude
        result['flight_mode'] = 'autonomous'
        
        self.logger.info(f"无人机 {robot.label} 在高度 {altitude}m 飞行")
        return result

    def _ground_vehicle_execute(self, robot: GroundVehicle, **kwargs) -> Dict[str, Any]:
        """地面车辆导航逻辑"""
        result = self._default_execute(robot, **kwargs)
        
        # 添加地面车辆特有逻辑
        route_type = kwargs.get('route_type', 'default')
        result['route_type'] = route_type
        result['terrain_type'] = kwargs.get('terrain_type', 'paved')
        
        self.logger.info(f"地面车辆 {robot.label} 使用 {route_type} 路线")
        return result
