import sqlite3
from pathlib import Path
from typing import Any


class DatabaseManager:
    """Handles SQLite database connection and SQL execution."""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            db_path = str(Path(__file__).parent / "procurement.db")
        self.db_path = db_path
        self._connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        """Establish database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    def close(self) -> None:
        """Close database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """Execute a SQL query with parameters."""
        conn = self.connect()
        cursor = conn.execute(query, params)
        return cursor

    def execute_many(self, query: str, params_list: list[tuple[Any, ...]]) -> sqlite3.Cursor:
        """Execute a SQL query with multiple parameter sets."""
        conn = self.connect()
        cursor = conn.executemany(query, params_list)
        return cursor

    def commit(self) -> None:
        """Commit the current transaction."""
        if self._connection is not None:
            self._connection.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._connection is not None:
            self._connection.rollback()

    def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        """Execute query and fetch one result."""
        cursor = self.execute(query, params)
        return cursor.fetchone()

    def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        """Execute query and fetch all results."""
        cursor = self.execute(query, params)
        return cursor.fetchall()

    def initialize_schema(self) -> None:
        """Create database tables if they don't exist."""
        self.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requestor_name TEXT NOT NULL,
                title TEXT NOT NULL,
                vendor_name TEXT NOT NULL,
                vat_id TEXT NOT NULL,
                requestor_department TEXT NOT NULL,
                commodity_group INTEGER NOT NULL,
                total_cost REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.execute("""
            CREATE TABLE IF NOT EXISTS order_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                position_description TEXT NOT NULL,
                unit TEXT NOT NULL,
                unit_price REAL NOT NULL,
                amount REAL NOT NULL,
                total_price REAL NOT NULL,
                FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
            )
        """)

        # Migration: Add status column if it doesn't exist (for existing databases)
        try:
            self.execute("ALTER TABLE requests ADD COLUMN status TEXT NOT NULL DEFAULT 'Open'")
        except sqlite3.OperationalError:
            pass  # Column already exists

        self.commit()
