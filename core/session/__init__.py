from .store import VirtualSessionStore, SessionRecord
from .manager import VirtualSessionManager
from .api_key import (
    generate_api_key,
    validate_api_key,
    list_api_keys,
    revoke_api_key,
    get_api_key_hash,
)
from .middleware import VirtualSessionMiddleware
from .adapters import get_adapter, list_adapters

_store: VirtualSessionStore | None = None
_manager: VirtualSessionManager | None = None

def get_store() -> VirtualSessionStore:
    global _store
    if _store is None:
        _store = VirtualSessionStore()
    return _store

def get_manager() -> VirtualSessionManager:
    global _manager
    if _manager is None:
        _manager = VirtualSessionManager(get_store())
    return _manager

def init_session_system():
    store = get_store()
    manager = get_manager()
    return store, manager

session_store = get_store()
session_manager = get_manager()

__all__ = [
    'VirtualSessionStore',
    'VirtualSessionManager',
    'SessionRecord',
    'generate_api_key',
    'validate_api_key',
    'list_api_keys',
    'revoke_api_key',
    'get_api_key_hash',
    'VirtualSessionMiddleware',
    'get_adapter',
    'list_adapters',
    'get_store',
    'get_manager',
    'init_session_system',
    'session_store',
    'session_manager',
]
