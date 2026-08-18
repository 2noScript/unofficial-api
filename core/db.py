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


def auto_migrate_from_json():
    """Migrate legacy JSON files (sessions.json, profiles.json, api_keys.json, machine_id) into SQLite if DB is empty."""
    init_db()
    data_dir = get_data_dir()

    with _db_lock, get_db_connection() as conn:
        # Check if migration was already recorded
        cur = conn.cursor()
        cur.execute("SELECT value FROM system_settings WHERE key = 'migrated_from_json'")
        row = cur.fetchone()
        if row and row["value"] == "1":
            return

        conn.execute("BEGIN;")
        try:
            # 1. Migrate machine_id
            mid_file = data_dir / "machine_id"
            if mid_file.exists():
                try:
                    mid_val = mid_file.read_text().strip()
                    if mid_val:
                        conn.execute(
                            "INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)",
                            ("machine_id", mid_val)
                        )
                        logger.info("Migrated machine_id to SQLite")
                except Exception as e:
                    logger.warning("Failed to migrate machine_id: %s", e)

            # 2. Migrate api_keys.json
            keys_file = data_dir / "api_keys.json"
            if keys_file.exists():
                try:
                    with open(keys_file, "r", encoding="utf-8") as f:
                        raw_keys = json.load(f)
                    if isinstance(raw_keys, dict):
                        if "machine_id" in raw_keys and raw_keys["machine_id"]:
                            conn.execute(
                                "INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)",
                                ("machine_id", raw_keys["machine_id"])
                            )
                        keys_dict = raw_keys.get("keys", {})
                        last_used_dict = raw_keys.get("last_used", {})
                        count = 0
                        for k, info in keys_dict.items():
                            name = info.get("name", "") if isinstance(info, dict) else ""
                            is_active = 1 if info.get("is_active", True) else 0
                            created_at = info.get("created_at", "") if isinstance(info, dict) else ""
                            last_used = last_used_dict.get(k, "")
                            conn.execute(
                                """
                                INSERT OR REPLACE INTO api_keys (key, name, is_active, created_at, last_used)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (k, name, is_active, created_at, last_used)
                            )
                            count += 1
                        logger.info("Migrated %d API keys to SQLite", count)
                except Exception as e:
                    logger.warning("Failed to migrate api_keys.json: %s", e)

            # 3. Migrate profiles.json
            profiles_file = data_dir / "profiles.json"
            if profiles_file.exists():
                try:
                    with open(profiles_file, "r", encoding="utf-8") as f:
                        raw_profiles = json.load(f)
                    if isinstance(raw_profiles, dict):
                        p_dict = raw_profiles.get("profiles", {})
                        p_count = 0
                        for pid, p in p_dict.items():
                            ptype = p.get("type", "deepseek")
                            name = p.get("name", pid)
                            token = p.get("token")
                            cookie = p.get("cookie")
                            is_active = 1 if p.get("is_active", True) else 0
                            total_requests = int(p.get("total_requests", 0))
                            request_counts = json.dumps(p.get("request_counts", {}))
                            created_at = p.get("created_at", "")
                            updated_at = p.get("updated_at", "")
                            conn.execute(
                                """
                                INSERT OR REPLACE INTO profiles 
                                (id, type, name, token, cookie, is_active, total_requests, request_counts, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (pid, ptype, name, token, cookie, is_active, total_requests, request_counts, created_at, updated_at)
                            )
                            p_count += 1
                        logger.info("Migrated %d profiles to SQLite", p_count)
                except Exception as e:
                    logger.warning("Failed to migrate profiles.json: %s", e)

            # 4. Migrate sessions.json
            sessions_file = data_dir / "sessions.json"
            if sessions_file.exists():
                try:
                    with open(sessions_file, "r", encoding="utf-8") as f:
                        raw_sessions = json.load(f)
                    if isinstance(raw_sessions, dict):
                        s_dict = raw_sessions.get("sessions", {})
                        s_count = 0
                        for vid, rec in s_dict.items():
                            data_json = json.dumps(rec.get("data", {}))
                            last_used = float(rec.get("last_used", 0))
                            api_key_hash = rec.get("api_key_hash")
                            created_at = last_used
                            conn.execute(
                                """
                                INSERT OR REPLACE INTO sessions (session_id, data, last_used, api_key_hash, created_at)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (vid, data_json, last_used, api_key_hash, created_at)
                            )
                            s_count += 1

                        ac_dict = raw_sessions.get("assistant_cache", {})
                        ac_count = 0
                        for h, vid in ac_dict.items():
                            if vid in s_dict:
                                conn.execute(
                                    """
                                    INSERT OR REPLACE INTO assistant_cache (hash_key, session_id, last_used)
                                    VALUES (?, ?, ?)
                                    """,
                                    (h, vid, float(s_dict[vid].get("last_used", 0)))
                                )
                                ac_count += 1
                        logger.info("Migrated %d sessions and %d assistant cache entries to SQLite", s_count, ac_count)
                except Exception as e:
                    logger.warning("Failed to migrate sessions.json: %s", e)

            # Mark migration as complete
            conn.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('migrated_from_json', '1')")
            conn.execute("COMMIT;")
            logger.info("Auto-migration from JSON to SQLite completed successfully.")
        except Exception as e:
            conn.execute("ROLLBACK;")
            logger.error("Auto-migration failed: %s", e)
