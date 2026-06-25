import hashlib
import time
import uuid
import logging
import threading

logger = logging.getLogger(__name__)

RESERVED_HEADERS = ['x-session-id', 'session-id', 'session_id', 'x-client-request-id', 'x-conversation-id']
BODY_FIELDS = ['session_id', 'conversation_id', 'prompt_cache_key']
ASSISTANT_MIN_LEN = 50
ASSISTANT_CAP_LEN = 50

def _sha16(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]

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

def _accumulate_assistant_text(body: dict) -> str:
    items = body.get('input') or body.get('messages') or []
    text = ''
    for msg in items:
        if not isinstance(msg, dict):
            continue
        if msg.get('role') != 'assistant':
            continue
        content = msg.get('content', '')
        if isinstance(content, str):
            text += content
        elif isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                text += part.get('text', '') or part.get('output', '')
        if len(text) >= ASSISTANT_CAP_LEN:
            break
    return text[:ASSISTANT_CAP_LEN]

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
                
        for key in BODY_FIELDS:
            val = _normalize_session_id(body.get(key))
            if val:
                logger.debug('Session from body %s: %s', key, val[:20])
                return val
                
        text = _accumulate_assistant_text(body)
        if len(text) >= ASSISTANT_MIN_LEN:
            hash_key = _sha16(f"{provider}:{text}")
            cached = self.store.get_assistant(hash_key)
            if cached:
                logger.debug('Session from assistant hash (cached): %s', cached[:20])
                return cached
            vid = self._generate_vid()
            self.store.set_assistant(hash_key, vid)
            logger.debug('Session from assistant hash (new): %s', vid[:20])
            return vid
            
        if api_key_hash:
            vid = self._derive_session_id(api_key_hash)
            logger.debug('Session from api_key: %s', vid[:20])
            return vid
            
        vid = self._derive_session_id(fingerprint if fingerprint else 'unknown')
        logger.debug('Session from fingerprint: %s', vid[:20])
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
