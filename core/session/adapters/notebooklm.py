import logging
from .base import BaseSessionAdapter

logger = logging.getLogger(__name__)


class NotebookLMAdapter(BaseSessionAdapter):
    @property
    def scope(self) -> str:
        return 'notebooklm'

    def inject(self, data: dict, request_args: dict) -> dict:
        kwargs = {}
        cid = data.get('notebooklm_conversation_id')
        if cid:
            kwargs['conversation_id'] = cid
            logger.debug('Injected notebooklm conversation_id: %s', cid[:20])
        return kwargs

    def extract(self, response, data: dict) -> dict:
        new_data = dict(data)
        if hasattr(response, 'conversation_id') and response.conversation_id:
            new_data['notebooklm_conversation_id'] = response.conversation_id
            logger.debug('Extracted notebooklm conversation_id: %s', response.conversation_id[:20])
        return new_data

    def clear_provider_session(self, data: dict) -> None:
        data.pop('notebooklm_conversation_id', None)
        logger.debug('Cleared notebooklm provider session state')
