from __future__ import annotations

from datetime import datetime, timedelta

from timetracker.analytics.base_metric import BaseMetric, MetricQuery
from timetracker.analytics.metric_registry import registry
from timetracker.storage.repository import Repository


class TrendMetric(BaseMetric):
    metric_id = "trend"
    display_name = "趋势"

    def compute(self, query: MetricQuery, repo: Repository) -> dict:
        rows = repo.get_aggregates(query.start_date, query.end_date, query.category_type)
        totals: dict[str, int] = {}
        by_date: dict[str, dict[str, int]] = {}
        for row in rows:
            totals[row.category_key] = totals.get(row.category_key, 0) + row.duration_sec
            day_map = by_date.setdefault(row.date, {})
            day_map[row.category_key] = day_map.get(row.category_key, 0) + row.duration_sec
        ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
        top_keys = [key for key, _ in ranked[: query.top_n]]
        dates = _iter_dates(query.start_date, query.end_date)
        series = []
        for key in top_keys:
            name = repo.get_display_name(key, query.start_date, query.end_date)
            values = [by_date.get(day, {}).get(key, 0) for day in dates]
            series.append({"key": key, "name": name, "values": values})
        return {"dates": dates, "series": series}


def _iter_dates(start: str, end: str) -> list[str]:
    begin = datetime.fromisoformat(start).date()
    finish = datetime.fromisoformat(end).date()
    current = begin
    items = []
    while current <= finish:
        items.append(current.isoformat())
        current += timedelta(days=1)
    return items


registry.register(TrendMetric)
