import os
import json
import uuid
import time
import logging
import threading
from datetime import datetime
from pathlib import Path

from core.utils import safe_read_json, atomic_write_json

logger = logging.getLogger(__name__)

_profiles_lock = threading.RLock()

def _get_data_dir() -> Path:
    return Path(os.environ.get('UNOFFICIAL_API_DATA_DIR', 'data'))

def _get_profiles_file() -> Path:
    return _get_data_dir() / 'profiles.json'


def _ensure_data_dir():
    _get_data_dir().mkdir(parents=True, exist_ok=True)


def _load_profiles_data() -> dict:
    _ensure_data_dir()
    profiles_file = _get_profiles_file()
    data = safe_read_json(profiles_file, default={"profiles": {}})
    if not isinstance(data, dict) or "profiles" not in data:
        return {"profiles": {}}
    return data


def _save_profiles_data(data: dict):
    _ensure_data_dir()
    profiles_file = _get_profiles_file()
    atomic_write_json(profiles_file, data)


def _normalize_profile_stats(profile: dict) -> dict:
    if "total_requests" not in profile:
        profile["total_requests"] = 0
    if "request_counts" not in profile or not isinstance(profile["request_counts"], dict):
        profile["request_counts"] = {}
    return profile


def create_profile(
    profile_type: str,
    name: str,
    token: str | None = None,
    cookie: str | None = None,
    is_active: bool = True
) -> dict:
    with _profiles_lock:
        data = _load_profiles_data()
        profile_id = f"prof_{profile_type}_{uuid.uuid4().hex[:8]}"
        now = time.strftime('%Y-%m-%dT%H:%M:%S')

        profile_entry = {
            "id": profile_id,
            "type": profile_type,
            "name": name or f"{profile_type.capitalize()} Profile",
            "token": token if profile_type == "deepseek" else None,
            "cookie": cookie if profile_type == "gemini" else None,
            "is_active": is_active,
            "total_requests": 0,
            "request_counts": {},
            "created_at": now,
            "updated_at": now
        }

        data["profiles"][profile_id] = profile_entry
        _save_profiles_data(data)
        logger.info("Created profile: %s (%s)", profile_id, name)
        return profile_entry


def list_profiles(profile_type: str | None = None) -> list[dict]:
    with _profiles_lock:
        data = _load_profiles_data()
        result = []
        for pid, profile in data.get("profiles", {}).items():
            if profile_type and profile.get("type") != profile_type:
                continue
            result.append(_normalize_profile_stats(profile))
        return result


def get_profile(profile_id: str) -> dict | None:
    with _profiles_lock:
        data = _load_profiles_data()
        profile = data.get("profiles", {}).get(profile_id)
        if profile:
            return _normalize_profile_stats(profile)
        return None


def update_profile(
    profile_id: str,
    name: str | None = None,
    token: str | None = None,
    cookie: str | None = None,
    is_active: bool | None = None
) -> dict | None:
    with _profiles_lock:
        data = _load_profiles_data()
        if profile_id not in data.get("profiles", {}):
            return None

        profile = data["profiles"][profile_id]
        ptype = profile.get("type")

        if name is not None:
            profile["name"] = name
        if is_active is not None:
            profile["is_active"] = is_active

        if ptype == "deepseek" and token is not None:
            profile["token"] = token
        elif ptype == "gemini" and cookie is not None:
            profile["cookie"] = cookie

        profile["updated_at"] = time.strftime('%Y-%m-%dT%H:%M:%S')
        data["profiles"][profile_id] = profile
        _save_profiles_data(data)
        logger.info("Updated profile: %s", profile_id)
        return _normalize_profile_stats(profile)


def delete_profile(profile_id: str) -> bool:
    with _profiles_lock:
        data = _load_profiles_data()
        if profile_id not in data.get("profiles", {}):
            return False

        del data["profiles"][profile_id]
        _save_profiles_data(data)
        logger.info("Deleted profile: %s", profile_id)
        return True


def deactivate_profile(profile_id: str) -> dict | None:
    """Deactivate a profile (set is_active=False) when auth or runtime errors occur."""
    logger.warning("Deactivating profile '%s' due to runtime/auth error", profile_id)
    return update_profile(profile_id, is_active=False)


def record_profile_request(profile_id: str, timestamp: datetime | None = None) -> dict | None:
    """Increment request count for profile grouped by YYYY-MM-DD and HH."""
    with _profiles_lock:
        data = _load_profiles_data()
        if profile_id not in data.get("profiles", {}):
            return None

        profile = data["profiles"][profile_id]
        dt = timestamp if timestamp is not None else datetime.now()

        day_key = dt.strftime("%Y-%m-%d")
        hour_key = dt.strftime("%H")

        if "request_counts" not in profile or not isinstance(profile["request_counts"], dict):
            profile["request_counts"] = {}

        if day_key not in profile["request_counts"]:
            profile["request_counts"][day_key] = {}

        current_count = profile["request_counts"][day_key].get(hour_key, 0)
        profile["request_counts"][day_key][hour_key] = current_count + 1
        profile["total_requests"] = profile.get("total_requests", 0) + 1

        profile["updated_at"] = time.strftime('%Y-%m-%dT%H:%M:%S')
        data["profiles"][profile_id] = profile
        _save_profiles_data(data)
        logger.info(
            "Recorded request for profile %s (%s %s:00 total=%d count=%d)",
            profile_id, day_key, hour_key, profile["total_requests"], profile["request_counts"][day_key][hour_key]
        )
        return _normalize_profile_stats(profile)


