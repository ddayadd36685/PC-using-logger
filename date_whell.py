import sys
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout
from PySide6.QtGui import QPainter, QColor, QWheelEvent
from PySide6.QtCore import QAbstractAnimation, Qt, QPropertyAnimation, QEasingCurve, Property, QTimer, QRectF

class ScrollWheelWidget(QWidget):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = [str(item) for item in items]
        self._offset = 0.0  # 当前滚动的浮点偏移量
        self.item_height = 40  # 每个列表项的基础高度
        
        self.setMinimumSize(100, 200)
        
        # 滚动停止检测定时器
        self.stop_timer = QTimer(self)
        self.stop_timer.setSingleShot(True)
        self.stop_timer.setInterval(150) # 150毫秒无滚轮事件则认为滚动停止
        self.stop_timer.timeout.connect(self._snap_to_nearest)
        
        # 吸附动画
        self.animation = QPropertyAnimation(self, b"offset", self)
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.Type.OutQuad)

    # 定义 offset 属性，供 QPropertyAnimation 使用
    def get_offset(self):
        return self._offset

    def set_offset(self, value):
        self._offset = value
        self.update()

    offset = Property(float, get_offset, set_offset)

    @property
    def current_index(self):
        return int(round(self._offset))

    @property
    def current_value(self):
        idx = max(0, min(self.current_index, len(self.items) - 1))
        return self.items[idx]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        center_y = height / 2.0

        # 绘制中心选中区域的高亮线 (iOS 风格的上下两条线)
        painter.setPen(QColor(200, 200, 200, 150))
        painter.drawLine(10, center_y - self.item_height / 2, width - 10, center_y - self.item_height / 2)
        painter.drawLine(10, center_y + self.item_height / 2, width - 10, center_y + self.item_height / 2)

        # 可视范围内的最大项数（上下各延展几项）
        visible_half_count = int((height / 2) / self.item_height) + 1
        
        base_index = int(self._offset)
        remainder = self._offset - base_index

        font = self.font()
        font.setBold(True)

        for i in range(-visible_half_count - 1, visible_half_count + 2):
            idx = base_index + i
            
            # 限制索引在有效范围内
            if 0 <= idx < len(self.items):
                # 距离中心的相对浮点距离
                distance = i - remainder
                
                # 计算 Y 坐标
                y_pos = center_y + distance * self.item_height
                
                # 计算衰减比例 (边缘处趋近于 0，中心为 1)
                max_distance = (height / 2.0) / self.item_height
                ratio = 1.0 - (abs(distance) / max_distance)
                
                if ratio > 0:
                    # 动态调整透明度 (二次方衰减让渐变消失更自然)
                    alpha = int(255 * (ratio ** 1.5))
                    painter.setPen(QColor(50, 50, 50, alpha))
                    
                    # 动态调整字体大小 (中心最大)
                    current_font_size = 12 + int(6 * ratio)
                    font.setPointSize(current_font_size)
                    painter.setFont(font)
                    
                    # 绘制文字
                    rect = QRectF(0, y_pos - self.item_height / 2, width, self.item_height)
                    painter.drawText(rect, Qt.AlignCenter, self.items[idx])

    def wheelEvent(self, event: QWheelEvent):
        # 停止正在运行的动画
        if self.animation.state() == QAbstractAnimation.State.Running:
            self.animation.stop()

        # 获取滚动增量并更新 offset
        delta = event.angleDelta().y()
        scroll_steps = delta / 120.0  # 鼠标滚轮标准一格是 120
        
        # 调整滚动灵敏度
        self._offset -= scroll_steps * 0.5 
        
        # 边界限制
        if self._offset < 0:
            self._offset = 0.0
        elif self._offset > len(self.items) - 1:
            self._offset = float(len(self.items) - 1)

        self.update()
        
        # 重置定时器，如果停止滚动，则触发吸附
        self.stop_timer.start()

    def _snap_to_nearest(self):
        """动画滚动到最近的整数索引"""
        target_offset = float(round(self._offset))
        
        # 边界安全检查
        target_offset = max(0.0, min(target_offset, len(self.items) - 1))
        
        self.animation.setStartValue(self._offset)
        self.animation.setEndValue(target_offset)
        self.animation.start()


# 测试用窗口
class DateTimePicker(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("iOS Style Date Picker")
        self.resize(300, 250)
        self.setStyleSheet("background-color: white;")

        layout = QHBoxLayout(self)
        
        # 生成测试数据：月份和日期
        months = [f"{i}月" for i in range(1, 13)]
        days = [f"{i}日" for i in range(1, 32)]
        
        self.month_wheel = ScrollWheelWidget(months)
        self.day_wheel = ScrollWheelWidget(days)
        
        layout.addWidget(self.month_wheel)
        layout.addWidget(self.day_wheel)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DateTimePicker()
    window.show()
    sys.exit(app.exec())
