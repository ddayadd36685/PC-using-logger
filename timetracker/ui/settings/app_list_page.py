from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from timetracker.config.config_manager import ConfigManager
from timetracker.storage.repository import Repository


class ToggleSwitch(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(40, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool) -> None:
        if self._checked == checked:
            return
        self._checked = checked
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._checked = not self._checked
        self.update()
        self.toggled.emit(self._checked)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect())
        radius = rect.height() / 2
        track_color = QColor("#00E5FF") if self._checked else QColor("#1E2A3C")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(rect, radius, radius)
        knob = rect.height() - 4
        x = rect.right() - knob - 2 if self._checked else rect.left() + 2
        painter.setBrush(QColor("#EAF3FF"))
        painter.drawEllipse(QRectF(x, rect.top() + 2, knob, knob))


class AppListPage(QWidget):
    def __init__(self, config: ConfigManager, repo: Repository, on_change: Callable[[], None]) -> None:
        super().__init__()
        self._config = config
        self._repo = repo
        self._on_change = on_change

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["软件", "操作"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setShowGrid(False)
        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        layout = QVBoxLayout()
        layout.addWidget(self._table)
        self.setLayout(layout)
        self.reload()

    def reload(self) -> None:
        apps = self._repo.get_recorded_apps()
        blocked = set(self._config.get_json("blocked_apps") or [])
        self._table.setRowCount(len(apps))
        for row, (key, name, total) in enumerate(apps):
            info_widget = QWidget()
            info_layout = QVBoxLayout(info_widget)
            info_layout.setContentsMargins(4, 2, 4, 2)
            info_layout.setSpacing(2)
            name_label = QLabel(name)
            time_label = QLabel(format_duration(total))
            time_label.setStyleSheet("color:#8EA6C2; font-size:11px;")
            info_layout.addWidget(name_label)
            info_layout.addWidget(time_label)
            self._table.setCellWidget(row, 0, info_widget)
            info_item = QTableWidgetItem()
            info_item.setData(Qt.ItemDataRole.UserRole, key)
            self._table.setItem(row, 0, info_item)

            controls = QWidget()
            controls_layout = QHBoxLayout(controls)
            controls_layout.setContentsMargins(4, 0, 4, 0)
            controls_layout.setSpacing(8)
            toggle = ToggleSwitch(key in blocked)
            toggle.toggled.connect(lambda checked, k=key: self._toggle_block(k, checked))
            delete_btn = QPushButton("删除")
            delete_btn.setFixedHeight(22)
            delete_btn.setMinimumWidth(52)
            delete_btn.setStyleSheet("padding:2px 10px; font-size:10px;")
            delete_btn.clicked.connect(lambda _checked=False, k=key, n=name: self._delete_app(k, n))
            controls_layout.addWidget(toggle)
            controls_layout.addWidget(delete_btn)
            controls_layout.addStretch(1)
            self._table.setCellWidget(row, 1, controls)
            self._table.setRowHeight(row, 44)

        self._table.resizeColumnsToContents()

    def _toggle_block(self, key: str, checked: bool) -> None:
        blocked = set(self._config.get_json("blocked_apps") or [])
        if checked:
            blocked.add(key)
        else:
            blocked.discard(key)
        self._config.set("blocked_apps", sorted(blocked))
        self._on_change()

    def _delete_app(self, key: str, name: str) -> None:
        result = QMessageBox.question(self, "确认删除", f"确定要删除 {name} 的全部数据吗？")
        if result != QMessageBox.StandardButton.Yes:
            return
        self._repo.delete_category_data(key)
        blocked = set(self._config.get_json("blocked_apps") or [])
        if key in blocked:
            blocked.discard(key)
            self._config.set("blocked_apps", sorted(blocked))
        self.reload()
        self._on_change()


def format_duration(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 3600 % 60
    return f"{hours}:{minutes:02d}:{seconds:02d}"
