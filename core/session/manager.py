import time
import uuid
import logging
import threading

logger = logging.getLogger(__name__)

RESERVED_HEADERS = ['x-session-id']

def _normalize_session_id(value) -> str | None:
    if not isinstance(value, str):
        return None
    v = value.strip()
    if not v or len(v) > 256:
        return None
    return v

def _extract_header(headers: dict, key: str) -> str | None:
    val = headers.get(key)
    if not val:
        val = headers.get(key.lower())
    return _normalize_session_id(val)

class VirtualSessionManager:
    def __init__(self, store):
        self.store = store
        self._runtime_sessions = {}  # key (seed/connectionId) -> (session_id, last_used)
        self._lock = threading.Lock()

    def resolve(self, headers: dict, body: dict, provider: str, api_key_hash: str | None = None, fingerprint: str | None = None) -> str:
        for key in RESERVED_HEADERS:
            val = _extract_header(headers, key)
            if val:
                logger.debug('Session from header %s: %s', key, val[:20])
                return val

        vid = self._generate_vid()
        logger.debug('No session header, fresh session: %s', vid[:20])
        return vid

    def _derive_session_id(self, seed: str) -> str:
        if not seed:
            return self._generate_vid()
            
        with self._lock:
            now = time.time()
            if seed in self._runtime_sessions:
                # Move to end to mark as recently used (LRU)
                vid, _ = self._runtime_sessions.pop(seed)
                self._runtime_sessions[seed] = (vid, now)
                return vid
                
            # Evict oldest entry if runtime sessions exceed safety cap (matches 9router's cap of 1000)
            if len(self._runtime_sessions) >= 1000:
                oldest = next(iter(self._runtime_sessions))
                self._runtime_sessions.pop(oldest, None)
                
            vid = self._generate_vid()
            self._runtime_sessions[seed] = (vid, now)
            return vid

    def _generate_vid(self) -> str:
        return f"{uuid.uuid4().hex}{int(time.time() * 1000)}"
