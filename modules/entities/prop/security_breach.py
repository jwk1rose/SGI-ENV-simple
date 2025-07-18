from typing import Dict

from .prop import Prop


class SecurityBreach(Prop):
    """
    安全隐患（SecurityBreach），代表一个需要处理的安全事件。

    它只包含位置和状态信息（'discovered' 或 'resolved'）。
    """

    def __init__(self, entity_id: int, label: str, breach_location: Dict):
        """
        初始化一个安全隐患事件。

        Args:
            entity_id (int): 该安全事件的唯一ID。
            label (str): 事件的简短描述，例如 '未授权人员闯入'。
            breach_location (Dict): 事件发生的地点坐标，例如 {'x': 150, 'y': 220}。
        """
        initial_state = {
            'type': 'security_breach',
            'breach_location': breach_location,
            'status': 'discovered'  # 初始状态为"已发现"
        }
        super().__init__(entity_id, label, initial_state)

    def resolve(self):
        """将该安全隐患的状态标记为"已解决"。"""
        print(f"[事件更新] 安全隐患 '{self.label}' (ID: {self.id}) 已被解决。")
        self.state['status'] = 'resolved'
