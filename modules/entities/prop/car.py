from .prop import Prop


class Car(Prop):
    """
    汽车（Car），是一种物理道具。
    它具有车牌号 等专属属性。
    """

    def __init__(self, entity_id: int, label: str, license_plate: str):
        """
        初始化一个汽车实例。

        Args:
            entity_id (int): 唯一ID。
            label (str): 标签，例如 '蓝色轿车'。
            license_plate (str): 唯一的车牌号。
        """
        initial_state = {
            'license_plate': license_plate,
            'status': 'parked'  # 默认状态：已停放
        }
        super().__init__(entity_id, label, initial_state)
