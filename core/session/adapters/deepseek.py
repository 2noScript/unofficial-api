import logging
from .base import BaseSessionAdapter

logger = logging.getLogger(__name__)

class DeepSeekAdapter(BaseSessionAdapter):
    @property
    def scope(self) -> str:
        return 'deepseek'

    def inject(self, data: dict, request_args: dict) -> dict:
        chat = request_args.get('chat')
        if chat is None:
            return {}
        sid = data.get('deepseek_chat_session_id')
        if sid:
            chat.chat_session_id = sid
            logger.debug('Injected deepseek chat_session_id: %s', sid[:20])
        return {}

    def extract(self, result: dict, data: dict) -> dict:
        new_data = dict(data)
        chat = result.get('_chat_instance')
        if chat and getattr(chat, 'chat_session_id', None):
            new_data['deepseek_chat_session_id'] = chat.chat_session_id
            logger.debug('Extracted deepseek chat_session_id: %s', chat.chat_session_id[:20])
        return new_data
