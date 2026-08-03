import logging
from .base import BaseSessionAdapter

logger = logging.getLogger(__name__)


class GeminiAdapter(BaseSessionAdapter):
    @property
    def scope(self) -> str:
        return 'gemini'

    def inject(self, data: dict, request_args: dict) -> dict:
        client = request_args.get('client')
        if not client:
            return {}
        chat_cls = request_args.get('chat_cls')
        if not chat_cls:
            from gemini_webapi import ChatSession
            chat_cls = ChatSession
        metadata = data.get('gemini_metadata')
        if metadata:
            chat = chat_cls(geminiclient=client, metadata=metadata)
        else:
            cid = data.get('gemini_cid', '')
            chat = chat_cls(geminiclient=client, cid=cid)
        return {'chat': chat}

    def extract(self, response, data: dict) -> dict:
        new_data = dict(data)
        cid = getattr(response, 'cid', None)
        if cid:
            new_data['gemini_cid'] = cid
            logger.debug('Extracted gemini cid: %s', str(cid)[:20])
        metadata = getattr(response, 'metadata', None)
        if metadata:
            new_data['gemini_metadata'] = metadata
        state = getattr(response, 'session_state', None)
        if state:
            new_data['gemini_session_state'] = state
        return new_data

    def clear_provider_session(self, data: dict) -> None:
        data.pop('gemini_cid', None)
        data.pop('gemini_session_state', None)
        data.pop('gemini_metadata', None)
        logger.debug('Cleared gemini provider session state')
