from __future__ import annotations

from typing import Dict, Type

from timetracker.analytics.base_metric import BaseMetric


class MetricRegistry:
    def __init__(self) -> None:
        self._registry: Dict[str, Type[BaseMetric]] = {}

    def register(self, metric: Type[BaseMetric]) -> None:
        self._registry[metric.metric_id] = metric

    def get(self, metric_id: str) -> Type[BaseMetric]:
        return self._registry[metric_id]

    def list(self) -> list[str]:
        return list(self._registry.keys())


registry = MetricRegistry()
