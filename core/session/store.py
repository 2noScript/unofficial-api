import os
import json
import time
import threading
import logging
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# --- Configurable via env vars ---
_ttl_days = float(os.environ.get('SESSION_TTL_DAYS', '7'))  # 0 = never expire
MAX_SESSIONS = int(os.environ.get('SESSION_MAX_SESSIONS', '5000'))
MAX_ASSISTANT = 10000
TTL_S = _ttl_days * 86400 if _ttl_days > 0 else float('inf')
TTL_MS = TTL_S * 1000 if _ttl_days > 0 else float('inf')
CLEANUP_INTERVAL_S = 3600  # every hour

DATA_DIR = Path(os.environ.get('UNOFFICIAL_API_DATA_DIR', Path.home() / '.unofficial-api'))
SESSIONS_FILE = DATA_DIR / 'sessions.json'


@dataclass
class SessionRecord:
    session_id: str
    data: dict
    last_used: float
    api_key_hash: str | None = None


class VirtualSessionStore:
    def __init__(self):
        self._sessions = {}
        self._assistant_cache = {}
        self._lock = threading.Lock()
        self._load_from_disk()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

    # ── persistence ──────────────────────────────────────────────────────────

    def _load_from_disk(self):
        """Load sessions from disk, discarding any that have already expired."""
        try:
            if not SESSIONS_FILE.exists():
                return
            raw = json.loads(SESSIONS_FILE.read_text())
            now = time.time()
            loaded = 0
            for vid, rec in raw.get('sessions', {}).items():
                last_used = rec.get('last_used', 0)
                if TTL_S != float('inf') and (now - last_used) > TTL_S:
                    continue  # expired — skip
                self._sessions[vid] = SessionRecord(
                    session_id=vid,
                    data=rec.get('data', {}),
                    last_used=last_used,
                    api_key_hash=rec.get('api_key_hash'),
                )
                loaded += 1
            # only keep assistant_cache entries whose vid survived the TTL filter
            self._assistant_cache = {
                k: v for k, v in raw.get('assistant_cache', {}).items()
                if v in self._sessions
            }
            logger.info('Loaded %d sessions from disk (%s), TTL=%.1f days', loaded, SESSIONS_FILE, _ttl_days if _ttl_days > 0 else float('inf'))
        except Exception as e:
            logger.warning('Failed to load sessions from disk: %s', e)

    def _save_to_disk(self):
        """Persist current (already-cleaned) in-memory state to disk."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with self._lock:
                payload = {
                    'sessions': {
                        vid: {
                            'data': rec.data,
                            'last_used': rec.last_used,
                            'api_key_hash': rec.api_key_hash,
                        }
                        for vid, rec in self._sessions.items()
                    },
                    'assistant_cache': dict(self._assistant_cache),
                }
            SESSIONS_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.warning('Failed to save sessions to disk: %s', e)

    # ── public API ────────────────────────────────────────────────────────────

    def get_or_create(self, vid: str, api_key_hash: str | None = None) -> SessionRecord:
        with self._lock:
            if vid in self._sessions:
                rec = self._sessions[vid]
                rec.last_used = time.time()
                return rec

            rec = SessionRecord(
                session_id=vid,
                data={},
                last_used=time.time(),
                api_key_hash=api_key_hash
            )
            self._evict_lru()
            self._sessions[vid] = rec
            return rec

    def update(self, vid: str, **fields):
        with self._lock:
            rec = self._sessions.get(vid)
            if not rec:
                return
            rec.last_used = time.time()
            rec.data.update(fields)
        self._save_to_disk()

    def get(self, vid: str) -> SessionRecord | None:
        with self._lock:
            rec = self._sessions.get(vid)
            if rec:
                rec.last_used = time.time()
            return rec

    def set_assistant(self, hash_key: str, vid: str):
        with self._lock:
            if len(self._assistant_cache) >= MAX_ASSISTANT:
                oldest = next(iter(self._assistant_cache))
                del self._assistant_cache[oldest]
            self._assistant_cache[hash_key] = vid

    def get_assistant(self, hash_key: str) -> str | None:
        with self._lock:
            return self._assistant_cache.get(hash_key)

    def get_sessions_by_api_key(self, api_key_hash: str) -> list[SessionRecord]:
        with self._lock:
            return [rec for rec in self._sessions.values() if rec.api_key_hash == api_key_hash]

    def delete_expired(self):
        if TTL_S == float('inf'):
            return  # never expire mode
        now = time.time()
        with self._lock:
            expired = [
                vid for vid, rec in self._sessions.items()
                if (now - rec.last_used) > TTL_S
            ]
            for vid in expired:
                del self._sessions[vid]

            assistant_expired = [
                h for h, vid in self._assistant_cache.items()
                if vid not in self._sessions
            ]
            for h in assistant_expired:
                del self._assistant_cache[h]

            if expired or assistant_expired:
                logger.debug('Expired %d sessions, %d assistant cache entries', len(expired), len(assistant_expired))

        if expired or assistant_expired:
            self._save_to_disk()

    # ── internals ─────────────────────────────────────────────────────────────

    def _evict_lru(self):
        if len(self._sessions) < MAX_SESSIONS:
            return
        oldest = min(self._sessions.items(), key=lambda x: x[1].last_used)
        del self._sessions[oldest[0]]

    def _cleanup_loop(self):
        while True:
            time.sleep(CLEANUP_INTERVAL_S)
            try:
                self.delete_expired()
            except Exception as e:
                logger.warning('Session cleanup error: %s', e)
