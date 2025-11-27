"""
SQLite database management for llm_supercli.
Handles database initialization, migrations, and core operations.
"""
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Optional

from ..constants import HISTORY_DB, CONFIG_DIR


SCHEMA_VERSION = 1

SCHEMA = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_info (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Chat sessions
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    provider TEXT,
    model TEXT,
    system_prompt TEXT,
    created_at REAL,
    updated_at REAL,
    message_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost REAL DEFAULT 0.0,
    is_favorite INTEGER DEFAULT 0,
    metadata TEXT
);

-- Chat messages
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp REAL NOT NULL,
    tokens INTEGER DEFAULT 0,
    cost REAL DEFAULT 0.0,
    metadata TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Favorites (starred sessions/messages)
CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    reference_id TEXT NOT NULL,
    title TEXT,
    notes TEXT,
    created_at REAL,
    tags TEXT
);

-- Usage statistics
CREATE TABLE IF NOT EXISTS usage_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_cost REAL DEFAULT 0.0,
    request_count INTEGER DEFAULT 0
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at);
CREATE INDEX IF NOT EXISTS idx_sessions_favorite ON sessions(is_favorite);
CREATE INDEX IF NOT EXISTS idx_usage_date ON usage_stats(date);
CREATE INDEX IF NOT EXISTS idx_favorites_type ON favorites(type);
"""


class Database:
    """
    SQLite database wrapper with connection pooling and thread safety.
    
    Uses a connection per thread to ensure thread safety.
    """
    
    _instance: Optional['Database'] = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: Optional[Path] = None) -> 'Database':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: Optional[Path] = None) -> None:
        if self._initialized:
            return
            
        self._db_path = db_path or HISTORY_DB
        self._local = threading.local()
        self._ensure_directory()
        self._initialize_schema()
        self._initialized = True
    
    def _ensure_directory(self) -> None:
        """Ensure database directory exists."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            self._local.connection.row_factory = sqlite3.Row
            self._local.connection.execute("PRAGMA foreign_keys = ON")
            self._local.connection.execute("PRAGMA journal_mode = WAL")
        return self._local.connection
    
    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connection."""
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
    
    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database transaction."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _initialize_schema(self) -> None:
        """Initialize database schema."""
        with self.transaction() as conn:
            conn.executescript(SCHEMA)
            
            cursor = conn.execute(
                "SELECT value FROM schema_info WHERE key = 'version'"
            )
            row = cursor.fetchone()
            
            if row is None:
                conn.execute(
                    "INSERT INTO schema_info (key, value) VALUES (?, ?)",
                    ("version", str(SCHEMA_VERSION))
                )
            else:
                current_version = int(row[0])
                if current_version < SCHEMA_VERSION:
                    self._migrate(conn, current_version)
    
    def _migrate(self, conn: sqlite3.Connection, from_version: int) -> None:
        """
        Run database migrations.
        
        Args:
            conn: Database connection
            from_version: Current schema version
        """
        # Future migrations go here
        conn.execute(
            "UPDATE schema_info SET value = ? WHERE key = 'version'",
            (str(SCHEMA_VERSION),)
        )
    
    def execute(
        self,
        query: str,
        params: tuple = (),
        commit: bool = True
    ) -> sqlite3.Cursor:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters
            commit: Whether to commit transaction
            
        Returns:
            Cursor with results
        """
        conn = self._get_connection()
        cursor = conn.execute(query, params)
        if commit:
            conn.commit()
        return cursor
    
    def execute_many(
        self,
        query: str,
        params_list: list[tuple],
        commit: bool = True
    ) -> sqlite3.Cursor:
        """
        Execute a SQL query with multiple parameter sets.
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
            commit: Whether to commit transaction
            
        Returns:
            Cursor with results
        """
        conn = self._get_connection()
        cursor = conn.executemany(query, params_list)
        if commit:
            conn.commit()
        return cursor
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """
        Fetch a single row.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Row or None
        """
        cursor = self.execute(query, params, commit=False)
        return cursor.fetchone()
    
    def fetch_all(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        """
        Fetch all rows.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of rows
        """
        cursor = self.execute(query, params, commit=False)
        return cursor.fetchall()
    
    def insert(self, table: str, data: dict) -> int:
        """
        Insert a row into a table.
        
        Args:
            table: Table name
            data: Column-value dictionary
            
        Returns:
            Inserted row ID
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        cursor = self.execute(query, tuple(data.values()))
        return cursor.lastrowid
    
    def update(
        self,
        table: str,
        data: dict,
        where: str,
        where_params: tuple = ()
    ) -> int:
        """
        Update rows in a table.
        
        Args:
            table: Table name
            data: Column-value dictionary
            where: WHERE clause
            where_params: WHERE parameters
            
        Returns:
            Number of affected rows
        """
        set_clause = ", ".join(f"{k} = ?" for k in data.keys())
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        params = tuple(data.values()) + where_params
        cursor = self.execute(query, params)
        return cursor.rowcount
    
    def delete(self, table: str, where: str, where_params: tuple = ()) -> int:
        """
        Delete rows from a table.
        
        Args:
            table: Table name
            where: WHERE clause
            where_params: WHERE parameters
            
        Returns:
            Number of deleted rows
        """
        query = f"DELETE FROM {table} WHERE {where}"
        cursor = self.execute(query, where_params)
        return cursor.rowcount
    
    def close(self) -> None:
        """Close the thread-local connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
    
    def vacuum(self) -> None:
        """Optimize database storage."""
        self.execute("VACUUM")
    
    def get_stats(self) -> dict:
        """
        Get database statistics.
        
        Returns:
            Dict with database stats
        """
        stats = {}
        
        row = self.fetch_one("SELECT COUNT(*) as count FROM sessions")
        stats['sessions'] = row['count'] if row else 0
        
        row = self.fetch_one("SELECT COUNT(*) as count FROM messages")
        stats['messages'] = row['count'] if row else 0
        
        row = self.fetch_one("SELECT COUNT(*) as count FROM favorites")
        stats['favorites'] = row['count'] if row else 0
        
        row = self.fetch_one(
            "SELECT SUM(total_tokens) as tokens, SUM(total_cost) as cost FROM sessions"
        )
        stats['total_tokens'] = row['tokens'] or 0 if row else 0
        stats['total_cost'] = row['cost'] or 0.0 if row else 0.0
        
        stats['db_size'] = self._db_path.stat().st_size if self._db_path.exists() else 0
        
        return stats


_database: Optional[Database] = None


def get_database() -> Database:
    """Get the global database instance."""
    global _database
    if _database is None:
        _database = Database()
    return _database
