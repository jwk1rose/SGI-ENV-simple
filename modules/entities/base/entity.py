from typing import Dict, Any, Optional


class Entity:
    """
    模拟或场景中所有物体的基类。

    Entity 代表了世界中“物体”的最基本概念。
    它拥有一个唯一的标识符、一个人类可读的标签，以及一个描述其当前属性的状态。
    这个类被设计用来被更具体的类（如 Robot、Prop、Building 等）继承。
    """

    def __init__(self, entity_id: int, label: str, initial_state: Optional[Dict[str, Any]] = None):
        """
        初始化一个新的 Entity 实例。

        Args:
            entity_id (int): 该实体的唯一标识符。不应该存在两个ID相同的实体。
            label (str): 实体的人类可读名称，用于识别和调试。
            initial_state (Optional[State]): 一个定义实体初始状态的字典。
                                             如果为 None，状态将是一个空字典。
        """
        if not isinstance(entity_id, int):
            raise TypeError("'entity_id' 必须是整数。")
        if not label or not isinstance(label, str):
            raise TypeError("'label' 必须是一个非空的字符串。")

        self.id: int = entity_id
        self.label: str = label

        # state 是一个灵活的字典，用于存储与实体相关的任何属性，
        # 例如 'position', 'is_enabled', 'temperature' 等。
        self.state: Optional[Dict[str, Any]] = initial_state if initial_state is not None else {}

    def __repr__(self) -> str:
        """
        提供一个“官方”的、详细的对象字符串表示。
        对开发者和调试非常有用。
        """
        # 将 state 字典格式化为字符串，以提高可读性。
        state_str = ", ".join(f"{key}={value!r}" for key, value in self.state.items())
        return f"{self.__class__.__name__}(id={self.id}, label='{self.label}', state={{{state_str}}})"

    def __str__(self) -> str:
        """
        提供一个“非正式”的、易于阅读的对象字符串表示。
        对日志或用户输出很有用。
        """
        return f"[{self.id}] {self.label}"

    def get_state(self, key: str, default: Any = None) -> Any:
        """
        安全地从 state 字典中获取一个值。

        Args:
            key (str): 要检索的状态键。
            default (Any, optional): 如果键不存在时要返回的值。默认为 None。

        Returns:
            Any: 状态值，如果键未找到则为默认值。
        """
        return self.state.get(key, default)

    def set_state(self, key: str, value: Any):
        """
        在 state 字典中设置或更新一个值。

        Args:
            key (str): 要设置的状态键。
            value (Any): 键对应的新值。
        """
        self.state[key] = value
