import os
import json
import hmac
import hashlib
import secrets
import logging
import time
import threading
from pathlib import Path
from core.utils import safe_read_json, atomic_write_json

logger = logging.getLogger(__name__)
_keys_lock = threading.RLock()

API_KEY_PREFIX = 'sk'
API_KEY_SECRET = os.environ.get('API_KEY_SECRET', 'unofficial-api-key-secret')

def _get_data_dir() -> Path:
    return Path(os.environ.get('UNOFFICIAL_API_DATA_DIR', 'data'))

def _get_keys_file() -> Path:
    return _get_data_dir() / 'api_keys.json'

def _ensure_data_dir():
    _get_data_dir().mkdir(parents=True, exist_ok=True)

def _get_machine_id() -> str:
    _ensure_data_dir()
    mid_file = _get_data_dir() / 'machine_id'
    if mid_file.exists():
        try:
            return mid_file.read_text().strip()
        except Exception:
            pass
    
    raw = f"{secrets.token_hex(16)}-{time.time()}"
    machine_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
    try:
        mid_file.write_text(machine_id)
    except Exception:
        pass
    return machine_id

def _load_keys() -> dict:
    _ensure_data_dir()
    keys_file = _get_keys_file()
    default_data = {
        "keys": {},
        "machine_id": _get_machine_id(),
        "last_used": {}
    }
    data = safe_read_json(keys_file, default=default_data)
    if not isinstance(data, dict):
        data = default_data
    if "machine_id" not in data or not data["machine_id"]:
        data["machine_id"] = _get_machine_id()
    if "keys" not in data or not isinstance(data["keys"], dict):
        data["keys"] = {}
    if "last_used" not in data or not isinstance(data["last_used"], dict):
        data["last_used"] = {}
    return data

def _save_keys(data: dict):
    _ensure_data_dir()
    atomic_write_json(_get_keys_file(), data)

def generate_api_key(name: str = '') -> str:
    with _keys_lock:
        data = _load_keys()
        machine_id = data['machine_id']
        key_id = secrets.token_hex(3)
        raw = f"{machine_id[:8]}{key_id}"
        crc = hmac.new(API_KEY_SECRET.encode(), raw.encode(), 'sha256').hexdigest()[:8]
        api_key = f"{API_KEY_PREFIX}-{machine_id[:8]}-{key_id}-{crc}"
        
        if not name:
            name = f"Key {len(data['keys']) + 1}"
            
        created_at = time.strftime('%Y-%m-%dT%H:%M:%S')
        data['keys'][api_key] = {
            'name': name,
            'created_at': created_at,
            'is_active': True
        }
        _save_keys(data)
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

        with _keys_lock:
            data = _load_keys()
            if api_key not in data.get('keys', {}):
                logger.debug('API key not found in store')
                return False

            key_entry = data['keys'][api_key]
            if not key_entry.get('is_active', True):
                logger.debug('API key is deactivated')
                return False

            machine_id = data['machine_id']
            if len(parts) == 4:
                _, mid, key_id, crc = parts
                raw = f"{machine_id[:8]}{key_id}"
                expected_crc = hmac.new(API_KEY_SECRET.encode(), raw.encode(), 'sha256').hexdigest()[:8]
                if crc != expected_crc:
                    logger.debug('API key CRC mismatch')
                    return False
                    
            try:
                data.setdefault('last_used', {})[api_key] = time.strftime('%Y-%m-%dT%H:%M:%S')
                _save_keys(data)
            except Exception as se:
                logger.warning('Failed to save API key last_used: %s', se)
            return True
    except Exception as e:
        logger.error('API key validation error: %s', e)
        return False

def list_api_keys() -> list[dict]:
    with _keys_lock:
        data = _load_keys()
        result = []
        for key, info in data.get('keys', {}).items():
            result.append({
                'key': key,
                'name': info.get('name', ''),
                'created_at': info.get('created_at', ''),
                'is_active': info.get('is_active', True),
                'last_used': data.get('last_used', {}).get(key, '')
            })
        return result

def revoke_api_key(api_key: str) -> bool:
    with _keys_lock:
        data = _load_keys()
        if api_key not in data.get('keys', {}):
            return False
        data['keys'][api_key]['is_active'] = False
        _save_keys(data)
        return True

def get_api_key_hash(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]

