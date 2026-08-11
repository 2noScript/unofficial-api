import logging
from typing import Tuple
from core.profile import list_profiles

logger = logging.getLogger(__name__)


class NoActiveProfileError(Exception):
    """Raised when no active profile with valid credentials is found for a provider."""
    pass


class ProfileLoadBalancer:
    def __init__(self):
        self._indices: dict[str, int] = {"deepseek": 0, "gemini": 0}

    def get_active_profiles(self, provider_type: str) -> list[dict]:
        all_profiles = list_profiles(profile_type=provider_type)
        active = []
        for p in all_profiles:
            if not p.get("is_active", True):
                continue
            if provider_type == "deepseek" and not p.get("token"):
                continue
            if provider_type == "gemini" and not p.get("cookie"):
                continue
            active.append(p)
        return active

    def select_profile(
        self,
        provider_type: str,
        session_data: dict | None = None
    ) -> Tuple[dict, bool]:
        """
        Select an active profile for the given provider_type.

        Session Sticky Affinity:
        - If session_data contains a valid, active 'profile_id', reuse that profile.
        - If the sticky profile is inactive or missing, failover to next active profile.
        - If no sticky profile is present, use Round-Robin and save 'profile_id' to session_data.

        Returns: (profile_dict, is_sticky_reused)
        """
        active_profiles = self.get_active_profiles(provider_type)
        if not active_profiles:
            raise NoActiveProfileError(f"No active profile found for provider '{provider_type}'.")

        # Check Sticky Session Affinity
        if session_data is not None:
            sticky_pid = session_data.get("profile_id")
            if sticky_pid:
                for p in active_profiles:
                    if p.get("id") == sticky_pid:
                        logger.debug("Reusing sticky profile '%s' for session", sticky_pid)
                        return p, True
                # Sticky profile is inactive or deleted -> Failover!
                logger.info("Sticky profile '%s' is no longer active. Failing over to next profile.", sticky_pid)
                session_data.pop("profile_id", None)

        # Round-Robin Selection
        idx = self._indices.get(provider_type, 0) % len(active_profiles)
        selected = active_profiles[idx]
        self._indices[provider_type] = (idx + 1) % len(active_profiles)

        if session_data is not None:
            session_data["profile_id"] = selected["id"]

        logger.debug("Selected profile '%s' via Round-Robin for provider '%s'", selected["id"], provider_type)
        return selected, False

    def handle_profile_failure(
        self,
        profile_id: str,
        session_data: dict | None = None
    ) -> None:
        """
        Deactivate a failing profile and clear sticky affinity from session_data.
        """
        from core.profile import deactivate_profile
        deactivate_profile(profile_id)
        if session_data is not None and session_data.get("profile_id") == profile_id:
            logger.info("Clearing sticky profile_id '%s' from session due to failure", profile_id)
            session_data.pop("profile_id", None)

    @staticmethod
    def is_retryable_error(err: str | Exception) -> bool:
        """
        Check if an error is an auth, credential expiration, or rate-limit error that warrants failover retry.
        """
        msg = str(err).lower()
        retryable_keywords = (
            "401", "403", "429", "unauthorized", "unauthenticated",
            "forbidden", "expired", "invalid cookie", "invalid token",
            "rate limit", "too many requests", "40300"
        )
        return any(kw in msg for kw in retryable_keywords)


load_balancer = ProfileLoadBalancer()

