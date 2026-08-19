import os
import json
import time
import tempfile
from pathlib import Path
import pytest

from core.db import init_db, get_db_connection, get_db_path

from core.session.store import VirtualSessionStore, SessionRecord
from core.profile import (
    create_profile,
    list_profiles,
    get_profile,
    update_profile,
    delete_profile,
    record_profile_request,
    deactivate_profile,
)
from core.session.api_key import (
    generate_api_key,
    validate_api_key,
    list_api_keys,
    revoke_api_key,
    _get_machine_id,
)


@pytest.fixture(autouse=True)
def temp_data_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("UNOFFICIAL_API_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SESSION_TTL_DAYS", "7")
    monkeypatch.setenv("SESSION_MAX_SESSIONS", "100")
    init_db()
    return data_dir


def test_init_db_and_wal():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode;")
        mode = cur.fetchone()[0]
        assert mode.lower() == "wal"


def test_session_store_crud():
    store = VirtualSessionStore()
    vid = "test-sess-123"

    # 1. get_or_create
    rec = store.get_or_create(vid, api_key_hash="hash123")
    assert rec.session_id == vid
    assert rec.data == {}
    assert rec.api_key_hash == "hash123"

    # 2. update
    store.update(vid, history=[{"role": "user", "content": "hello"}], profile_id="prof_1")

    # 3. get
    rec2 = store.get(vid)
    assert rec2 is not None
    assert rec2.data["profile_id"] == "prof_1"
    assert len(rec2.data["history"]) == 1

    # 4. save_data
    store.save_data(vid, {"profile_id": "prof_2", "history": []})
    rec3 = store.get(vid)
    assert rec3.data["profile_id"] == "prof_2"

    # 5. query by api_key_hash
    sessions = store.get_sessions_by_api_key("hash123")
    assert len(sessions) == 1
    assert sessions[0].session_id == vid


def test_assistant_cache():
    store = VirtualSessionStore()
    vid = "sess-for-cache"
    store.get_or_create(vid)

    store.set_assistant("prompt-hash-1", vid)
    assert store.get_assistant("prompt-hash-1") == vid
    assert store.get_assistant("non-existent") is None


def test_profile_crud():
    # 1. create
    p1 = create_profile(profile_type="deepseek", name="DeepSeek Test", token="ds-token-123")
    assert p1["id"].startswith("prof_deepseek_")
    assert p1["name"] == "DeepSeek Test"
    assert p1["token"] == "ds-token-123"
    assert p1["is_active"] is True

    # 2. get
    fetched = get_profile(p1["id"])
    assert fetched is not None
    assert fetched["name"] == "DeepSeek Test"

    # 3. list
    profiles = list_profiles(profile_type="deepseek")
    assert any(p["id"] == p1["id"] for p in profiles)

    # 4. update
    updated = update_profile(p1["id"], name="DeepSeek Renamed", is_active=False)
    assert updated["name"] == "DeepSeek Renamed"
    assert updated["is_active"] is False

    # 5. record requests
    rec_prof = record_profile_request(p1["id"])
    assert rec_prof["total_requests"] == 1

    # 6. delete
    assert delete_profile(p1["id"]) is True
    assert get_profile(p1["id"]) is None


def test_api_key_lifecycle():
    key = generate_api_key(name="Client Key")
    assert key.startswith("sk-")

    # validate
    assert validate_api_key(key) is True

    # list
    keys = list_api_keys()
    assert any(k["key"] == key for k in keys)

    # revoke
    assert revoke_api_key(key) is True
    assert validate_api_key(key) is False

