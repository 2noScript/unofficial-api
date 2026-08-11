import pytest
from core.profile import create_profile, delete_profile, list_profiles
from core.load_balancer import load_balancer, NoActiveProfileError


class TestProfileLoadBalancer:
    def test_round_robin_distribution(self):
        # Create 2 active deepseek profiles
        p1 = create_profile("deepseek", "LB DeepSeek 1", token="Bearer tok_lb1")
        p2 = create_profile("deepseek", "LB DeepSeek 2", token="Bearer tok_lb2")

        try:
            active = load_balancer.get_active_profiles("deepseek")
            num_active = len(active)

            selected_ids = []
            for _ in range(num_active):
                sel, reused = load_balancer.select_profile("deepseek")
                assert reused is False
                selected_ids.append(sel["id"])

            # All active profiles should be selected once per cycle
            assert set(selected_ids) == {p["id"] for p in active}
            assert len(selected_ids) == len(set(selected_ids))

            # Next selection should loop back to first selected
            sel_next, _ = load_balancer.select_profile("deepseek")
            assert sel_next["id"] == selected_ids[0]
        finally:
            delete_profile(p1["id"])
            delete_profile(p2["id"])

    def test_session_sticky_affinity(self):
        p1 = create_profile("deepseek", "Sticky 1", token="Bearer tok_s1")
        p2 = create_profile("deepseek", "Sticky 2", token="Bearer tok_s2")

        session_data = {}

        try:
            # Turn 1: No profile in session_data -> selects a profile and stores profile_id
            sel1, reused1 = load_balancer.select_profile("deepseek", session_data=session_data)
            assert reused1 is False
            assert "profile_id" in session_data
            pid = session_data["profile_id"]
            assert pid == sel1["id"]

            # Turn 2: Subsequent selection with same session_data -> reuses the SAME profile
            sel2, reused2 = load_balancer.select_profile("deepseek", session_data=session_data)
            assert reused2 is True
            assert sel2["id"] == pid

            # Turn 3: Continuous reuse
            sel3, reused3 = load_balancer.select_profile("deepseek", session_data=session_data)
            assert reused3 is True
            assert sel3["id"] == pid
        finally:
            delete_profile(p1["id"])
            delete_profile(p2["id"])

    def test_sticky_session_failover(self):
        p1 = create_profile("gemini", "Failover Gem 1", cookie="__Secure-1PSID=gem1")
        p2 = create_profile("gemini", "Failover Gem 2", cookie="__Secure-1PSID=gem2")

        session_data = {"profile_id": p1["id"]}

        try:
            # p1 is deactivated / deleted
            delete_profile(p1["id"])

            # Next request should detect p1 is no longer active and FAIL OVER to another active profile
            sel2, reused2 = load_balancer.select_profile("gemini", session_data=session_data)
            assert reused2 is False
            assert sel2["id"] != p1["id"]
            assert session_data["profile_id"] == sel2["id"]
        finally:
            delete_profile(p1["id"])
            delete_profile(p2["id"])

    def test_no_active_profile_error(self):
        # Ensure inactive profiles are skipped
        p_inactive = create_profile("deepseek", "Inactive", token="tok_in", is_active=False)

        try:
            # If all profiles are inactive and no env set, active list filters it out
            active = load_balancer.get_active_profiles("deepseek")
            assert p_inactive["id"] not in [p["id"] for p in active]
        finally:
            delete_profile(p_inactive["id"])

    def test_handle_profile_failure(self):
        p1 = create_profile("deepseek", "Failing DeepSeek", token="Bearer tok_fail")
        session_data = {"profile_id": p1["id"]}

        try:
            load_balancer.handle_profile_failure(p1["id"], session_data)
            assert session_data.get("profile_id") is None
            active = load_balancer.get_active_profiles("deepseek")
            assert p1["id"] not in [p["id"] for p in active]
        finally:
            delete_profile(p1["id"])

    def test_is_retryable_error(self):
        assert load_balancer.is_retryable_error("HTTP 401: Unauthorized token") is True
        assert load_balancer.is_retryable_error("HTTP 429: Too Many Requests") is True
        assert load_balancer.is_retryable_error("Gemini cookie is unauthenticated or expired") is True
        assert load_balancer.is_retryable_error("SyntaxError: bad token") is False

