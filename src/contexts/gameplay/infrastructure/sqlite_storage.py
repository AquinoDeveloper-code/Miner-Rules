from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class SQLiteStorage:
    """Persistência principal do jogo em SQLite."""

    VERSION = "2.0"

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self._create_tables()

    def _create_tables(self):
        with self.conn:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS game_state (
                    id       INTEGER PRIMARY KEY CHECK (id = 1),
                    payload  TEXT NOT NULL,
                    version  TEXT NOT NULL,
                    saved_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS save_history (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    action     TEXT NOT NULL,
                    payload    TEXT,
                    created_at REAL NOT NULL
                );
                """
            )

    def load_game_state(self) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT payload FROM game_state WHERE id = 1").fetchone()
        if not row:
            return None
        return json.loads(row["payload"])

    def save_game_state(self, data: dict[str, Any], action: str = "save") -> bool:
        payload = json.dumps(data, ensure_ascii=False)
        now = time.time()
        try:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO game_state (id, payload, version, saved_at)
                    VALUES (1, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        payload = excluded.payload,
                        version = excluded.version,
                        saved_at = excluded.saved_at
                    """,
                    (payload, self.VERSION, now),
                )
                self.conn.execute(
                    "INSERT INTO save_history (action, payload, created_at) VALUES (?, ?, ?)",
                    (action, payload, now),
                )
            return True
        except sqlite3.Error:
            return False

    def clear_game_state(self) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM game_state WHERE id = 1")
            self.conn.execute(
                "INSERT INTO save_history (action, payload, created_at) VALUES (?, ?, ?)",
                ("reset", None, time.time()),
            )

    def has_game_state(self) -> bool:
        row = self.conn.execute("SELECT 1 FROM game_state WHERE id = 1").fetchone()
        return row is not None

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
