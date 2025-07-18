from .prop import Prop


class Cargo(Prop):
    """
    货物（Cargo），是 Prop 的一种。
    它具有如“重量”等货物专属的属性。
    """

    def __init__(self, entity_id: int, label: str, weight_kg: float, is_fragile: bool = False):
        """
        初始化一个货物实例。

        Args:
            entity_id (int): 唯一ID。
            label (str): 标签。
            weight_kg (float): 货物的重量（公斤）。
            is_fragile (bool): 货物是否为易碎品。
        """
        # 1. 构建该子类专属的初始状态字典
        initial_state = {
            'weight_kg': weight_kg,
            'is_fragile': is_fragile,
            'is_held': False,  # 默认状态：未被持有
            'location': 'warehouse_A'  # 默认位置
        }

        # 2. 调用父类(Entity)的构造函数，将ID、标签和我们构建的状态传进去
        super().__init__(entity_id, label, initial_state)
