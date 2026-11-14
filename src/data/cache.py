"""Persistent caching layer using SQLite for external NASA and SoilGrids data."""

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional


class EnvironmentalDataCache:
    """Thread-safe SQLite cache with TTL expiration for environmental queries."""

    def __init__(self, db_path: str = "data/processed/cache.sqlite", ttl_days: int = 30):
        self.db_path = Path(db_path)
        self.ttl_days = ttl_days
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_cache (
                    cache_key TEXT PRIMARY KEY,
                    service_name TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cache_expires ON api_cache (expires_at)"
            )
            conn.commit()

    def get(self, cache_key: str) -> Optional[dict[str, Any]]:
        """Retrieve unexpired cached data."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT payload FROM api_cache WHERE cache_key = ? AND expires_at > ?",
                (cache_key, now),
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row["payload"])
        return None

    def set(self, cache_key: str, service_name: str, data: dict[str, Any]) -> None:
        """Store payload with TTL."""
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(days=self.ttl_days)).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO api_cache (cache_key, service_name, payload, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (cache_key, service_name, json.dumps(data), now.isoformat(), expires_at),
            )
            conn.commit()

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM api_cache")
            conn.commit()
