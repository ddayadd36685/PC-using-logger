from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from timetracker.config.config_manager import ConfigManager


class RestOverlay(QWidget):
    def __init__(self, config: ConfigManager) -> None:
        super().__init__()
        self._config = config
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._title = QLabel("该休息啦")
        title_font = QFont("Microsoft YaHei", 20)
        title_font.setWeight(QFont.Weight.DemiBold)
        self._title.setFont(title_font)
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._countdown = QLabel("05:00")
        countdown_font = QFont("Microsoft YaHei", 28)
        countdown_font.setWeight(QFont.Weight.DemiBold)
        self._countdown.setFont(countdown_font)
        self._countdown.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._countdown.setStyleSheet("color:#7CEBFF;")

        self._start_button = QPushButton("开始休息")
        self._delay_button = QPushButton()
        self._skip_button = QPushButton("跳过")

        button_row = QHBoxLayout()
        button_row.addWidget(self._start_button)
        button_row.addWidget(self._delay_button)
        button_row.addWidget(self._skip_button)

        frame = QFrame()
        frame.setObjectName("HealthOverlay")
        layout = QVBoxLayout(frame)
        layout.addWidget(self._title)
        layout.addWidget(self._countdown)
        layout.addLayout(button_row)

        root = QVBoxLayout(self)
        root.addWidget(frame, alignment=Qt.AlignmentFlag.AlignCenter)
        root.setContentsMargins(40, 40, 40, 40)
        frame.setStyleSheet(
            "QFrame#HealthOverlay {"
            "background: rgba(10, 18, 32, 230);"
            "border: 1px solid rgba(0, 229, 255, 160);"
            "border-radius: 16px;"
            "padding: 24px;"
            "}"
        )
        self._update_buttons()

    def set_callbacks(self, on_start, on_delay, on_skip) -> None:
        self._start_button.clicked.connect(on_start)
        self._delay_button.clicked.connect(on_delay)
        self._skip_button.clicked.connect(self._wrap_skip(on_skip))

    def show_overlay(self) -> None:
        self._update_buttons()
        self.showFullScreen()

    def hide_overlay(self) -> None:
        self.hide()

    def update_countdown(self, seconds: int) -> None:
        minutes = max(0, seconds) // 60
        secs = max(0, seconds) % 60
        self._countdown.setText(f"{minutes:02d}:{secs:02d}")

    def _update_buttons(self) -> None:
        delay_min = self._config.get_int("health_delay_min")
        skip_max = self._config.get_int("health_skip_max")
        self._delay_button.setText(f"延迟 {delay_min} 分钟")
        self._delay_button.setVisible(delay_min > 0)
        self._skip_button.setVisible(skip_max > 0)

    def _wrap_skip(self, on_skip):
        def handler() -> None:
            allowed = on_skip()
            if not allowed:
                self._skip_button.setEnabled(False)

        return handler
