"""
机器人能力定义

定义了机器人可能拥有的各种能力类型，
用于技能的前置条件检查和机器人能力管理。
"""

from enum import Enum


class Capability(Enum):
    """机器人能力枚举"""
    
    # 移动能力
    NAVIGATE = "navigate"           # 导航能力
    FLY = "fly"                     # 飞行能力
    DRIVE = "drive"                 # 驾驶能力
    WALK = "walk"                   # 行走能力
    
    # 感知能力
    SENSOR = "sensor"               # 传感器能力
    TAKE_PHOTO = "take_photo"       # 拍照能力
    SCAN = "scan"                   # 扫描能力
    DETECT = "detect"               # 检测能力
    
    # 操作能力
    MANIPULATE = "manipulate"       # 操作能力
    GRASP = "grasp"                 # 抓取能力
    CARRY_PAYLOAD = "carry_payload" # 载重能力
    LIFT = "lift"                   # 举升能力
    
    # 分析能力
    ANALYZE = "analyze"             # 分析能力
    PROCESS = "process"             # 处理能力
    IDENTIFY = "identify"           # 识别能力
    
    # 搜索能力
    SEARCH = "search"               # 搜索能力
    EXPLORE = "explore"             # 探索能力
    PATROL = "patrol"               # 巡逻能力
    
    # 通信能力
    COMMUNICATE = "communicate"     # 通信能力
    BROADCAST = "broadcast"         # 广播能力
    RECEIVE = "receive"             # 接收能力
    
    # 特殊能力
    IDENTIFY_ANOMALY = "identify_anomaly"  # 异常识别能力
    EMERGENCY_RESPONSE = "emergency_response"  # 应急响应能力
    AUTONOMOUS = "autonomous"       # 自主能力
    
    @property
    def name(self) -> str:
        """获取能力名称"""
        return self.value
    
    @property
    def display_name(self) -> str:
        """获取显示名称"""
        capability_names = {
            Capability.NAVIGATE: "导航能力",
            Capability.FLY: "飞行能力", 
            Capability.DRIVE: "驾驶能力",
            Capability.WALK: "行走能力",
            Capability.SENSOR: "传感器能力",
            Capability.TAKE_PHOTO: "拍照能力",
            Capability.SCAN: "扫描能力",
            Capability.DETECT: "检测能力",
            Capability.MANIPULATE: "操作能力",
            Capability.GRASP: "抓取能力",
            Capability.CARRY_PAYLOAD: "载重能力",
            Capability.LIFT: "举升能力",
            Capability.ANALYZE: "分析能力",
            Capability.PROCESS: "处理能力",
            Capability.IDENTIFY: "识别能力",
            Capability.SEARCH: "搜索能力",
            Capability.EXPLORE: "探索能力",
            Capability.PATROL: "巡逻能力",
            Capability.COMMUNICATE: "通信能力",
            Capability.BROADCAST: "广播能力",
            Capability.RECEIVE: "接收能力",
            Capability.IDENTIFY_ANOMALY: "异常识别能力",
            Capability.EMERGENCY_RESPONSE: "应急响应能力",
            Capability.AUTONOMOUS: "自主能力"
        }
        return capability_names.get(self, self.value)
    
    @property
    def description(self) -> str:
        """获取能力描述"""
        capability_descriptions = {
            Capability.NAVIGATE: "能够自主导航到指定位置",
            Capability.FLY: "能够在空中飞行",
            Capability.DRIVE: "能够在地面行驶",
            Capability.WALK: "能够在地面行走",
            Capability.SENSOR: "能够感知周围环境",
            Capability.TAKE_PHOTO: "能够拍摄照片",
            Capability.SCAN: "能够扫描周围环境",
            Capability.DETECT: "能够检测特定目标",
            Capability.MANIPULATE: "能够操作物体",
            Capability.GRASP: "能够抓取物体",
            Capability.CARRY_PAYLOAD: "能够携带负载",
            Capability.LIFT: "能够举升物体",
            Capability.ANALYZE: "能够分析数据",
            Capability.PROCESS: "能够处理信息",
            Capability.IDENTIFY: "能够识别目标",
            Capability.SEARCH: "能够搜索目标",
            Capability.EXPLORE: "能够探索未知区域",
            Capability.PATROL: "能够执行巡逻任务",
            Capability.COMMUNICATE: "能够与其他实体通信",
            Capability.BROADCAST: "能够广播信息",
            Capability.RECEIVE: "能够接收信息",
            Capability.IDENTIFY_ANOMALY: "能够识别异常情况",
            Capability.EMERGENCY_RESPONSE: "能够响应紧急情况",
            Capability.AUTONOMOUS: "能够自主决策和执行"
        }
        return capability_descriptions.get(self, "未知能力")


# 能力分类
class CapabilityCategory(Enum):
    """能力分类"""
    MOVEMENT = "movement"      # 移动类
    PERCEPTION = "perception"  # 感知类
    MANIPULATION = "manipulation"  # 操作类
    ANALYSIS = "analysis"      # 分析类
    SEARCH = "search"          # 搜索类
    COMMUNICATION = "communication"  # 通信类
    SPECIAL = "special"        # 特殊类


# 能力分类映射
CAPABILITY_CATEGORIES = {
    Capability.NAVIGATE: CapabilityCategory.MOVEMENT,
    Capability.FLY: CapabilityCategory.MOVEMENT,
    Capability.DRIVE: CapabilityCategory.MOVEMENT,
    Capability.WALK: CapabilityCategory.MOVEMENT,
    
    Capability.SENSOR: CapabilityCategory.PERCEPTION,
    Capability.TAKE_PHOTO: CapabilityCategory.PERCEPTION,
    Capability.SCAN: CapabilityCategory.PERCEPTION,
    Capability.DETECT: CapabilityCategory.PERCEPTION,
    
    Capability.MANIPULATE: CapabilityCategory.MANIPULATION,
    Capability.GRASP: CapabilityCategory.MANIPULATION,
    Capability.CARRY_PAYLOAD: CapabilityCategory.MANIPULATION,
    Capability.LIFT: CapabilityCategory.MANIPULATION,
    
    Capability.ANALYZE: CapabilityCategory.ANALYSIS,
    Capability.PROCESS: CapabilityCategory.ANALYSIS,
    Capability.IDENTIFY: CapabilityCategory.ANALYSIS,
    
    Capability.SEARCH: CapabilityCategory.SEARCH,
    Capability.EXPLORE: CapabilityCategory.SEARCH,
    Capability.PATROL: CapabilityCategory.SEARCH,
    
    Capability.COMMUNICATE: CapabilityCategory.COMMUNICATION,
    Capability.BROADCAST: CapabilityCategory.COMMUNICATION,
    Capability.RECEIVE: CapabilityCategory.COMMUNICATION,
    
    Capability.IDENTIFY_ANOMALY: CapabilityCategory.SPECIAL,
    Capability.EMERGENCY_RESPONSE: CapabilityCategory.SPECIAL,
    Capability.AUTONOMOUS: CapabilityCategory.SPECIAL
}


def get_capability_category(capability: Capability) -> CapabilityCategory:
    """获取能力分类"""
    return CAPABILITY_CATEGORIES.get(capability, CapabilityCategory.SPECIAL)


def get_capabilities_by_category(category: CapabilityCategory) -> list[Capability]:
    """根据分类获取能力列表"""
    return [cap for cap, cat in CAPABILITY_CATEGORIES.items() if cat == category]


def get_all_capabilities() -> list[Capability]:
    """获取所有能力"""
    return list(Capability)


def get_capability_by_name(name: str) -> Capability:
    """根据名称获取能力"""
    try:
        return Capability(name)
    except ValueError:
        raise ValueError(f"未知的能力名称: {name}") 