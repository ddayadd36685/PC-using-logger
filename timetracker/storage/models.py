from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FocusSlice:
    ts: int
    date: str
    process_name: str
    category_type: str
    category_key: str
    category_name: str
    duration_sec: int = 1
    app_display: Optional[str] = None
    window_title: Optional[str] = None
    browser_name: Optional[str] = None
    domain: Optional[str] = None
    url: Optional[str] = None


@dataclass(frozen=True)
class DayAggregate:
    date: str
    category_type: str
    category_key: str
    category_name: str
    duration_sec: int


@dataclass(frozen=True)
class HourAggregate:
    date: str
    hour: int
    category_type: str
    category_key: str
    category_name: str
    duration_sec: int
