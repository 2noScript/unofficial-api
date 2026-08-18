import os
import json
import time
import threading
import logging
from dataclasses import dataclass
from core.db import get_db_connection, init_db

logger = logging.getLogger(__name__)

# --- Configurable via env vars ---
_ttl_days = float(os.environ.get('SESSION_TTL_DAYS', '7'))  # 0 = never expire
MAX_SESSIONS = int(os.environ.get('SESSION_MAX_SESSIONS', '5000'))
MAX_ASSISTANT = 10000
TTL_S = _ttl_days * 86400 if _ttl_days > 0 else float('inf')
TTL_MS = TTL_S * 1000 if _ttl_days > 0 else float('inf')
CLEANUP_INTERVAL_S = 3600  # every hour


@dataclass
class SessionRecord:
    session_id: str
    data: dict
    last_used: float
    api_key_hash: str | None = None


class VirtualSessionStore:
    def __init__(self):
        init_db()
        self._lock = threading.RLock()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    # ── public API ────────────────────────────────────────────────────────────

    def get_or_create(self, vid: str, api_key_hash: str | None = None) -> SessionRecord:
        with self._lock, get_db_connection() as conn:
            now = time.time()
            cur = conn.cursor()
            cur.execute(
                "SELECT session_id, data, last_used, api_key_hash FROM sessions WHERE session_id = ?",
                (vid,)
            )
            row = cur.fetchone()
            if row:
                try:
                    data = json.loads(row["data"]) if row["data"] else {}
                except Exception:
                    data = {}
                # Update last_used
                conn.execute("UPDATE sessions SET last_used = ? WHERE session_id = ?", (now, vid))
                return SessionRecord(
                    session_id=vid,
                    data=data,
                    last_used=now,
                    api_key_hash=row["api_key_hash"] or api_key_hash
                )

            # Not found -> create new
            rec = SessionRecord(
                session_id=vid,
                data={},
                last_used=now,
                api_key_hash=api_key_hash
            )
            conn.execute(
                """
                INSERT INTO sessions (session_id, data, last_used, api_key_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (vid, json.dumps({}), now, api_key_hash, now)
            )
            self._evict_lru()
            return rec

    def get(self, vid: str) -> SessionRecord | None:
        with self._lock, get_db_connection() as conn:
            now = time.time()
            cur = conn.cursor()
            cur.execute(
                "SELECT session_id, data, last_used, api_key_hash FROM sessions WHERE session_id = ?",
                (vid,)
            )
            row = cur.fetchone()
            if not row:
                return None
            try:
                data = json.loads(row["data"]) if row["data"] else {}
            except Exception:
                data = {}
            conn.execute("UPDATE sessions SET last_used = ? WHERE session_id = ?", (now, vid))
            return SessionRecord(
                session_id=vid,
                data=data,
                last_used=now,
                api_key_hash=row["api_key_hash"]
            )

    def save(self, record: SessionRecord):
        """Save a SessionRecord directly to SQLite."""
        self.save_data(record.session_id, record.data, api_key_hash=record.api_key_hash)

    def save_data(self, vid: str, data: dict, api_key_hash: str | None = None):
        """Persist session data dictionary to SQLite."""
        with self._lock, get_db_connection() as conn:
            now = time.time()
            data_json = json.dumps(data, ensure_ascii=False)
            if api_key_hash is not None:
                conn.execute(
                    """
                    INSERT INTO sessions (session_id, data, last_used, api_key_hash, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        data = excluded.data,
                        last_used = excluded.last_used,
                        api_key_hash = COALESCE(excluded.api_key_hash, sessions.api_key_hash)
                    """,
                    (vid, data_json, now, api_key_hash, now)
                )
            else:
                conn.execute(
                    """
                    INSERT INTO sessions (session_id, data, last_used, api_key_hash, created_at)
                    VALUES (?, ?, ?, NULL, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        data = excluded.data,
                        last_used = excluded.last_used
                    """,
                    (vid, data_json, now, now)
                )

    def update(self, vid: str, **fields):
        with self._lock, get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT data, api_key_hash FROM sessions WHERE session_id = ?", (vid,))
            row = cur.fetchone()
            if not row:
                return
            try:
                data = json.loads(row["data"]) if row["data"] else {}
            except Exception:
                data = {}
            data.update(fields)
            now = time.time()
            conn.execute(
                "UPDATE sessions SET data = ?, last_used = ? WHERE session_id = ?",
                (json.dumps(data, ensure_ascii=False), now, vid)
            )

    def set_assistant(self, hash_key: str, vid: str):
        with self._lock, get_db_connection() as conn:
            now = time.time()
            conn.execute(
                """
                INSERT INTO assistant_cache (hash_key, session_id, last_used)
                VALUES (?, ?, ?)
                ON CONFLICT(hash_key) DO UPDATE SET
                    session_id = excluded.session_id,
                    last_used = excluded.last_used
                """,
                (hash_key, vid, now)
            )
            # Evict LRU from assistant_cache if over cap
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS cnt FROM assistant_cache")
            count = cur.fetchone()["cnt"]
            if count > MAX_ASSISTANT:
                excess = count - MAX_ASSISTANT
                conn.execute(
                    """
                    DELETE FROM assistant_cache WHERE hash_key IN (
                        SELECT hash_key FROM assistant_cache ORDER BY last_used ASC LIMIT ?
                    )
                    """,
                    (excess,)
                )

    def get_assistant(self, hash_key: str) -> str | None:
        with self._lock, get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT session_id FROM assistant_cache WHERE hash_key = ?", (hash_key,))
            row = cur.fetchone()
            if row:
                now = time.time()
                conn.execute("UPDATE assistant_cache SET last_used = ? WHERE hash_key = ?", (now, hash_key))
                return row["session_id"]
            return None

    def get_sessions_by_api_key(self, api_key_hash: str) -> list[SessionRecord]:
        with self._lock, get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT session_id, data, last_used, api_key_hash FROM sessions WHERE api_key_hash = ?",
                (api_key_hash,)
            )
            results = []
            for row in cur.fetchall():
                try:
                    data = json.loads(row["data"]) if row["data"] else {}
                except Exception:
                    data = {}
                results.append(SessionRecord(
                    session_id=row["session_id"],
                    data=data,
                    last_used=row["last_used"],
                    api_key_hash=row["api_key_hash"]
                ))
            return results

    def delete_expired(self):
        if TTL_S == float('inf'):
            return  # never expire mode
        now = time.time()
        with self._lock, get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM sessions WHERE (? - last_used) > ?",
                (now, TTL_S)
            )
            expired_count = cur.fetchone()["cnt"]
            if expired_count > 0:
                conn.execute("DELETE FROM sessions WHERE (? - last_used) > ?", (now, TTL_S))
                # clean dangling assistant_cache entries
                conn.execute("""
                    DELETE FROM assistant_cache WHERE session_id NOT IN (SELECT session_id FROM sessions)
                """)
                logger.debug('Expired %d sessions from SQLite', expired_count)

    # ── internals ─────────────────────────────────────────────────────────────

    def _evict_lru(self):
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS cnt FROM sessions")
            count = cur.fetchone()["cnt"]
            if count > MAX_SESSIONS:
                excess = count - MAX_SESSIONS
                conn.execute(
                    """
                    DELETE FROM sessions WHERE session_id IN (
                        SELECT session_id FROM sessions ORDER BY last_used ASC LIMIT ?
                    )
                    """,
                    (excess,)
                )

    def _cleanup_loop(self):
        while True:
            time.sleep(CLEANUP_INTERVAL_S)
            try:
                self.delete_expired()
            except Exception as e:
                logger.warning('Session cleanup error: %s', e)
