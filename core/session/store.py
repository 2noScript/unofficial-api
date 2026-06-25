import time
import threading
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

MAX_SESSIONS = 1000
MAX_ASSISTANT = 5000
TTL_MS = 7200000
TTL_S = TTL_MS / 1000
CLEANUP_INTERVAL_S = 1800

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
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()

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
        now = time.time()
        with self._lock:
            expired = []
            for vid, rec in self._sessions.items():
                if (now - rec.last_used) * 1000 > TTL_MS:
                    expired.append(vid)
                    
            for vid in expired:
                del self._sessions[vid]
                
            assistant_expired = []
            for h, vid in self._assistant_cache.items():
                if vid not in self._sessions:
                    assistant_expired.append(h)
                    
            for h in assistant_expired:
                del self._assistant_cache[h]
                
            if expired or assistant_expired:
                logger.debug(f'Expired {len(expired)} sessions, {len(assistant_expired)} assistant cache entries')

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
