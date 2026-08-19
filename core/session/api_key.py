import os
import json
import hmac
import hashlib
import secrets
import logging
import time
import threading
from core.db import get_db_connection, get_data_dir

logger = logging.getLogger(__name__)
_mid_lock = threading.RLock()

API_KEY_PREFIX = 'sk'
API_KEY_SECRET = os.environ.get('API_KEY_SECRET', 'unofficial-api-key-secret')
_cached_machine_ids: dict[str, str] = {}


def _get_machine_id() -> str:
    db_key = str(get_data_dir().resolve())
    if db_key in _cached_machine_ids:
        return _cached_machine_ids[db_key]

    with _mid_lock:
        if db_key in _cached_machine_ids:
            return _cached_machine_ids[db_key]

        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT value FROM system_settings WHERE key = 'machine_id'")
            row = cur.fetchone()
            if row and row["value"]:
                _cached_machine_ids[db_key] = row["value"]
                return row["value"]

            # Check fallback file in data dir
            mid_file = get_data_dir() / 'machine_id'
            if mid_file.exists():
                try:
                    mid_text = mid_file.read_text().strip()
                    if mid_text:
                        conn.execute(
                            "INSERT OR REPLACE INTO system_settings (key, value) VALUES ('machine_id', ?)",
                            (mid_text,)
                        )
                        _cached_machine_ids[db_key] = mid_text
                        return mid_text
                except Exception:
                    pass

            # Generate new machine ID
            raw = f"{secrets.token_hex(16)}-{time.time()}"
            machine_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
            conn.execute(
                "INSERT OR REPLACE INTO system_settings (key, value) VALUES ('machine_id', ?)",
                (machine_id,)
            )
            try:
                mid_file.write_text(machine_id)
            except Exception:
                pass
            _cached_machine_ids[db_key] = machine_id
            return machine_id


def generate_api_key(name: str = '') -> str:
    machine_id = _get_machine_id()
    key_id = secrets.token_hex(3)
    raw = f"{machine_id[:8]}{key_id}"
    crc = hmac.new(API_KEY_SECRET.encode(), raw.encode(), 'sha256').hexdigest()[:8]
    api_key = f"{API_KEY_PREFIX}-{machine_id[:8]}-{key_id}-{crc}"

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS cnt FROM api_keys")
        count = cur.fetchone()["cnt"]

        if not name:
            name = f"Key {count + 1}"

        created_at = time.strftime('%Y-%m-%dT%H:%M:%S')
        conn.execute(
            """
            INSERT OR REPLACE INTO api_keys (key, name, is_active, created_at, last_used)
            VALUES (?, ?, ?, ?, ?)
            """,
            (api_key, name, 1, created_at, '')
        )
        logger.info("Generated API key: %s...", api_key[:20])
        return api_key


def validate_api_key(api_key: str) -> bool:
    try:
        parts = api_key.split('-')
        if len(parts) < 2:
            logger.debug('Invalid API key format (too few parts)')
            return False

        prefix = parts[0]
        if prefix != API_KEY_PREFIX:
            logger.debug('Invalid API key prefix: %s', prefix)
            return False

        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT key, name, is_active FROM api_keys WHERE key = ?", (api_key,))
            row = cur.fetchone()
            if not row:
                logger.debug('API key not found in store')
                return False

            if not row["is_active"]:
                logger.debug('API key is deactivated')
                return False

            machine_id = _get_machine_id()
            if len(parts) == 4:
                _, mid, key_id, crc = parts
                raw = f"{machine_id[:8]}{key_id}"
                expected_crc = hmac.new(API_KEY_SECRET.encode(), raw.encode(), 'sha256').hexdigest()[:8]
                if crc != expected_crc:
                    logger.debug('API key CRC mismatch')
                    return False

            try:
                now = time.strftime('%Y-%m-%dT%H:%M:%S')
                conn.execute("UPDATE api_keys SET last_used = ? WHERE key = ?", (now, api_key))
            except Exception as se:
                logger.warning('Failed to save API key last_used: %s', se)
            return True
    except Exception as e:
        logger.error('API key validation error: %s', e)
        return False


def list_api_keys() -> list[dict]:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT key, name, is_active, created_at, last_used FROM api_keys")
        result = []
        for row in cur.fetchall():
            result.append({
                'key': row['key'],
                'name': row['name'],
                'created_at': row['created_at'],
                'is_active': bool(row['is_active']),
                'last_used': row['last_used'] or ''
            })
        return result


def get_api_key(api_key: str) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT key, name, is_active, created_at, last_used FROM api_keys WHERE key = ?", (api_key,))
        row = cur.fetchone()
        if not row:
            return None
        return {
            'key': row['key'],
            'name': row['name'],
            'created_at': row['created_at'],
            'is_active': bool(row['is_active']),
            'last_used': row['last_used'] or ''
        }


def revoke_api_key(api_key: str) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT key FROM api_keys WHERE key = ?", (api_key,))
        if not cur.fetchone():
            return False
        conn.execute("UPDATE api_keys SET is_active = 0 WHERE key = ?", (api_key,))
        return True


def get_api_key_hash(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]
