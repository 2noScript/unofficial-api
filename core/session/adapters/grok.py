from .base import BaseSessionAdapter

class GrokAdapter(BaseSessionAdapter):
    @property
    def scope(self) -> str:
        return 'grok'
