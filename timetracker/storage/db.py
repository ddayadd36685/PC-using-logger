import os
import sqlite3
import threading
from pathlib import Path


def default_db_path() -> Path:
    base = os.environ.get("APPDATA")
    if not base:
        base = str(Path.cwd())
    return Path(base) / "TimeTracker" / "data.db"


class Database:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or default_db_path()
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.Lock()

    def connect(self) -> sqlite3.Connection:
        with self._lock:
            if self._conn is None:
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
                self._conn.row_factory = sqlite3.Row
                self._conn.execute("PRAGMA journal_mode=WAL")
                self._conn.execute("PRAGMA synchronous=NORMAL")
                ensure_schema(self._conn)
            return self._conn

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS focus_events (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            ts            INTEGER NOT NULL,
            date          TEXT    NOT NULL,
            process_name  TEXT    NOT NULL,
            app_display   TEXT,
            window_title  TEXT,
            browser_name  TEXT,
            domain        TEXT,
            url           TEXT,
            category_type TEXT    NOT NULL,
            category_key  TEXT    NOT NULL,
            category_name TEXT    NOT NULL,
            duration_sec  INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS day_aggregates (
            date          TEXT NOT NULL,
            category_type TEXT NOT NULL,
            category_key  TEXT NOT NULL,
            category_name TEXT NOT NULL,
            duration_sec  INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (date, category_key)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS hour_aggregates (
            date          TEXT NOT NULL,
            hour          INTEGER NOT NULL,
            category_type TEXT NOT NULL,
            category_key  TEXT NOT NULL,
            category_name TEXT NOT NULL,
            duration_sec  INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (date, hour, category_key)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS focus_sessions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            date          TEXT    NOT NULL,
            category_type TEXT    NOT NULL,
            category_key  TEXT    NOT NULL,
            category_name TEXT    NOT NULL,
            started_at    INTEGER NOT NULL,
            ended_at      INTEGER NOT NULL,
            duration_sec  INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS app_config (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_date ON focus_events(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agg_date ON day_aggregates(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hour_agg_date ON hour_aggregates(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_date ON focus_sessions(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_key ON focus_sessions(date, category_key)")
    conn.commit()
