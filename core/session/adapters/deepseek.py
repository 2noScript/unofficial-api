import logging
from .base import BaseSessionAdapter

logger = logging.getLogger(__name__)


class DeepSeekAdapter(BaseSessionAdapter):
    @property
    def scope(self) -> str:
        return 'deepseek'

    def inject(self, data: dict, request_args: dict) -> dict:
        """Inject stored DeepSeek session state into ChatSession kwargs."""
        kwargs = {}
        sid = data.get('deepseek_chat_session_id')
        if sid:
            kwargs['chat_session_id'] = sid
            logger.debug('Injected deepseek chat_session_id: %s', str(sid)[:20])
        pid = data.get('deepseek_parent_message_id')
        if pid:
            kwargs['parent_message_id'] = pid
            logger.debug('Injected deepseek parent_message_id: %s', str(pid)[:20])

        chat = request_args.get('chat')
        if chat is not None:
            if sid:
                chat.chat_session_id = sid
            if pid:
                chat.parent_message_id = pid

        return kwargs

    def extract(self, response: dict, data: dict) -> dict:
        """Extract and persist DeepSeek session state after a response."""
        new_data = dict(data)
        chat = response.get('_chat_instance')
        if not chat:
            return new_data

        state = getattr(chat, 'get_state', lambda: {})()
        chat_session_id = state.get('chat_session_id') or getattr(chat, 'chat_session_id', None)
        parent_message_id = state.get('parent_message_id') or getattr(chat, 'parent_message_id', None)

        if chat_session_id:
            new_data['deepseek_chat_session_id'] = chat_session_id
            logger.debug('Extracted deepseek chat_session_id: %s', str(chat_session_id)[:20])
        if parent_message_id:
            new_data['deepseek_parent_message_id'] = parent_message_id
            logger.debug('Extracted deepseek parent_message_id: %s', str(parent_message_id)[:20])
        return new_data

    def clear_provider_session(self, data: dict) -> None:
        """Clear provider-side session IDs so the next request starts fresh."""
        data.pop('deepseek_chat_session_id', None)
        data.pop('deepseek_parent_message_id', None)
        logger.debug('Cleared deepseek provider session state')
