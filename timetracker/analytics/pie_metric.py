from __future__ import annotations

from timetracker.analytics.base_metric import BaseMetric, MetricQuery
from timetracker.analytics.metric_registry import registry
from timetracker.storage.repository import Repository


class PieMetric(BaseMetric):
    metric_id = "pie"
    display_name = "时间分布"

    def compute(self, query: MetricQuery, repo: Repository) -> dict:
        rows = repo.get_aggregates(query.start_date, query.end_date, query.category_type)
        totals: dict[str, int] = {}
        for row in rows:
            totals[row.category_key] = totals.get(row.category_key, 0) + row.duration_sec
        ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
        top = ranked[: query.top_n]
        others = sum(value for _, value in ranked[query.top_n :])
        labels = [repo.get_display_name(key, query.start_date, query.end_date) for key, _ in top]
        values = [value for _, value in top]
        if others:
            labels.append("其他")
            values.append(others)
        return {
            "labels": labels,
            "values": values,
            "total": sum(values),
        }


registry.register(PieMetric)
