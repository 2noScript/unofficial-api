import logging
from .base import BaseSessionAdapter

logger = logging.getLogger(__name__)

class GeminiAdapter(BaseSessionAdapter):
    @property
    def scope(self) -> str:
        return 'gemini'

    def inject(self, data: dict, request_args: dict) -> dict:
        kwargs = {}
        cid = data.get('gemini_cid')
        if cid:
            kwargs['chat_data'] = {'cid': cid}
            logger.debug('Injected gemini cid: %s', cid[:20])
        state = data.get('gemini_session_state')
        if state:
            kwargs['session_state'] = state
        return kwargs

    def extract(self, response, data: dict) -> dict:
        new_data = dict(data)
        if hasattr(response, 'cid') and response.cid:
            new_data['gemini_cid'] = response.cid
            logger.debug('Extracted gemini cid: %s', response.cid[:20])
        if hasattr(response, 'session_state'):
            new_data['gemini_session_state'] = response.session_state
        return new_data
