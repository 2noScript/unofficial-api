from .base import BaseSessionAdapter

class MetaAIAdapter(BaseSessionAdapter):
    @property
    def scope(self) -> str:
        return 'metaai'
