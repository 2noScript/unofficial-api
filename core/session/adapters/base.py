class BaseSessionAdapter:
    @property
    def scope(self) -> str:
        return ""

    def inject(self, data: dict, request_args: dict) -> dict:
        return {}

    def extract(self, response, data: dict) -> dict:
        return data

    def clear_provider_session(self, data: dict) -> None:
        """Override to clear provider-specific session keys on session reset."""
        pass
