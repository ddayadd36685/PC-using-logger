"""
PySide6 交互式环形饼图
- 环形（Donut）样式
- 点击扇区：分离悬浮 + 高亮（放大内外径 + 偏移）
- 中心显示选中扇区的比例

这是一个 PySide6 的问题，我直接给你完整实现代码。
核心思路：

用 QPainter 手动绘制环形饼图（drawPie + 内圆遮罩）
点击时通过极坐标计算判断点击位置落在哪个扇区（同时检查内外径范围），避免错位
选中扇区通过增大内外径 + 偏移圆心实现分离悬浮效果
中心显示比例文字
环形饼图，支持点击分离高亮donut_chart.pyPresented fileDone实现说明
核心设计思路
环形绘制 — 使用 QPainterPath.arcTo() 绘制外弧，然后反向绘制内弧，closeSubpath() 闭合，形成环形扇区。每个扇区之间留 GAP_DEG=1.2° 间隙。
点击检测（无错位） — 这是最关键的部分，分三步：
1. 计算点击点相对于「该扇区实际圆心」的距离
   → 选中扇区圆心有偏移，必须用偏移后的圆心来算，否则错位
2. 检查距离是否在 [inner_r, outer_r] 之间（环形区域）
3. 将偏移坐标转为极角，判断是否落在扇区角度范围内
选中高亮效果：
属性、正常、选中
外径、160、178（+18）
内径90、82（-8，环变厚）
圆心偏移、0、沿中心角方向 +14px
颜色、原色、lighter(130)
描边、无、白色 2px
中心文字 — 选中时显示标签 + 大号百分比；未选中时显示提示语。
"""

import sys
import math
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPainterPath
)


# ── 数据 ────────────────────────────────────────────────────────────────────
SLICES = [
    {"label": "产品 A", "value": 35, "color": QColor("#4F8EF7")},
    {"label": "产品 B", "value": 25, "color": QColor("#F7874F")},
    {"label": "产品 C", "value": 20, "color": QColor("#4FD4A8")},
    {"label": "产品 D", "value": 12, "color": QColor("#F7CF4F")},
    {"label": "产品 E", "value": 8,  "color": QColor("#C44FF7")},
]


class DonutChart(QWidget):
    # ── 样式常量 ──────────────────────────────────────────────────────────
    OUTER_R      = 160   # 正常外径
    INNER_R      = 90    # 正常内径
    SEL_OUTER_R  = 178   # 选中外径（放大）
    SEL_INNER_R  = 82    # 选中内径（缩小，让环更厚）
    SEL_OFFSET   = 14    # 选中扇区沿半径方向偏移量
    GAP_DEG      = 1.2   # 扇区间隙（度）

    def __init__(self, slices, parent=None):
        super().__init__(parent)
        self.slices = slices
        self.selected = None          # 当前选中索引

        total = sum(s["value"] for s in slices)
        # 预计算每个扇区的起始角度、跨度角度（Qt 单位：1/16 度）
        self._angles = []             # [(start_deg, span_deg), ...]
        cur = 0.0
        for s in slices:
            span = s["value"] / total * 360.0
            self._angles.append((cur, span))
            cur += span

        self.setMinimumSize(500, 500)
        self.setAttribute(Qt.WA_StyledBackground, True)

    # ── 绘制 ─────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx, cy = self.width() / 2, self.height() / 2

        # 背景
        painter.fillRect(self.rect(), QColor("#1A1D2E"))

        # ── 绘制每个扇区 ──────────────────────────────────────────────
        for i, (s, (start_deg, span_deg)) in enumerate(
                zip(self.slices, self._angles)):

            selected = (i == self.selected)

            outer_r = self.SEL_OUTER_R if selected else self.OUTER_R
            inner_r = self.SEL_INNER_R if selected else self.INNER_R
            gap     = self.GAP_DEG

            # 选中扇区：沿中心角方向偏移
            ox, oy = cx, cy
            if selected:
                mid_rad = math.radians(start_deg + span_deg / 2)
                ox += self.SEL_OFFSET * math.cos(mid_rad)
                oy += self.SEL_OFFSET * math.sin(mid_rad)

            # 用 QPainterPath 绘制环形扇区（外弧 - 内弧）
            path = self._make_slice_path(
                ox, oy, inner_r, outer_r,
                start_deg + gap / 2,
                span_deg  - gap
            )

            # 颜色：选中加亮
            color = QColor(s["color"])
            if selected:
                color = color.lighter(130)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawPath(path)

            # 选中时加白色描边
            if selected:
                pen = QPen(QColor(255, 255, 255, 180), 2)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(path)
                painter.setPen(Qt.NoPen)

        # ── 中心文字 ──────────────────────────────────────────────────
        self._draw_center(painter, cx, cy)

        # ── 图例 ──────────────────────────────────────────────────────
        self._draw_legend(painter)

    def _make_slice_path(self, cx, cy, r_in, r_out, start_deg, span_deg):
        """构造一个环形扇区的 QPainterPath"""
        path = QPainterPath()

        # Qt drawArc: 角度 0 = 3 点钟，逆时针为正 → 我们用标准数学坐标
        # QPainterPath.arcTo 使用角度单位（度），方向：逆时针正
        # 但 Qt 的 Y 轴朝下，所以传入时 start 取负，方向用 -span
        outer_rect = QRect(
            int(cx - r_out), int(cy - r_out),
            int(r_out * 2), int(r_out * 2)
        )
        inner_rect = QRect(
            int(cx - r_in), int(cy - r_in),
            int(r_in * 2), int(r_in * 2)
        )

        # 外弧起点（Qt 角度：从 3 点钟顺时针为负）
        # 我们的 start_deg 是数学角（3 点钟=0，顺时针增）
        # 转 Qt 角度：qt_angle = -start_deg（Qt 逆时针为正，Y 轴朝下抵消）
        qt_start = -start_deg
        qt_span  = -span_deg   # 顺时针

        path.arcMoveTo(outer_rect, qt_start)
        path.arcTo(outer_rect, qt_start, qt_span)

        # 连到内弧终点，再反向画内弧
        path.arcTo(inner_rect, qt_start + qt_span, -qt_span)
        path.closeSubpath()
        return path

    def _draw_center(self, painter, cx, cy):
        if self.selected is None:
            # 默认显示"总计"
            painter.setPen(QColor("#FFFFFF"))
            font = QFont("Arial", 13, QFont.Bold)
            painter.setFont(font)
            painter.drawText(
                QRect(int(cx)-60, int(cy)-18, 120, 36),
                Qt.AlignCenter, "点击查看详情"
            )
        else:
            s = self.slices[self.selected]
            total = sum(x["value"] for x in self.slices)
            pct = s["value"] / total * 100

            # 标签
            painter.setPen(QColor("#CCCCCC"))
            painter.setFont(QFont("Arial", 11))
            painter.drawText(
                QRect(int(cx)-70, int(cy)-36, 140, 28),
                Qt.AlignCenter, s["label"]
            )
            # 百分比（大字）
            painter.setPen(QColor(s["color"]).lighter(140))
            painter.setFont(QFont("Arial", 28, QFont.Bold))
            painter.drawText(
                QRect(int(cx)-70, int(cy)-12, 140, 44),
                Qt.AlignCenter, f"{pct:.1f}%"
            )

    def _draw_legend(self, painter):
        total = sum(s["value"] for s in self.slices)
        x0, y0 = 20, 20
        for i, s in enumerate(self.slices):
            y = y0 + i * 28
            # 色块
            painter.setBrush(QBrush(s["color"]))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(x0, y, 16, 16, 3, 3)
            # 文字
            painter.setPen(QColor("#DDDDDD") if i != self.selected
                           else QColor(s["color"]).lighter(140))
            font = QFont("Arial", 10,
                         QFont.Bold if i == self.selected else QFont.Normal)
            painter.setFont(font)
            pct = s["value"] / total * 100
            painter.drawText(x0 + 24, y + 13,
                             f"{s['label']}  {pct:.1f}%")

    # ── 点击检测 ─────────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return

        cx, cy = self.width() / 2, self.height() / 2
        mx, my = event.position().x(), event.position().y()

        # 对每个扇区做精确碰撞检测
        for i, (s, (start_deg, span_deg)) in enumerate(
                zip(self.slices, self._angles)):

            selected = (i == self.selected)
            outer_r = self.SEL_OUTER_R if selected else self.OUTER_R
            inner_r = self.SEL_INNER_R if selected else self.INNER_R

            # 当前扇区的实际圆心（选中时有偏移）
            ox, oy = cx, cy
            if selected:
                mid_rad = math.radians(start_deg + span_deg / 2)
                ox += self.SEL_OFFSET * math.cos(mid_rad)
                oy += self.SEL_OFFSET * math.sin(mid_rad)

            # 计算点击点相对于该扇区圆心的极坐标
            dx, dy = mx - ox, my - oy
            dist = math.hypot(dx, dy)

            if not (inner_r <= dist <= outer_r):
                continue

            # 角度（数学坐标，顺时针，0=3点钟）
            angle_deg = math.degrees(math.atan2(dy, dx)) % 360

            # 检查是否在扇区角度范围内（考虑间隙）
            gap = self.GAP_DEG
            a_start = (start_deg + gap / 2) % 360
            a_end   = (start_deg + span_deg - gap / 2) % 360

            in_angle = self._angle_in_range(angle_deg, a_start, a_end)
            if in_angle:
                # 点击已选中 → 取消选中
                self.selected = None if self.selected == i else i
                self.update()
                return

        # 点击空白区域 → 取消选中
        self.selected = None
        self.update()

    @staticmethod
    def _angle_in_range(angle, start, end):
        """判断 angle 是否在 [start, end] 范围内（处理跨 0 情况）"""
        if start <= end:
            return start <= angle <= end
        else:  # 跨 0°
            return angle >= start or angle <= end


# ── 主窗口 ──────────────────────────────────────────────────────────────────
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("环形饼图 · PySide6")
        self.setStyleSheet("background:#1A1D2E;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("销售占比分析")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "color:#FFFFFF; font-size:18px; font-weight:bold;"
            "padding:16px 0 4px 0; background:transparent;"
        )
        layout.addWidget(title)

        chart = DonutChart(SLICES)
        layout.addWidget(chart)

        hint = QLabel("点击扇区查看详情 · 再次点击取消选中")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(
            "color:#666888; font-size:11px; padding:8px; background:transparent;"
        )
        layout.addWidget(hint)

        self.resize(540, 580)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
