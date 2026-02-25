from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class IdlePopup(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(320, 120)
        title = QLabel("你刚刚离开电脑了吗？")
        title_font = QFont("Microsoft YaHei", 12)
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = QLabel("检测到 5 分钟无输入，已记录为 Idle")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color:#8EA6C2;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.addWidget(title)
        layout.addWidget(hint)
        self.setStyleSheet(
            "background: rgba(10, 18, 32, 230);"
            "border: 1px solid rgba(0, 229, 255, 160);"
            "border-radius: 12px;"
        )

    def show_popup(self) -> None:
        screen = self.screen()
        if screen is not None:
            rect = screen.availableGeometry()
            x = rect.center().x() - self.width() // 2
            y = rect.center().y() - self.height() // 2
            self.move(x, y)
        self.show()

    def hide_popup(self) -> None:
        self.hide()
