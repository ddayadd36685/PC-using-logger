from __future__ import annotations

from datetime import datetime, timedelta
from typing import cast

from PySide6.QtCore import QDate, QTimer, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from timetracker.config.config_manager import ConfigManager
from timetracker.storage.repository import Repository
from timetracker.ui.widgets.charts import PieChartWidget, PieEntry, TrendChartWidget


class StatsPage(QWidget):
    def __init__(self, repo: Repository, config: ConfigManager) -> None:
        super().__init__()
        self._repo = repo
        self._config = config
        self._selected_key: str | None = None
        self._color_map: dict[str, QColor] = {}
        self._color_index = 0
        self._palette = [
            QColor("#00E5FF"),
            QColor("#7C4DFF"),
            QColor("#00E676"),
            QColor("#FFEA00"),
            QColor("#FF6D00"),
            QColor("#FF1744"),
            QColor("#00B0FF"),
            QColor("#FF4081"),
        ]
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._refresh)
        self._auto_refresh = QTimer(self)
        self._auto_refresh.setInterval(1000)
        self._auto_refresh.timeout.connect(self._tick_refresh)
        self._auto_refresh.start()

        self._date_start = QDateEdit()
        self._date_start.setCalendarPopup(True)
        self._date_end = QDateEdit()
        self._date_end.setCalendarPopup(True)
        today = QDate.currentDate()
        self._date_end.setDate(today)
        self._date_start.setDate(today.addDays(-6))

        self._category_box = QComboBox()
        self._category_box.addItem("应用", "app")
        self._category_box.addItem("站点", "site")

        self._type_box = QComboBox()
        self._type_box.addItem("全部类型", "all")
        self._type_box.addItem("系统", "system")
        self._type_box.addItem("开发", "dev")
        self._type_box.addItem("娱乐", "entertain")
        self._type_box.addItem("其他", "other")

        self._granularity_box = QComboBox()
        self._granularity_box.addItem("按天", "day")
        self._granularity_box.addItem("按小时", "hour")

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索进程/站点")

        self._top_spin = QSpinBox()
        self._top_spin.setRange(3, 20)
        self._top_spin.setValue(8)

        self._refresh_button = QPushButton("刷新")
        self._refresh_button.clicked.connect(self._refresh)

        toolbar = QGridLayout()
        toolbar.addWidget(QLabel("开始"), 0, 0)
        toolbar.addWidget(self._date_start, 0, 1)
        toolbar.addWidget(QLabel("结束"), 0, 2)
        toolbar.addWidget(self._date_end, 0, 3)
        toolbar.addWidget(QLabel("维度"), 0, 4)
        toolbar.addWidget(self._category_box, 0, 5)
        toolbar.addWidget(QLabel("类型"), 0, 6)
        toolbar.addWidget(self._type_box, 0, 7)
        toolbar.addWidget(QLabel("Top"), 0, 8)
        toolbar.addWidget(self._top_spin, 0, 9)
        toolbar.addWidget(QLabel("粒度"), 0, 10)
        toolbar.addWidget(self._granularity_box, 0, 11)
        toolbar.addWidget(self._search_input, 0, 12)
        toolbar.addWidget(self._refresh_button, 0, 13)
        toolbar.setColumnStretch(12, 1)

        kpi_row = QHBoxLayout()
        self._kpi_total = _kpi_card("总使用时长")
        self._kpi_top = _kpi_card("最常用应用")
        self._kpi_count = _kpi_card("应用数量")
        self._kpi_change = _kpi_card("同比变化")
        kpi_row.addWidget(self._kpi_total["frame"])
        kpi_row.addWidget(self._kpi_top["frame"])
        kpi_row.addWidget(self._kpi_count["frame"])
        kpi_row.addWidget(self._kpi_change["frame"])

        self._pie_chart = PieChartWidget()
        self._pie_chart.slice_clicked.connect(self._handle_slice_click)
        self._trend_chart = TrendChartWidget()

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["名称", "时长", "占比", "强度"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setShowGrid(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSortingEnabled(False)
        self._table.cellClicked.connect(self._handle_table_click)

        left_panel = _panel("分布")
        cast(QVBoxLayout, left_panel.layout()).addWidget(self._pie_chart)

        right_panel = _panel("趋势")
        cast(QVBoxLayout, right_panel.layout()).addWidget(self._trend_chart)

        table_panel = _panel("Top 列表")
        cast(QVBoxLayout, table_panel.layout()).addWidget(self._table)

        charts_row = QHBoxLayout()
        charts_row.addWidget(left_panel, 1)
        charts_row.addWidget(right_panel, 2)

        grid = QGridLayout()
        grid.addLayout(kpi_row, 0, 0)
        grid.addLayout(toolbar, 1, 0)
        grid.addLayout(charts_row, 2, 0)
        grid.addWidget(table_panel, 3, 0)
        grid.setRowStretch(2, 1)
        grid.setRowStretch(3, 1)
        self.setLayout(grid)

        self._bind_refresh()
        self._refresh()

    def _bind_refresh(self) -> None:
        self._date_start.dateChanged.connect(self._schedule_refresh)
        self._date_end.dateChanged.connect(self._schedule_refresh)
        self._category_box.currentIndexChanged.connect(self._schedule_refresh)
        self._type_box.currentIndexChanged.connect(self._schedule_refresh)
        self._granularity_box.currentIndexChanged.connect(self._schedule_refresh)
        self._top_spin.valueChanged.connect(self._schedule_refresh)
        self._search_input.textChanged.connect(self._schedule_refresh)

    def refresh_now(self) -> None:
        self._refresh()

    def _schedule_refresh(self) -> None:
        self._refresh_timer.start(200)

    def _tick_refresh(self) -> None:
        if self.isVisible():
            self._refresh()

    def _refresh(self) -> None:
        start_date = self._date_start.date()
        end_date = self._date_end.date()
        if end_date < start_date:
            start_date, end_date = end_date, start_date
        start_str = start_date.toString("yyyy-MM-dd")
        end_str = end_date.toString("yyyy-MM-dd")
        category = self._category_box.currentData()
        top_n = int(self._top_spin.value())
        search = self._search_input.text().strip().lower()
        app_type = self._type_box.currentData()
        granularity = self._granularity_box.currentData()

        rows = self._repo.get_live_aggregates(start_str, end_str, category)
        filtered = self._apply_filters(rows, search, app_type, category)
        totals, name_map = self._accumulate_totals(filtered)
        sorted_items = sorted(totals.items(), key=lambda item: item[1], reverse=True)
        top_items = sorted_items[:top_n]
        others_total = sum(value for _, value in sorted_items[top_n:])
        self._ensure_colors([key for key, _ in sorted_items])
        entries: list[PieEntry] = [
            {
                "key": key,
                "label": name_map.get(key, key),
                "value": value,
                "color": self._color_map.get(key, QColor("#00E5FF")),
            }
            for key, value in top_items
        ]
        if others_total:
            entries.append(
                {
                    "key": "__others__",
                    "label": "其他",
                    "value": others_total,
                    "color": QColor("#455266"),
                }
            )
        total_sec = sum(entry["value"] for entry in entries)
        if self._selected_key not in totals:
            self._selected_key = None
        entries = self._normalize_entries(entries, category)
        self._pie_chart.set_data(entries, self._selected_key)
        trend_labels, trend_series = self._build_trend(
            sorted_items,
            start_date,
            end_date,
            category,
            granularity,
            self._selected_key,
        )
        self._trend_chart.set_data(trend_labels, trend_series)
        self._update_kpis(
            total_sec,
            entries,
            len(totals),
            start_str,
            end_str,
            category,
            search,
            app_type,
        )
        self._update_table(entries, total_sec)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor("#0A0F1B"))
        gradient.setColorAt(1.0, QColor("#0E1A2D"))
        painter.fillRect(self.rect(), gradient)
        painter.setPen(QPen(QColor(20, 40, 70, 120), 1))
        step = 28
        for x in range(0, self.width(), step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), step):
            painter.drawLine(0, y, self.width(), y)

    def _update_table(self, entries: list[PieEntry], total: int) -> None:
        self._table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            label = entry["label"]
            value = entry["value"]
            key = entry["key"]
            name_item = QTableWidgetItem(label)
            time_item = QTableWidgetItem(format_duration(value))
            percent = value * 100 / total if total else 0.0
            percent_item = QTableWidgetItem(f"{percent:.1f}%")
            name_item.setData(Qt.ItemDataRole.UserRole, key)
            time_item.setData(Qt.ItemDataRole.UserRole, value)
            percent_item.setData(Qt.ItemDataRole.UserRole, percent)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            percent_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(percent))
            bar.setTextVisible(False)
            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, time_item)
            self._table.setItem(row, 2, percent_item)
            self._table.setCellWidget(row, 3, bar)

    def _apply_filters(self, rows, search: str, app_type: str, category: str):
        blocked = set(self._config.get_json("blocked_apps") or [])
        result = []
        for row in rows:
            if category == "app" and row.category_key in blocked:
                continue
            name = row.category_name
            if category == "app" and name.lower().endswith(".exe"):
                name = name[:-4]
            name_lower = name.lower()
            key = row.category_key.lower()
            if search and search not in name_lower and search not in key:
                continue
            if app_type != "all":
                if category != "app":
                    continue
                if self._infer_app_type(row.category_key, name) != app_type:
                    continue
            result.append(row)
        return result

    def _normalize_entries(self, entries: list[PieEntry], category: str) -> list[PieEntry]:
        if category != "app":
            return entries
        normalized: list[PieEntry] = []
        for entry in entries:
            label = entry["label"]
            if label.lower().endswith(".exe"):
                label = label[:-4]
            normalized.append(
                {
                    "key": entry["key"],
                    "label": label,
                    "value": entry["value"],
                    "color": entry["color"],
                }
            )
        return normalized

    def _ensure_colors(self, keys: list[str]) -> None:
        for key in keys:
            if key not in self._color_map:
                color = self._palette[self._color_index % len(self._palette)]
                self._color_map[key] = color
                self._color_index += 1

    def _infer_app_type(self, key: str, name: str) -> str:
        text = f"{key} {name}".lower()
        dev_keywords = ["code", "pycharm", "idea", "studio", "terminal", "powershell", "cmd", "python", "git"]
        if any(keyword in text for keyword in dev_keywords):
            return "dev"
        entertainment_keywords = ["steam", "game", "bilibili", "douyin", "youtube", "spotify", "music", "video"]
        if any(keyword in text for keyword in entertainment_keywords):
            return "entertain"
        system_keywords = ["explorer", "system", "settings", "registry", "taskmgr"]
        if any(keyword in text for keyword in system_keywords):
            return "system"
        return "other"

    def _accumulate_totals(self, rows) -> tuple[dict[str, int], dict[str, str]]:
        totals: dict[str, int] = {}
        names: dict[str, str] = {}
        for row in rows:
            totals[row.category_key] = totals.get(row.category_key, 0) + row.duration_sec
            names[row.category_key] = row.category_name
        return totals, names

    def _update_kpis(
        self,
        total_sec: int,
        entries: list[PieEntry],
        app_count: int,
        start_str: str,
        end_str: str,
        category: str,
        search: str,
        app_type: str,
    ) -> None:
        avg_sec = total_sec // max(1, app_count)
        top_entry = (
            entries[0]
            if entries
            else {"key": "", "label": "-", "value": 0, "color": QColor("#455266")}
        )
        top_percent = top_entry["value"] * 100 / total_sec if total_sec else 0.0
        self._kpi_total["value"].setText(format_duration(total_sec))
        self._kpi_total["sub"].setText(f"平均单次 {format_duration(avg_sec)}")
        self._kpi_top["value"].setText(f"{top_entry['label']} {top_percent:.1f}%")
        self._kpi_top["sub"].setText(format_duration(top_entry["value"]))
        self._kpi_count["value"].setText(str(app_count))
        self._kpi_count["sub"].setText("活跃应用数")
        change_text, change_sub = self._compute_change(
            start_str, end_str, category, search, app_type, total_sec
        )
        self._kpi_change["value"].setText(change_text)
        self._kpi_change["sub"].setText(change_sub)

    def _compute_change(
        self,
        start_str: str,
        end_str: str,
        category: str,
        search: str,
        app_type: str,
        total_sec: int,
    ) -> tuple[str, str]:
        start_date = datetime.fromisoformat(start_str).date()
        end_date = datetime.fromisoformat(end_str).date()
        range_days = (end_date - start_date).days + 1
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=range_days - 1)
        prev_rows = self._repo.get_aggregates(prev_start.isoformat(), prev_end.isoformat(), category)
        prev_filtered = self._apply_filters(prev_rows, search, app_type, category)
        prev_totals, _ = self._accumulate_totals(prev_filtered)
        prev_total = sum(prev_totals.values())
        if prev_total <= 0:
            return "—", "上一周期"
        delta = (total_sec - prev_total) / prev_total * 100
        return f"{delta:+.1f}%", "上一周期"

    def _build_trend(
        self,
        sorted_items: list[tuple[str, int]],
        start_date: QDate,
        end_date: QDate,
        category: str,
        granularity: str,
        selected_key: str | None,
    ) -> tuple[list[str], list[dict]]:
        keys = [key for key, _ in sorted_items[:3]]
        if selected_key and selected_key != "__others__":
            keys = [selected_key]
        if not keys:
            return [], []
        if granularity == "day":
            return self._build_daily_trend(keys, start_date, end_date, category)
        return self._build_hourly_trend(keys, start_date, end_date, category)

    def _build_daily_trend(
        self,
        keys: list[str],
        start_date: QDate,
        end_date: QDate,
        category: str,
    ) -> tuple[list[str], list[dict]]:
        start_str = start_date.toString("yyyy-MM-dd")
        end_str = end_date.toString("yyyy-MM-dd")
        rows = self._repo.get_live_aggregates(start_str, end_str, category)
        by_date: dict[str, dict[str, int]] = {}
        for row in rows:
            day_map = by_date.setdefault(row.date, {})
            day_map[row.category_key] = day_map.get(row.category_key, 0) + row.duration_sec
        date_keys = _iter_dates(start_date, end_date)
        labels = [item[5:] for item in date_keys]
        series = []
        for key in keys:
            name = self._repo.get_display_name(key, start_str, end_str)
            if category == "app" and name.lower().endswith(".exe"):
                name = name[:-4]
            values = [by_date.get(day, {}).get(key, 0) for day in date_keys]
            series.append(
                {
                    "name": name,
                    "values": values,
                    "color": self._color_map.get(key, QColor("#00E5FF")),
                }
            )
        return labels, series

    def _build_hourly_trend(
        self,
        keys: list[str],
        start_date: QDate,
        end_date: QDate,
        category: str,
    ) -> tuple[list[str], list[dict]]:
        end_dt = datetime.now().replace(minute=0, second=0, microsecond=0)
        start_dt = end_dt - timedelta(hours=23)
        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")
        labels = _iter_time_labels(start_dt, 24, 3600)
        series_map = {key: [0] * 24 for key in keys}
        rows = self._repo.get_live_hour_aggregates(start_str, end_str, category, keys)
        for row in rows:
            hour_dt = datetime.fromisoformat(row.date) + timedelta(hours=row.hour)
            index = int((hour_dt.timestamp() - start_dt.timestamp()) / 3600)
            if 0 <= index < 24:
                series_map[row.category_key][index] += row.duration_sec
        series = []
        for key in keys:
            name = self._repo.get_display_name(key, start_str, end_str)
            if category == "app" and name.lower().endswith(".exe"):
                name = name[:-4]
            series.append(
                {
                    "name": name,
                    "values": series_map[key],
                    "color": self._color_map.get(key, QColor("#00E5FF")),
                }
            )
        return labels, series

    def _handle_slice_click(self, key: str) -> None:
        if key == "__others__":
            self._selected_key = None
        else:
            self._selected_key = key if self._selected_key != key else None
        self._refresh()

    def _handle_table_click(self, row: int, _column: int) -> None:
        item = self._table.item(row, 0)
        if item is None:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        if not key or key == "__others__":
            return
        self._selected_key = key if self._selected_key != key else None
        self._refresh()


def _panel(title: str) -> QFrame:
    frame = QFrame()
    frame.setObjectName("HudPanel")
    layout = QVBoxLayout()
    header = QLabel(title)
    header.setObjectName("HudTitle")
    layout.addWidget(header)
    layout.addSpacing(4)
    frame.setLayout(layout)
    return frame


def _kpi_card(title: str) -> dict:
    frame = QFrame()
    frame.setObjectName("KpiCard")
    layout = QVBoxLayout()
    title_label = QLabel(title)
    title_label.setObjectName("KpiTitle")
    value_label = QLabel("--")
    value_label.setObjectName("KpiValue")
    sub_label = QLabel("")
    sub_label.setObjectName("KpiSub")
    layout.addWidget(title_label)
    layout.addWidget(value_label)
    layout.addWidget(sub_label)
    frame.setLayout(layout)
    return {"frame": frame, "value": value_label, "sub": sub_label}


def format_duration(total_seconds: int) -> str:
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def _iter_dates(start: QDate, end: QDate) -> list[str]:
    items = []
    current = start
    while current <= end:
        items.append(current.toString("yyyy-MM-dd"))
        current = current.addDays(1)
    return items


def _iter_time_labels(start_dt: datetime, buckets: int, bucket_seconds: int) -> list[str]:
    labels = []
    current = start_dt
    for _ in range(buckets):
        if bucket_seconds == 60:
            labels.append(current.strftime("%H:%M"))
        else:
            labels.append(current.strftime("%m-%d %H"))
        current += timedelta(seconds=bucket_seconds)
    return labels
