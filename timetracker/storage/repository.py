import threading
from datetime import date, datetime
from typing import List, Optional

from .db import Database
from .models import DayAggregate, FocusSlice, HourAggregate


class Repository:
    def __init__(self, db: Database, store_raw_events: bool = False) -> None:
        self._db = db
        self._store_raw_events = store_raw_events
        self._buffer: list[FocusSlice] = []
        self._lock = threading.Lock()

    def append_slice(self, slice_item: FocusSlice) -> None:
        with self._lock:
            self._buffer.append(slice_item)

    def flush(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            batch = list(self._buffer)
            self._buffer.clear()
        conn = self._db.connect()
        agg_rows = [
            (
                item.date,
                item.category_type,
                item.category_key,
                item.category_name,
                item.duration_sec,
            )
            for item in batch
        ]
        hour_rows = [
            (
                item.date,
                datetime.fromtimestamp(item.ts).hour,
                item.category_type,
                item.category_key,
                item.category_name,
                item.duration_sec,
            )
            for item in batch
        ]
        with conn:
            conn.executemany(
                """
                INSERT INTO day_aggregates (
                    date, category_type, category_key, category_name, duration_sec
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(date, category_key) DO UPDATE SET
                    duration_sec = duration_sec + excluded.duration_sec
                """,
                agg_rows,
            )
            conn.executemany(
                """
                INSERT INTO hour_aggregates (
                    date, hour, category_type, category_key, category_name, duration_sec
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(date, hour, category_key) DO UPDATE SET
                    duration_sec = duration_sec + excluded.duration_sec
                """,
                hour_rows,
            )
            if self._store_raw_events:
                event_rows = [
                    (
                        item.ts,
                        item.date,
                        item.process_name,
                        item.app_display,
                        item.window_title,
                        item.browser_name,
                        item.domain,
                        item.url,
                        item.category_type,
                        item.category_key,
                        item.category_name,
                        item.duration_sec,
                    )
                    for item in batch
                ]
                conn.executemany(
                    """
                    INSERT INTO focus_events (
                        ts, date, process_name, app_display, window_title,
                        browser_name, domain, url, category_type, category_key,
                        category_name, duration_sec
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    event_rows,
                )

    def get_aggregates(
        self,
        start_date: str,
        end_date: str,
        category_type: Optional[str] = None,
    ) -> List[DayAggregate]:
        conn = self._db.connect()
        params: list[str] = [start_date, end_date]
        sql = """
            SELECT date, category_type, category_key, category_name, duration_sec
            FROM day_aggregates
            WHERE date >= ? AND date <= ?
        """
        if category_type:
            sql += " AND category_type = ?"
            params.append(category_type)
        sql += " ORDER BY date ASC, duration_sec DESC"
        rows = conn.execute(sql, params).fetchall()
        return [
            DayAggregate(
                date=row["date"],
                category_type=row["category_type"],
                category_key=row["category_key"],
                category_name=row["category_name"],
                duration_sec=row["duration_sec"],
            )
            for row in rows
        ]

    def get_live_aggregates(
        self,
        start_date: str,
        end_date: str,
        category_type: Optional[str] = None,
    ) -> List[DayAggregate]:
        aggregates = self.get_aggregates(start_date, end_date, category_type)
        mapping: dict[tuple[str, str], DayAggregate] = {
            (item.date, item.category_key): item for item in aggregates
        }
        with self._lock:
            for item in self._buffer:
                if item.date < start_date or item.date > end_date:
                    continue
                if category_type and item.category_type != category_type:
                    continue
                key = (item.date, item.category_key)
                existing = mapping.get(key)
                if existing:
                    mapping[key] = DayAggregate(
                        date=existing.date,
                        category_type=existing.category_type,
                        category_key=existing.category_key,
                        category_name=existing.category_name,
                        duration_sec=existing.duration_sec + item.duration_sec,
                    )
                else:
                    mapping[key] = DayAggregate(
                        date=item.date,
                        category_type=item.category_type,
                        category_key=item.category_key,
                        category_name=item.category_name,
                        duration_sec=item.duration_sec,
                    )
        return sorted(mapping.values(), key=lambda row: (row.date, -row.duration_sec))

    def get_today_total(self) -> int:
        today = date.today().isoformat()
        conn = self._db.connect()
        row = conn.execute(
            "SELECT COALESCE(SUM(duration_sec), 0) AS total FROM day_aggregates WHERE date = ?",
            (today,),
        ).fetchone()
        base = int(row["total"]) if row else 0
        with self._lock:
            buffered = sum(item.duration_sec for item in self._buffer if item.date == today)
        return base + buffered

    def get_today_current(self, category_key: str) -> int:
        today = date.today().isoformat()
        conn = self._db.connect()
        row = conn.execute(
            """
            SELECT COALESCE(SUM(duration_sec), 0) AS total
            FROM day_aggregates
            WHERE date = ? AND category_key = ?
            """,
            (today, category_key),
        ).fetchone()
        base = int(row["total"]) if row else 0
        with self._lock:
            buffered = sum(
                item.duration_sec
                for item in self._buffer
                if item.date == today and item.category_key == category_key
            )
        return base + buffered

    def get_hour_aggregates(
        self,
        start_date: str,
        end_date: str,
        category_type: Optional[str] = None,
        category_keys: Optional[list[str]] = None,
    ) -> List[HourAggregate]:
        conn = self._db.connect()
        params: list[object] = [start_date, end_date]
        sql = """
            SELECT date, hour, category_type, category_key, category_name, duration_sec
            FROM hour_aggregates
            WHERE date >= ? AND date <= ?
        """
        if category_type:
            sql += " AND category_type = ?"
            params.append(category_type)
        if category_keys:
            placeholders = ",".join("?" for _ in category_keys)
            sql += f" AND category_key IN ({placeholders})"
            params.extend(category_keys)
        sql += " ORDER BY date ASC, hour ASC, duration_sec DESC"
        rows = conn.execute(sql, params).fetchall()
        return [
            HourAggregate(
                date=row["date"],
                hour=int(row["hour"]),
                category_type=row["category_type"],
                category_key=row["category_key"],
                category_name=row["category_name"],
                duration_sec=row["duration_sec"],
            )
            for row in rows
        ]

    def get_live_hour_aggregates(
        self,
        start_date: str,
        end_date: str,
        category_type: Optional[str] = None,
        category_keys: Optional[list[str]] = None,
    ) -> List[HourAggregate]:
        aggregates = self.get_hour_aggregates(start_date, end_date, category_type, category_keys)
        mapping: dict[tuple[str, int, str], HourAggregate] = {
            (item.date, item.hour, item.category_key): item for item in aggregates
        }
        with self._lock:
            for item in self._buffer:
                if item.date < start_date or item.date > end_date:
                    continue
                if category_type and item.category_type != category_type:
                    continue
                if category_keys and item.category_key not in category_keys:
                    continue
                hour = datetime.fromtimestamp(item.ts).hour
                key = (item.date, hour, item.category_key)
                existing = mapping.get(key)
                if existing:
                    mapping[key] = HourAggregate(
                        date=existing.date,
                        hour=existing.hour,
                        category_type=existing.category_type,
                        category_key=existing.category_key,
                        category_name=existing.category_name,
                        duration_sec=existing.duration_sec + item.duration_sec,
                    )
                else:
                    mapping[key] = HourAggregate(
                        date=item.date,
                        hour=hour,
                        category_type=item.category_type,
                        category_key=item.category_key,
                        category_name=item.category_name,
                        duration_sec=item.duration_sec,
                    )
        return sorted(mapping.values(), key=lambda row: (row.date, row.hour, -row.duration_sec))

    def get_display_name(self, category_key: str, start_date: str, end_date: str) -> str:
        conn = self._db.connect()
        row = conn.execute(
            """
            SELECT category_name
            FROM day_aggregates
            WHERE category_key = ? AND date >= ? AND date <= ?
            ORDER BY date DESC
            LIMIT 1
            """,
            (category_key, start_date, end_date),
        ).fetchone()
        return row["category_name"] if row else category_key

    def get_focus_events_range(
        self,
        start_ts: int,
        end_ts: int,
        category_type: Optional[str] = None,
        category_keys: Optional[list[str]] = None,
    ) -> list[tuple[int, str, int]]:
        conn = self._db.connect()
        params: list[object] = [start_ts, end_ts]
        sql = """
            SELECT ts, category_key, duration_sec
            FROM focus_events
            WHERE ts >= ? AND ts <= ?
        """
        if category_type:
            sql += " AND category_type = ?"
            params.append(category_type)
        if category_keys:
            placeholders = ",".join("?" for _ in category_keys)
            sql += f" AND category_key IN ({placeholders})"
            params.extend(category_keys)
        rows = conn.execute(sql, params).fetchall()
        result = [(int(row["ts"]), row["category_key"], int(row["duration_sec"])) for row in rows]
        with self._lock:
            for item in self._buffer:
                if item.ts < start_ts or item.ts > end_ts:
                    continue
                if category_type and item.category_type != category_type:
                    continue
                if category_keys and item.category_key not in category_keys:
                    continue
                result.append((item.ts, item.category_key, item.duration_sec))
        return result

    def get_recorded_apps(self) -> list[tuple[str, str, int]]:
        conn = self._db.connect()
        rows = conn.execute(
            """
            SELECT category_key, MAX(category_name) AS category_name, SUM(duration_sec) AS total
            FROM day_aggregates
            WHERE category_type = 'app'
            GROUP BY category_key
            ORDER BY total DESC
            """
        ).fetchall()
        totals: dict[str, int] = {row["category_key"]: int(row["total"]) for row in rows}
        names: dict[str, str] = {row["category_key"]: row["category_name"] for row in rows}
        with self._lock:
            for item in self._buffer:
                if item.category_type != "app":
                    continue
                totals[item.category_key] = totals.get(item.category_key, 0) + item.duration_sec
                names[item.category_key] = item.category_name
        return sorted(
            [(key, names.get(key, key), total) for key, total in totals.items()],
            key=lambda item: item[2],
            reverse=True,
        )

    def delete_category_data(self, category_key: str) -> None:
        with self._lock:
            self._buffer = [item for item in self._buffer if item.category_key != category_key]
        conn = self._db.connect()
        with conn:
            conn.execute("DELETE FROM focus_events WHERE category_key = ?", (category_key,))
            conn.execute("DELETE FROM hour_aggregates WHERE category_key = ?", (category_key,))
            conn.execute("DELETE FROM day_aggregates WHERE category_key = ?", (category_key,))

    def clear_data(self) -> None:
        conn = self._db.connect()
        with conn:
            conn.execute("DELETE FROM focus_events")
            conn.execute("DELETE FROM hour_aggregates")
            conn.execute("DELETE FROM day_aggregates")
