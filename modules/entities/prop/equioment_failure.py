from .prop import Prop


class EquipmentFailure(Prop):
    """
    设备故障（EquipmentFailure），是一种逻辑或事件型道具。
    它本身没有物理形态，而是代表一个需要处理的“事件”或“异常状态”。
    """

    def __init__(self, entity_id: int, label: str, failed_equipment_id: int, severity: str = 'medium'):
        """
        初始化一个设备故障事件。

        Args:
            entity_id (int): 该故障事件的唯一ID。
            label (str): 故障的简短描述，例如 '冷却系统过热'。
            failed_equipment_id (int): 发生故障的设备的ID。
            severity (str): 故障的严重程度 (例如: 'low', 'medium', 'high', 'critical')。
        """
        initial_state = {
            'type': 'equipment_failure',
            'failed_equipment_id': failed_equipment_id,
            'severity': severity,
            'is_resolved': False  # 默认状态：未解决
        }
        super().__init__(entity_id, label, initial_state)
