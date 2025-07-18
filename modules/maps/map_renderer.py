"""
现代化的异步MapRenderer实现

基于PyQt6的实时场景可视化工具，支持异步事件处理和GPU加速渲染。
提供2D物理地图和逻辑关系图的实时可视化。
# TODO: 测试通过, 初代先不考虑渲染的问题。
"""

import asyncio
import time
import numpy as np
import networkx as nx
from matplotlib import pyplot as plt
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# PyQt6 imports for modern async UI
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QFrame, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsTextItem,
    QGraphicsLineItem, QGraphicsPolygonItem
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QObject, QEvent, QRectF,
    QPointF, QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath,
    QLinearGradient, QRadialGradient
)


class RenderEvent(Enum):
    """渲染事件类型"""
    OBJECT_CREATED = "object_created"
    OBJECT_REMOVED = "object_removed" 
    OBJECT_UPDATED = "object_updated"
    RELATION_ADDED = "relation_added"
    RELATION_REMOVED = "relation_removed"
    RELATION_UPDATED = "relation_updated"
    HIGHLIGHT_OBJECT = "highlight_object"


@dataclass
class RenderMessage:
    """渲染消息数据结构"""
    event_type: RenderEvent
    obj_id: Optional[Any] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class AsyncRenderWorker(QObject):
    """异步渲染工作线程"""
    
    render_signal = pyqtSignal(RenderMessage)
    
    def __init__(self):
        super().__init__()
        self._running = False
        self._message_queue = asyncio.Queue()
        
    def start(self):
        """启动渲染工作线程"""
        self._running = True
        asyncio.create_task(self._process_messages())
        
    def stop(self):
        """停止渲染工作线程"""
        self._running = False
        
    async def post_message(self, message: RenderMessage):
        """发送渲染消息"""
        await self._message_queue.put(message)
        
    async def _process_messages(self):
        """处理渲染消息"""
        while self._running:
            try:
                # 等待消息
                message = await asyncio.wait_for(self._message_queue.get(), timeout=0.1)
                
                # 发送到UI线程
                self.render_signal.emit(message)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error processing render message: {e}")


class SpatialMapView(QGraphicsView):
    """2D物理空间地图视图"""
    
    def __init__(self, task_context: "TaskContext", template_library: "EntityTemplateLibrary"):
        # 确保QApplication存在
        self._ensure_qapplication()
        super().__init__()
        self.task_context = task_context
        self.template_lib = template_library
        self.highlighted_objects = set()
        
        # 初始化视图
        self._setup_view()
        
    def _ensure_qapplication(self):
        """确保QApplication实例存在"""
        from PyQt6.QtWidgets import QApplication
        import sys
        
        # 检查是否已经有QApplication实例
        app = QApplication.instance()
        if app is None:
            # 创建新的QApplication实例
            app = QApplication(sys.argv)
            
        return app
        
    def _setup_view(self):
        """设置视图属性"""
        # 设置视图属性
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 创建场景
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # 颜色映射
        self._colors = self._generate_color_map()
        self._object_items = {}  # 存储图形项引用
        
        # 设置场景边界
        self.scene.setSceneRect(-1000, -1000, 2000, 2000)
        
    def _generate_color_map(self):
        """生成颜色映射"""
        return {
            'building': QColor(100, 100, 100),
            'robot': QColor(0, 150, 255),
            'prop': QColor(255, 150, 0),
            'drone': QColor(0, 200, 100),
            'ground_vehicle': QColor(150, 0, 200),
            'cargo': QColor(255, 200, 0),
            'car': QColor(200, 100, 0),
            'truck': QColor(100, 50, 0),
            'equipment_failure': QColor(255, 0, 0),
            'security_breach': QColor(255, 0, 255)
        }
        
    def redraw(self):
        """重新绘制地图"""
        self.scene.clear()
        self._object_items.clear()
        
        # 从 TaskContext 获取所有对象
        config = self.task_context.get_config()
        environment = config.get('environment', {})
        scene_config = environment.get('scene_config', {})
        nodes = scene_config.get('nodes', [])
        
        for node in nodes:
            self._draw_object(node)
            
    def _draw_object(self, node_data):
        """绘制单个对象"""
        obj_id = node_data.get('id')
        properties = node_data.get('properties', {})
        shape = node_data.get('shape')
        
        if not shape:
            return
            
        # 获取对象类型和颜色
        obj_type = properties.get('type', 'unknown')
        category = properties.get('category', 'unknown')
        
        # 确定颜色
        color = self._colors.get(obj_type, self._colors.get(category, QColor(128, 128, 128)))
        
        # 绘制形状
        if shape.get('type') == 'rectangle':
            self._draw_rectangle(obj_id, shape, color, properties)
        elif shape.get('type') == 'circle':
            self._draw_circle(obj_id, shape, color, properties)
            
    def _draw_rectangle(self, obj_id, shape, color, properties):
        """绘制矩形对象"""
        min_corner = shape.get('min_corner', [0, 0])
        max_corner = shape.get('max_corner', [10, 10])
        
        x = min_corner[0]
        y = min_corner[1]
        width = max_corner[0] - min_corner[0]
        height = max_corner[1] - min_corner[1]
        
        # 创建矩形项
        rect_item = QGraphicsRectItem(x, y, width, height)
        rect_item.setBrush(QBrush(color))
        rect_item.setPen(QPen(QColor(0, 0, 0), 1))
        
        # 添加标签
        label = properties.get('label', str(obj_id))
        text_item = QGraphicsTextItem(label)
        text_item.setPos(x, y - 20)
        text_item.setDefaultTextColor(QColor(0, 0, 0))
        
        # 添加到场景
        self.scene.addItem(rect_item)
        self.scene.addItem(text_item)
        
        # 保存引用
        self._object_items[obj_id] = (rect_item, text_item)
        
    def _draw_circle(self, obj_id, shape, color, properties):
        """绘制圆形对象"""
        center = shape.get('center', [0, 0])
        radius = shape.get('radius', 5)
        
        x = center[0] - radius
        y = center[1] - radius
        diameter = radius * 2
        
        # 创建圆形项
        circle_item = QGraphicsEllipseItem(x, y, diameter, diameter)
        circle_item.setBrush(QBrush(color))
        circle_item.setPen(QPen(QColor(0, 0, 0), 1))
        
        # 添加标签
        label = properties.get('label', str(obj_id))
        text_item = QGraphicsTextItem(label)
        text_item.setPos(x, y - 20)
        text_item.setDefaultTextColor(QColor(0, 0, 0))
        
        # 添加到场景
        self.scene.addItem(circle_item)
        self.scene.addItem(text_item)
        
        # 保存引用
        self._object_items[obj_id] = (circle_item, text_item)
        
    def highlight_object(self, obj_id):
        """高亮显示对象"""
        if obj_id in self._object_items:
            item, text_item = self._object_items[obj_id]
            item.setPen(QPen(QColor(255, 255, 0), 3))  # 黄色高亮


class GraphMapView(QGraphicsView):
    """逻辑关系图视图"""
    
    def __init__(self, task_context: "TaskContext", template_library: "EntityTemplateLibrary"):
        # 确保QApplication存在
        self._ensure_qapplication()
        super().__init__()
        self.task_context = task_context
        self.template_lib = template_library
        
        # 初始化视图
        self._setup_view()
        
    def _ensure_qapplication(self):
        """确保QApplication实例存在"""
        from PyQt6.QtWidgets import QApplication
        import sys
        
        # 检查是否已经有QApplication实例
        app = QApplication.instance()
        if app is None:
            # 创建新的QApplication实例
            app = QApplication(sys.argv)
            
        return app
        
    def _setup_view(self):
        """设置视图属性"""
        # 设置视图属性
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 创建场景
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        # 颜色映射
        self._colors = self._generate_color_map()
        self._rel_colors = {}
        self._node_items = {}
        
        # 设置场景边界
        self.scene.setSceneRect(-500, -500, 1000, 1000)
        
    def _generate_color_map(self):
        """生成颜色映射"""
        return {
            'building': QColor(100, 100, 100),
            'robot': QColor(0, 150, 255),
            'prop': QColor(255, 150, 0),
            'drone': QColor(0, 200, 100),
            'ground_vehicle': QColor(150, 0, 200),
            'cargo': QColor(255, 200, 0),
            'car': QColor(200, 100, 0),
            'truck': QColor(100, 50, 0),
            'equipment_failure': QColor(255, 0, 0),
            'security_breach': QColor(255, 0, 255)
        }
        
    def redraw(self):
        """重新绘制关系图"""
        self.scene.clear()
        self._node_items.clear()
        self._rel_colors.clear()
        
        # 从 TaskContext 获取所有对象和关系
        config = self.task_context.get_config()
        environment = config.get('environment', {})
        scene_config = environment.get('scene_config', {})
        nodes = scene_config.get('nodes', [])
        edges = scene_config.get('edges', [])
        
        # 绘制节点
        for node in nodes:
            self._draw_node(node)
            
        # 绘制边
        for edge in edges:
            self._draw_edge(edge)
            
    def _draw_node(self, node_data):
        """绘制节点"""
        node_id = node_data.get('id')
        properties = node_data.get('properties', {})
        
        # 获取节点类型和颜色
        obj_type = properties.get('type', 'unknown')
        category = properties.get('category', 'unknown')
        
        # 确定颜色
        color = self._colors.get(obj_type, self._colors.get(category, QColor(128, 128, 128)))
        
        # 计算位置（简化布局）
        x = (hash(str(node_id)) % 20) * 50 - 500
        y = (hash(str(node_id)) % 15) * 50 - 350
        
        # 创建圆形节点
        radius = 20
        circle_item = QGraphicsEllipseItem(x - radius, y - radius, radius * 2, radius * 2)
        circle_item.setBrush(QBrush(color))
        circle_item.setPen(QPen(QColor(0, 0, 0), 2))
        
        # 添加标签
        label = properties.get('label', str(node_id))
        text_item = QGraphicsTextItem(label)
        text_item.setPos(x - 30, y + radius + 5)
        text_item.setDefaultTextColor(QColor(0, 0, 0))
        
        # 添加到场景
        self.scene.addItem(circle_item)
        self.scene.addItem(text_item)
        
        # 保存引用
        self._node_items[node_id] = circle_item
        
    def _draw_edge(self, edge_data):
        """绘制边"""
        source = edge_data.get('source')
        target = edge_data.get('target')
        edge_type = edge_data.get('type', 'relation')
        
        if source not in self._node_items or target not in self._node_items:
            return
            
        # 获取节点位置
        source_item = self._node_items[source]
        target_item = self._node_items[target]
        
        source_pos = source_item.rect().center()
        target_pos = target_item.rect().center()
        
        # 创建边
        line_item = QGraphicsLineItem(source_pos.x(), source_pos.y(), 
                                    target_pos.x(), target_pos.y())
        
        # 设置边的样式
        if edge_type == 'contains':
            pen = QPen(QColor(0, 255, 0), 2)  # 绿色
        elif edge_type == 'near':
            pen = QPen(QColor(255, 255, 0), 2)  # 黄色
        else:
            pen = QPen(QColor(128, 128, 128), 1)  # 灰色
            
        line_item.setPen(pen)
        
        # 添加到场景
        self.scene.addItem(line_item)


class MapRenderer(QMainWindow):
    """
    现代化的异步MapRenderer实现
    
    基于PyQt6的实时场景可视化工具，支持异步事件处理和GPU加速渲染。
    """
    
    def __init__(self, task_context: "TaskContext", template_library: "EntityTemplateLibrary", 
                 window_size: Tuple[int, int] = (1600, 900)):
        # 确保QApplication存在
        self._ensure_qapplication()
        
        super().__init__()
        
        self.task_context = task_context
        self.template_lib = template_library
        self.window_size = window_size
        
        # 初始化UI
        self._setup_ui()
        
        # 异步渲染工作线程
        self._render_thread = QThread()
        self._render_worker = AsyncRenderWorker()
        self._render_worker.moveToThread(self._render_thread)
        
        # 连接信号
        self._render_worker.render_signal.connect(self._handle_render_message)
        self._render_thread.started.connect(self._render_worker.start)
        
        # 启动渲染线程
        self._render_thread.start()
            
    def connect_to_task_context(self, task_context: "TaskContext"):
        """连接到TaskContext以监听事件"""
        if hasattr(task_context, 'subscribe'):
            task_context.subscribe(self._on_task_context_event)
            
    def _on_task_context_event(self, event: Dict[str, Any]):
        """处理TaskContext事件"""
        event_type = event.get('type')
        obj_id = event.get('object_id')
        data = event.get('data')
        
        # 触发重绘
        self._trigger_redraw()
            
    def _trigger_redraw(self):
        """触发重绘"""
        # 发送重绘消息到渲染线程
        message = RenderMessage(
            event_type=RenderEvent.OBJECT_UPDATED,
            data={'redraw': True}
        )
        self._render_worker.render_signal.emit(message)
            
    def _ensure_qapplication(self):
        """确保QApplication实例存在"""
        from PyQt6.QtWidgets import QApplication
        import sys
        
        # 检查是否已经有QApplication实例
        app = QApplication.instance()
        if app is None:
            # 创建新的QApplication实例
            app = QApplication(sys.argv)
            
        return app
            
    def _setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("Modern Async Map Renderer")
        self.resize(*self.window_size)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QHBoxLayout(central_widget)
        
        # 左侧空间地图视图
        self.spatial_view = SpatialMapView(self.task_context, self.template_lib)
        spatial_frame = QFrame()
        spatial_frame.setFrameStyle(QFrame.Shape.Box)
        spatial_layout = QVBoxLayout(spatial_frame)
        spatial_layout.addWidget(QLabel("2D Physical Map"))
        spatial_layout.addWidget(self.spatial_view)
        layout.addWidget(spatial_frame, 3)
        
        # 右侧关系图视图
        self.graph_view = GraphMapView(self.task_context, self.template_lib)
        graph_frame = QFrame()
        graph_frame.setFrameStyle(QFrame.Shape.Box)
        graph_layout = QVBoxLayout(graph_frame)
        graph_layout.addWidget(QLabel("Logical Relationship Graph"))
        graph_layout.addWidget(self.graph_view)
        layout.addWidget(graph_frame, 2)
        
        # 初始绘制
        self.spatial_view.redraw()
        self.graph_view.redraw()
        
    def _handle_render_message(self, message: RenderMessage):
        """处理渲染消息"""
        if message.event_type == RenderEvent.HIGHLIGHT_OBJECT:
            if message.obj_id:
                self.spatial_view.highlight_object(message.obj_id)
        else:
            # 重新绘制相关视图
            self.spatial_view.redraw()
            self.graph_view.redraw()
            
    def _on_object_event(self, **kwargs):
        """处理对象事件"""
        obj_id = kwargs.get('obj_id')
        if obj_id:
            message = RenderMessage(
                event_type=RenderEvent.HIGHLIGHT_OBJECT,
                obj_id=obj_id,
                data=kwargs
            )
            # 直接发送消息到UI线程
            self._render_worker.render_signal.emit(message)
            
    def _on_relation_event(self, **kwargs):
        """处理关系事件"""
        message = RenderMessage(
            event_type=RenderEvent.RELATION_UPDATED,
            data=kwargs
        )
        # 直接发送消息到UI线程
        self._render_worker.render_signal.emit(message)
        
    async def post_event(self, event_data: Dict[str, Any]):
        """异步事件接口，供外部调用"""
        event_type = event_data.get('type')
        obj_id = event_data.get('obj_id')
        
        if event_type == 'highlight':
            message = RenderMessage(
                event_type=RenderEvent.HIGHLIGHT_OBJECT,
                obj_id=obj_id,
                data=event_data
            )
        else:
            message = RenderMessage(
                event_type=RenderEvent.OBJECT_UPDATED,
                obj_id=obj_id,
                data=event_data
            )
            
        await self._render_worker.post_message(message)
        
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止渲染线程
        self._render_thread.quit()
        self._render_thread.wait()
        super().closeEvent(event)
        
    def run(self):
        """启动渲染器（同步方法，用于兼容性）"""
        self.show()
        return QApplication.instance().exec()