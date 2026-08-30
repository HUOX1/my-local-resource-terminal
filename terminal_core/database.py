from __future__ import annotations

import sqlite3
from pathlib import Path


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        with self.connect() as conn:
            conn.executescript(schema_path.read_text(encoding="utf-8"))

    def table_names(self) -> set[str]:
        with self.connect() as conn:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return {str(row["name"]) for row in rows}
