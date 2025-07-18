# file: entity_library.py

"""
定义了实体模板库 (EntityTemplateLibrary)。

这个模块是整个场景生成框架的"数据字典"。它不仅存储了所有标准实体的
"蓝图"，还提供了一个动态解析的方法来获取所有支持的实体类型。
"""
import copy
from modules.utils.global_config import GlobalConfig, EntityType, RobotStatus, ObjectStatus
from modules.entity.skill.skill_factory import SkillFactory

class EntityTemplateLibrary:
    """
    一个用于维护和提供所有实体模板的类。
    这是所有构建器获取标准"零件"的唯一来源。
    它还能自动解析自身，提供所有可用模板的目录。
    """
    
    def __init__(self):
        """初始化实体模板库"""
        self._templates = self._build_templates()
    
    def _build_templates(self):
        """构建实体模板"""
        return {
            # ======================================================================
            # 类别 1: 建筑 (Building) - 静态的环境组成部分
            # ======================================================================
            "building": {
                "hospital":           { "category": "building", "type": "hospital", "size": (100, 150) },
                "power_station":      { "category": "building", "type": "power_station", "size": (150, 200) },
                "shopping_mall":      { "category": "building", "type": "shopping_mall", "size": (200, 200) },
                "park":               { "category": "building", "type": "park", "size": (250, 250) },
                "parking_lot":        { "category": "building", "type": "parking_lot", "size": (100, 100) },
                "residential_building": { "category": "building", "type": "residential_building", "size": (80, 60) },
                "robot_base":           {"category": "building", "type": "robot_base", "size": (120, 120)}

            },

            # ======================================================================
            # 类别 2: 机器人 (Robot) - 场景中的自主行动者
            # ======================================================================
            "robot": {
                "drone": {
                    "category": "robot", "type": "drone",
                    "skills": self._get_skills_for_robot_type("drone"),
                    "max_speed_ms": 20, "max_operational_time_min": 35, "max_payload_kg": 3, "shape_size": (2, 2),
                    "status": RobotStatus.LANDED.value
                },
                "ground_vehicle": {
                    "category": "robot", "type": "ground_vehicle",
                    "skills": self._get_skills_for_robot_type("ground_vehicle"),
                    "max_speed_ms": 5, "max_operational_time_min": 540, "max_payload_kg": 150, "shape_size": (3, 5),
                    "status": RobotStatus.PARKED.value
                }
            },

            # ======================================================================
            # 类别 3: 道具/交互物 (Prop) - 场景中可被交互的对象
            # ======================================================================
            "prop": {
                "cargo": {
                    "category": "prop", "type": "cargo",
                    "weight_kg": 10, # 默认重量，可被具体实例覆盖
                    "shape_size": (1, 1),
                    "status": ObjectStatus.WAITING_PICKUP.value
                },
                "car": {
                    "category": "prop", "type": "car",
                    "license_plate": "00001",
                    "shape_size": (2, 4),
                    "status": ObjectStatus.PARKED.value
                },
                "truck": {
                    "category": "prop", "type": "truck",
                    "license_plate": "00002",
                    "shape_size": (3, 8),
                    "status": ObjectStatus.PARKED.value
                },
                "equipment_failure": {
                    "category": "prop", "type": "equipment_failure",
                    "status": ObjectStatus.UNDISCOVERED.value,
                },
                "security_breach": {
                    "category": "prop", "type": "security_breach",
                    "status": ObjectStatus.UNDISCOVERED.value,
                }
            }
        }
    
    def _get_skills_for_robot_type(self, robot_type: str) -> list:
        """根据机器人类型获取可用技能"""
        # 获取所有可用技能
        all_skills = SkillFactory.list_skills()
        
        # 根据机器人类型过滤技能
        if robot_type == "drone":
            # 无人机特有的技能
            drone_skills = ["take_off", "land", "navigate", "take_photo", "search_for_target", "identify_anomaly", "load_object", "unload_object"]
            return [skill for skill in all_skills if skill in drone_skills]
        elif robot_type == "ground_vehicle":
            # 地面车辆特有的技能（不能飞行）
            ground_skills = ["navigate", "take_photo", "search_for_target", "identify_anomaly", "load_object", "unload_object"]
            return [skill for skill in all_skills if skill in ground_skills]
        else:
            # 默认返回所有技能
            return all_skills

    @classmethod
    def list_all_templates(cls) -> dict:
        """
        这个方法使得库能够"自我描述"，外部代码可以调用它来动态地
        发现所有支持的实体类型，而无需硬编码。

        :return: 一个字典，键是主类别，值是该类别下所有模板键名的列表。
                 e.g., {"building": ["hospital", ...], "robot": ["drone", ...]}
        """
        instance = cls()
        return {
            category: list(templates.keys())
            for category, templates in instance._templates.items()
        }

    def get_template(self, category: str, key: str) -> dict:
        """
        获取一个指定实体模板的深拷贝，以防意外修改。

        :param category: 主类别, e.g., 'building', 'robot', 'prop'.
        :param key: 该类别下的具体模板名, e.g., 'hospital', 'drone', 'cargo'.
        :return: 一个模板属性字典。
        :raises KeyError: 如果模板不存在。
        """
        # 直接检查模板是否存在，不再需要手动维护的列表
        if category not in self._templates or key not in self._templates[category]:
            raise KeyError(f"Template for '{category}:{key}' is not supported or does not exist.")

        # 使用 copy.deepcopy() 确保返回的是完全独立的副本
        return copy.deepcopy(self._templates[category][key])

    def refresh_templates(self):
        """刷新模板，重新从技能工厂获取技能列表"""
        self._templates = self._build_templates()

    @classmethod
    def validate_template(cls, template: dict) -> bool:
        """
        验证模板是否符合全局配置要求
        
        :param template: 要验证的模板字典
        :return: 是否有效
        """
        return GlobalConfig.validate_entity_template(template)

    @classmethod
    def get_valid_entity_types(cls) -> list:
        """
        获取所有有效的实体类型
        
        :return: 实体类型列表
        """
        return GlobalConfig.get_valid_entity_types()

    @classmethod
    def get_valid_robot_statuses(cls) -> list:
        """
        获取所有有效的机器人状态
        
        :return: 机器人状态列表
        """
        return GlobalConfig.get_valid_robot_statuses()

    @classmethod
    def get_valid_prop_statuses(cls) -> list:
        """
        获取所有有效的物品状态
        
        :return: 物品状态列表
        """
        return GlobalConfig.get_valid_object_statuses()


