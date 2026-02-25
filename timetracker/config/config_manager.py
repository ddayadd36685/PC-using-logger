import json
from typing import Any

from timetracker.storage.db import Database


DEFAULT_CONFIG: dict[str, Any] = {
    "sample_interval_ms": 1000,
    "health_enabled": False,
    "health_work_min": 45,
    "health_rest_min": 5,
    "health_delay_min": 5,
    "health_skip_max": 2,
    "health_whitelist": [],
    "blocked_apps": [],
    "privacy_mode": True,
    "floating_ball_visible": False,
    "store_raw_events": False,
    "autostart": False,
}


class ConfigManager:
    def __init__(self, db: Database) -> None:
        self._db = db
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        conn = self._db.connect()
        with conn:
            for key, value in DEFAULT_CONFIG.items():
                conn.execute(
                    "INSERT OR IGNORE INTO app_config(key, value) VALUES(?, ?)",
                    (key, json.dumps(value, ensure_ascii=False)),
                )

    def get(self, key: str) -> Any:
        conn = self._db.connect()
        row = conn.execute("SELECT value FROM app_config WHERE key = ?", (key,)).fetchone()
        if row is None:
            return DEFAULT_CONFIG.get(key)
        raw = row["value"]
        try:
            return json.loads(raw)
        except Exception:
            return raw

    def set(self, key: str, value: Any) -> None:
        conn = self._db.connect()
        with conn:
            conn.execute(
                "INSERT INTO app_config(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, json.dumps(value, ensure_ascii=False)),
            )

    def get_int(self, key: str) -> int:
        value = self.get(key)
        try:
            return int(value)
        except Exception:
            return int(DEFAULT_CONFIG.get(key, 0))

    def get_bool(self, key: str) -> bool:
        value = self.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {"1", "true", "yes", "on"}
        return bool(value)

    def get_json(self, key: str) -> Any:
        return self.get(key)
