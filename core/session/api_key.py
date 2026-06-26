import os
import json
import hmac
import hashlib
import secrets
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

API_KEY_PREFIX = 'ua'
API_KEY_SECRET = os.environ.get('API_KEY_SECRET', 'unofficial-api-key-secret')
DATA_DIR = Path(os.environ.get('UNOFFICIAL_API_DATA_DIR', Path.home() / '.unofficial-api'))
KEYS_FILE = DATA_DIR / 'api_keys.json'

def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def _get_machine_id() -> str:
    _ensure_data_dir()
    mid_file = DATA_DIR / 'machine_id'
    if mid_file.exists():
        return mid_file.read_text().strip()
    
    raw = f"{secrets.token_hex(16)}-{time.time()}"
    machine_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
    mid_file.write_text(machine_id)
    return machine_id

def _load_keys() -> dict:
    _ensure_data_dir()
    if KEYS_FILE.exists():
        try:
            return json.loads(KEYS_FILE.read_text())
        except Exception:
            pass
    return {
        "keys": {},
        "machine_id": _get_machine_id(),
        "last_used": {}
    }

def _save_keys(data: dict):
    _ensure_data_dir()
    KEYS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def generate_api_key(name: str = '') -> str:
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
                
        data.setdefault('last_used', {})[api_key] = time.strftime('%Y-%m-%dT%H:%M:%S')
        _save_keys(data)
        return True
    except Exception as e:
        logger.error('API key validation error: %s', e)
        return False

def list_api_keys() -> list[dict]:
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
    data = _load_keys()
    if api_key not in data.get('keys', {}):
        return False
    data['keys'][api_key]['is_active'] = False
    _save_keys(data)
    return True

def get_api_key_hash(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]
