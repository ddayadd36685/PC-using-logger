from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from timetracker.storage.repository import Repository


@dataclass(frozen=True)
class MetricQuery:
    start_date: str
    end_date: str
    category_type: str
    top_n: int = 10


class BaseMetric(ABC):
    metric_id: str
    display_name: str

    @abstractmethod
    def compute(self, query: MetricQuery, repo: Repository) -> dict:
        raise NotImplementedError()
