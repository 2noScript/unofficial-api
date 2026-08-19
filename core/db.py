import os
import json
import sqlite3
import logging
import threading
from pathlib import Path
from typing import Generator
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_db_lock = threading.RLock()


def get_data_dir() -> Path:
    data_dir = Path(os.environ.get("UNOFFICIAL_API_DATA_DIR", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_db_path() -> Path:
    return get_data_dir() / "unofficial_api.db"


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections with WAL mode and row factory."""
    db_path = get_db_path()
    conn = sqlite3.connect(
        db_path,
        timeout=15.0,
        check_same_thread=False,
        isolation_level=None  # autocommit mode / explicit transaction management
    )
    conn.row_factory = sqlite3.Row
    try:
        # Configure PRAGMAs
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
    finally:
        conn.close()


def init_db():
    """Create tables and indexes if they do not exist."""
    with _db_lock, get_db_connection() as conn:
        conn.execute("BEGIN;")
        try:
            # 1. Sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL DEFAULT '{}',
                    last_used REAL NOT NULL,
                    api_key_hash TEXT,
                    created_at REAL NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_last_used ON sessions(last_used);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_api_key_hash ON sessions(api_key_hash);")

            # 2. Assistant cache table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS assistant_cache (
                    hash_key TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    last_used REAL NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_assistant_cache_last_used ON assistant_cache(last_used);")

            # 3. Profiles table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS profiles (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    token TEXT,
                    cookie TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    total_requests INTEGER NOT NULL DEFAULT 0,
                    request_counts TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_profiles_type ON profiles(type);")

            # 4. API keys table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_used TEXT NOT NULL DEFAULT ''
                );
            """)

            # 5. System settings table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
            """)

            conn.execute("COMMIT;")
            logger.info("SQLite database initialized at %s", get_db_path())
        except Exception:
            conn.execute("ROLLBACK;")
            raise
