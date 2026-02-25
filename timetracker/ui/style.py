from __future__ import annotations


def build_style() -> str:
    return """
    QWidget {
        color: #D7E2F1;
        font-family: "Microsoft YaHei";
        font-size: 12px;
    }
    QMainWindow {
        background-color: #0A0F1B;
    }
    QTabWidget::pane {
        border: 1px solid rgba(0, 229, 255, 80);
        border-radius: 10px;
        background-color: rgba(10, 15, 27, 220);
    }
    QTabBar::tab {
        background: rgba(20, 30, 48, 180);
        padding: 8px 16px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        margin-right: 6px;
    }
    QTabBar::tab:selected {
        background: rgba(0, 229, 255, 120);
        color: #0A0F1B;
    }
    QTabBar::tab:hover {
        background: rgba(124, 77, 255, 140);
    }
    QFrame#HudPanel {
        background: rgba(18, 28, 45, 200);
        border: 1px solid rgba(0, 229, 255, 120);
        border-radius: 12px;
        padding: 12px;
    }
    QFrame#KpiCard {
        background: rgba(10, 18, 32, 210);
        border: 1px solid rgba(124, 77, 255, 140);
        border-radius: 12px;
        padding: 10px;
    }
    QLabel#KpiTitle {
        font-size: 12px;
        color: #7CEBFF;
    }
    QLabel#KpiValue {
        font-size: 22px;
        font-weight: 600;
        color: #E5F4FF;
    }
    QLabel#KpiSub {
        font-size: 11px;
        color: #9BB2C8;
    }
    QLabel#HudTitle {
        font-size: 13px;
        color: #7CEBFF;
        letter-spacing: 1px;
    }
    QLabel {
        color: #D7E2F1;
    }
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(0, 229, 255, 200), stop:1 rgba(124, 77, 255, 200));
        color: #0A0F1B;
        border: 1px solid rgba(0, 229, 255, 160);
        border-radius: 8px;
        padding: 6px 16px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(0, 229, 255, 255), stop:1 rgba(255, 109, 0, 220));
    }
    QComboBox, QDateEdit, QSpinBox, QLineEdit {
        background: rgba(12, 20, 36, 220);
        border: 1px solid rgba(124, 77, 255, 150);
        border-radius: 6px;
        padding: 4px 8px;
    }
    QComboBox QAbstractItemView {
        font-size: 12px;
    }
    QComboBox:hover, QDateEdit:hover, QSpinBox:hover, QLineEdit:hover {
        border: 1px solid rgba(0, 229, 255, 200);
    }
    QTableWidget {
        background: rgba(8, 12, 22, 200);
        border: 1px solid rgba(0, 229, 255, 80);
        border-radius: 8px;
        gridline-color: rgba(0, 229, 255, 40);
    }
    QHeaderView::section {
        background: rgba(20, 30, 48, 200);
        color: #8FE7FF;
        border: none;
        padding: 6px 8px;
    }
    QProgressBar {
        background: rgba(12, 20, 36, 220);
        border: 1px solid rgba(0, 229, 255, 80);
        border-radius: 6px;
        text-align: center;
    }
    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(0, 229, 255, 200), stop:1 rgba(124, 77, 255, 200));
        border-radius: 6px;
    }
    QCheckBox {
        spacing: 8px;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid rgba(0, 229, 255, 150);
        background: rgba(12, 20, 36, 200);
        border-radius: 3px;
    }
    QCheckBox::indicator:checked {
        background: rgba(0, 229, 255, 220);
    }
    """
