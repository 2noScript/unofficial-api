import os
import json
import uuid
import time
import logging
from datetime import datetime
from core.db import get_db_connection

logger = logging.getLogger(__name__)


def _normalize_profile_stats(profile: dict) -> dict:
    if "total_requests" not in profile:
        profile["total_requests"] = 0
    if "request_counts" not in profile or not isinstance(profile["request_counts"], dict):
        profile["request_counts"] = {}
    return profile


def _row_to_profile(row) -> dict:
    try:
        req_counts = json.loads(row["request_counts"]) if row["request_counts"] else {}
    except Exception:
        req_counts = {}

    profile = {
        "id": row["id"],
        "type": row["type"],
        "name": row["name"],
        "token": row["token"],
        "cookie": row["cookie"],
        "is_active": bool(row["is_active"]),
        "total_requests": int(row["total_requests"] or 0),
        "request_counts": req_counts,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    return _normalize_profile_stats(profile)


def create_profile(
    profile_type: str,
    name: str,
    token: str | None = None,
    cookie: str | None = None,
    is_active: bool = True
) -> dict:
    with get_db_connection() as conn:
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

        conn.execute(
            """
            INSERT INTO profiles (id, type, name, token, cookie, is_active, total_requests, request_counts, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id,
                profile_type,
                profile_entry["name"],
                profile_entry["token"],
                profile_entry["cookie"],
                1 if is_active else 0,
                0,
                json.dumps({}),
                now,
                now
            )
        )
        logger.info("Created profile: %s (%s)", profile_id, name)
        return profile_entry


def list_profiles(profile_type: str | None = None) -> list[dict]:
    """Concurrent non-blocking read of profiles."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        if profile_type:
            cur.execute("SELECT * FROM profiles WHERE type = ?", (profile_type,))
        else:
            cur.execute("SELECT * FROM profiles")
        
        return [_row_to_profile(row) for row in cur.fetchall()]


def get_profile(profile_id: str) -> dict | None:
    """Concurrent non-blocking lookup of single profile."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        row = cur.fetchone()
        if row:
            return _row_to_profile(row)
        return None


def update_profile(
    profile_id: str,
    name: str | None = None,
    token: str | None = None,
    cookie: str | None = None,
    is_active: bool | None = None
) -> dict | None:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        row = cur.fetchone()
        if not row:
            return None

        profile = _row_to_profile(row)
        ptype = profile.get("type")
        new_name = name if name is not None else profile["name"]
        new_is_active = is_active if is_active is not None else profile["is_active"]
        
        new_token = profile["token"]
        new_cookie = profile["cookie"]
        if ptype == "deepseek" and token is not None:
            new_token = token
        elif ptype == "gemini" and cookie is not None:
            new_cookie = cookie

        now = time.strftime('%Y-%m-%dT%H:%M:%S')

        conn.execute(
            """
            UPDATE profiles SET
                name = ?,
                token = ?,
                cookie = ?,
                is_active = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (new_name, new_token, new_cookie, 1 if new_is_active else 0, now, profile_id)
        )
        logger.info("Updated profile: %s", profile_id)
        return get_profile(profile_id)


def delete_profile(profile_id: str) -> bool:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM profiles WHERE id = ?", (profile_id,))
        if not cur.fetchone():
            return False

        conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        logger.info("Deleted profile: %s", profile_id)
        return True


def deactivate_profile(profile_id: str) -> dict | None:
    """Deactivate a profile (set is_active=False) when auth or runtime errors occur."""
    logger.warning("Deactivating profile '%s' due to runtime/auth error", profile_id)
    return update_profile(profile_id, is_active=False)


def record_profile_request(profile_id: str, timestamp: datetime | None = None) -> dict | None:
    """Increment request count for profile grouped by YYYY-MM-DD and HH."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,))
        row = cur.fetchone()
        if not row:
            return None

        profile = _row_to_profile(row)
        dt = timestamp if timestamp is not None else datetime.now()
        day_key = dt.strftime("%Y-%m-%d")
        hour_key = dt.strftime("%H")

        request_counts = profile.get("request_counts", {})
        if not isinstance(request_counts, dict):
            request_counts = {}

        if day_key not in request_counts:
            request_counts[day_key] = {}

        current_count = request_counts[day_key].get(hour_key, 0)
        request_counts[day_key][hour_key] = current_count + 1
        total_requests = profile.get("total_requests", 0) + 1
        now = time.strftime('%Y-%m-%dT%H:%M:%S')

        conn.execute(
            """
            UPDATE profiles SET
                total_requests = ?,
                request_counts = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (total_requests, json.dumps(request_counts), now, profile_id)
        )
        logger.debug(
            "Recorded request for profile %s (%s %s:00 total=%d count=%d)",
            profile_id, day_key, hour_key, total_requests, request_counts[day_key][hour_key]
        )
        profile["total_requests"] = total_requests

        profile["request_counts"] = request_counts
        profile["updated_at"] = now
        return profile
