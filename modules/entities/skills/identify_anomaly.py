import time
import random
from typing import Dict, Any, List, TYPE_CHECKING
from modules.entity.robot.robot import Robot
from modules.entity.robot.drone import Drone
from modules.entity.robot.ground_vehicle import GroundVehicle
from modules.entity.robot.capabilities import Capability

if TYPE_CHECKING:
    from modules.map.scene_graph import SceneGraph

from .skill import Skill
from .preconditions import has_capability, battery_above, has_detection_area
from .effects import SkillEffect, StatusChangeEffect

class AnomalyRecordEffect(SkillEffect):
    """异常记录效果"""
    def apply(self, robot: Robot, **kwargs) -> Dict[str, Any]:
        anomalies = kwargs.get('detected_anomalies', [])
        if anomalies:
            robot.set_state('detected_anomalies', anomalies)
            robot.set_state('last_anomaly_detection_time', kwargs.get('timestamp', time.time()))
        return {'detected_anomalies': anomalies}

class IdentifyAnomalySkill(Skill):
    """异常识别技能"""
    required_capabilities = {Capability.SENSOR, Capability.ANALYZE}

    def _setup(self):
        """设置前置条件和效果"""
        self.preconditions.add(has_capability(Capability.SENSOR))
        self.preconditions.add(has_capability(Capability.ANALYZE))
        self.preconditions.add(battery_above(10.0))
        self.preconditions.add(has_detection_area())

        self.effects.append(AnomalyRecordEffect())
        self.effects.append(StatusChangeEffect('idle'))

    def _default_execute(self, robot: Robot, **kwargs) -> Dict[str, Any]:
        """默认异常识别逻辑"""
        detection_area = kwargs['detection_area']
        
        # 延迟导入避免循环依赖
        try:
            from modules.map.scene_graph import SceneGraph
            scene_graph = kwargs.get('scene_graph', SceneGraph())
            objects_in_area = scene_graph.get_objects_in_area(detection_area)
        except ImportError:
            # 如果SceneGraph不可用，使用模拟数据
            objects_in_area = []

        # 设置分析状态
        robot.set_state('status', 'working')

        # 模拟异常检测（实际应基于传感器数据和AI分析）
        detected_anomalies = []
        for obj in objects_in_area:
            # 随机模拟异常检测结果（实际项目中应替换为真实算法）
            if random.random() < 0.15:  # 15%概率检测到异常
                detected_anomalies.append({
                    'object_id': obj['id'],
                    'object_type': obj['type'],
                    'position': obj['position'],
                    'anomaly_type': random.choice(['structural', 'functional', 'environmental']),
                    'confidence': round(random.uniform(0.7, 0.99), 2)
                })

        result = {
            'detection_area': detection_area,
            'objects_scanned': len(objects_in_area),
            'detected_anomalies': detected_anomalies,
            'timestamp': time.time()
        }

        self.logger.info(f"机器人 {robot.label} 异常检测完成，扫描 {len(objects_in_area)} 个对象，发现 {len(detected_anomalies)} 个异常")

        return result

    def _drone_execute(self, robot: Drone, **kwargs) -> Dict[str, Any]:
        """无人机异常识别逻辑"""
        result = self._default_execute(robot, **kwargs)
        result['detection_altitude'] = robot.get_state('altitude', 0)
        result['sensor_type'] = 'thermal_camera'
        return result

    def _ground_vehicle_execute(self, robot: GroundVehicle, **kwargs) -> Dict[str, Any]:
        """地面车辆异常识别逻辑"""
        result = self._default_execute(robot, **kwargs)
        result['sensor_type'] = 'multispectral_camera'
        result['ground_clearance'] = kwargs.get('ground_clearance', 0.5)
        return result