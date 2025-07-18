import uuid
import time
from typing import Dict, Any
from modules.entity.robot.robot import Robot
from modules.entity.robot.drone import Drone
from modules.entity.robot.ground_vehicle import GroundVehicle
from modules.entity.robot.capabilities import Capability
from .skill import Skill
from .preconditions import has_capability, battery_above
from .effects import StatusChangeEffect
from .descriptions import SkillDescription, SkillCategory, SkillRequirement, SkillPrecondition, SkillOutput, SkillDescriptionRegistry

class TakePhotoSkill(Skill):
    """拍照技能"""
    required_capabilities = {Capability.TAKE_PHOTO}

    def __init__(self):
        super().__init__()
        self._register_description()

    def _register_description(self):
        """注册技能描述"""
        description = SkillDescription(
            name="take_photo",
            display_name="拍照",
            category=SkillCategory.SENSING,
            description="使用相机拍摄照片，记录当前位置的视觉信息",
            capabilities=["拍照能力", "图像处理"],
            requirements=[
                SkillRequirement(
                    capability="拍照能力",
                    min_battery=5.0,
                    description="机器人需要配备相机设备"
                )
            ],
            preconditions=[
                SkillPrecondition(
                    condition="机器人具备拍照能力",
                    check_type="capability",
                    description="检查机器人是否安装了相机"
                ),
                SkillPrecondition(
                    condition="电量充足",
                    check_type="battery",
                    description="电量需要≥5%才能执行拍照"
                )
            ],
            input_params={
                "target": "拍摄目标对象ID",
                "resolution": "照片分辨率",
                "format": "照片格式（jpg/png）"
            },
            outputs=[
                SkillOutput(
                    output_type="photo_data",
                    description="照片数据",
                    data_format="{'photo_id': str, 'timestamp': float, 'position': dict, 'target': str}"
                ),
                SkillOutput(
                    output_type="status",
                    description="拍照状态",
                    data_format="'success' | 'failed'"
                )
            ],
            execution_time="约1-3秒",
            examples=[
                "take_photo(target='building_001') - 拍摄指定建筑",
                "take_photo(resolution='high') - 拍摄高清照片",
                "take_photo(format='png') - 拍摄PNG格式照片"
            ],
            notes=[
                "拍照会消耗少量电量",
                "照片质量取决于相机性能",
                "支持多种照片格式"
            ]
        )
        SkillDescriptionRegistry.register("take_photo", description)

    def _setup(self):
        """设置前置条件和效果"""
        self.preconditions.add(has_capability(Capability.TAKE_PHOTO))
        self.preconditions.add(battery_above(5.0))
        
        # 添加效果
        self.effects.append(StatusChangeEffect('idle'))

    def _default_execute(self, robot: Robot, **kwargs) -> Dict[str, Any]:
        """默认拍照逻辑"""
        # 设置工作状态
        robot.set_state('status', 'working')
        
        # 生成照片ID和元数据
        photo_id = str(uuid.uuid4())
        timestamp = time.time()
        position = robot.get_state('position', {'x': 0, 'y': 0})

        # 模拟拍照延迟
        time.sleep(0.5)

        self.logger.info(f"机器人 {robot.label} 拍照完成，照片ID: {photo_id}")

        return {
            'photo_id': photo_id,
            'timestamp': timestamp,
            'position': position,
            'target': kwargs.get('target', 'unknown')
        }

    def _drone_execute(self, robot: Drone, **kwargs) -> Dict[str, Any]:
        """无人机拍照逻辑"""
        result = self._default_execute(robot, **kwargs)
        result['altitude'] = robot.get_state('altitude', 0)
        result['camera_angle'] = kwargs.get('camera_angle', 'nadir')
        return result

    def _ground_vehicle_execute(self, robot: GroundVehicle, **kwargs) -> Dict[str, Any]:
        """地面车辆拍照逻辑"""
        result = self._default_execute(robot, **kwargs)
        result['camera_height'] = kwargs.get('camera_height', 1.5)
        return result