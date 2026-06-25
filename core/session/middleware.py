import json
import logging
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from .store import VirtualSessionStore
from .manager import VirtualSessionManager

logger = logging.getLogger(__name__)

CHAT_PATHS = {'/chat/completions'}

async def session_saving_generator(iterator, store):
    try:
        async for chunk in iterator:
            yield chunk
    finally:
        try:
            store._save_to_disk()
        except Exception as e:
            logger.error("Failed to save session to disk in streaming middleware: %s", e)

class VirtualSessionMiddleware:
    def __init__(self, store: VirtualSessionStore, manager: VirtualSessionManager, validate_key_fn, get_key_hash_fn, extract_provider_fn):
        self.store = store
        self.manager = manager
        self.validate_key = validate_key_fn
        self.get_key_hash = get_key_hash_fn
        self.extract_provider = extract_provider_fn

    async def _read_body(self, request: Request) -> dict:
        body = await request.body()
        if not body:
            return {}
        request._body = body
        try:
            return json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    async def __call__(self, request: Request, call_next):
        path = request.url.path.rstrip('/')
        
        if not any(path.endswith(p) for p in CHAT_PATHS):
            return await call_next(request)
            
        api_key = None
        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            api_key = auth_header[7:].strip()
        if not api_key:
            api_key = request.headers.get('x-api-key')
            
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "message": "API key required. Set Authorization: Bearer <key> or X-Api-Key header.",
                        "type": "auth_error",
                        "code": "missing_api_key"
                    }
                }
            )
            
        if not self.validate_key(api_key):
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "message": "Invalid or deactivated API key.",
                        "type": "auth_error",
                        "code": "invalid_api_key"
                    }
                }
            )
            
        body = await self._read_body(request)
        provider = self.extract_provider(path)
        api_key_hash = self.get_key_hash(api_key)
        
        if request.client:
            fingerprint = f"{request.client.host}:{request.headers.get('user-agent', '')[:64]}"
        else:
            fingerprint = 'unknown'
            
        try:
            vid = self.manager.resolve(
                headers=dict(request.headers),
                body=body,
                provider=provider,
                api_key_hash=api_key_hash,
                fingerprint=fingerprint
            )
        except Exception as e:
            logger.error('Session resolution error: %s', e)
            vid = self.manager._derive_session_id(api_key_hash or fingerprint or 'error')
            
        session_record = self.store.get_or_create(vid, api_key_hash=api_key_hash)
        
        request.state.virtual_session_id = vid
        request.state.session_data = session_record.data
        
        response = await call_next(request)
        response.headers['X-Session-Id'] = vid
        
        # Automatically save session to disk on completion
        if hasattr(response, 'body_iterator'):
            response.body_iterator = session_saving_generator(response.body_iterator, self.store)
        else:
            try:
                self.store._save_to_disk()
            except Exception as e:
                logger.error("Failed to save session to disk: %s", e)
                
        return response
