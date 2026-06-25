"""
core/session/history.py

Utilities for managing the gateway-side conversation history that makes
virtual sessions provider-independent.

Design
------
Each session's `session_data` dict keeps a `history` key that is a list of
OpenAI-style messages:

    [
        {"role": "user",      "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!"},
        ...
    ]

When a router calls `sync_and_get_history` it:
1. Merges any new user / assistant turns from the incoming request into the
   local history (deduplication by content prefix).
2. Returns the updated local history list.

When a provider session has expired / does not exist the router calls
`format_prompt_with_history` to turn the history into a single user-prompt
text (a transcript) that can be sent in a fresh provider conversation so
context is preserved without relying on the provider's server-side state.
"""
from __future__ import annotations

import logging
from core.utils import extract_text

logger = logging.getLogger(__name__)

# How many characters of history to fingerprint for dedup
_DEDUP_LEN = 80


def _msg_fingerprint(msg: dict) -> str:
    """Short fingerprint used to detect if a message is already in history."""
    role = msg.get("role", "")
    content = extract_text(msg.get("content", ""))
    return f"{role}:{content[:_DEDUP_LEN]}"


def sync_and_get_history(
    body_messages: list[dict],
    session_data: dict,
    *,
    max_turns: int = 50,
) -> list[dict]:
    """Integrate incoming request messages into the session's local history.

    Parameters
    ----------
    body_messages:
        The ``messages`` list from the incoming OpenAI-compatible request.
        Items should be plain dicts with ``role`` and ``content`` keys.
    session_data:
        The mutable ``session_data`` dict attached to the virtual session
        (``request.state.session_data``).  Modified in-place.
    max_turns:
        Maximum number of messages kept in history to avoid unbounded growth.

    Returns
    -------
    list[dict]
        The updated history list (same object as ``session_data['history']``).
    """
    history: list[dict] = session_data.setdefault("history", [])

    # Build a set of existing fingerprints for O(1) dedup lookup
    existing_fps = {_msg_fingerprint(m) for m in history}

    for msg in body_messages:
        role = msg.get("role", "")
        content = msg.get("content")
        if not role or content is None:
            continue
        # Normalise content to a plain string for storage
        if not isinstance(content, str):
            content = extract_text(content)

        fp = f"{role}:{content[:_DEDUP_LEN]}"
        if fp in existing_fps:
            continue  # already in history

        history.append({"role": role, "content": content})
        existing_fps.add(fp)

    # Trim to max_turns (keep the most recent turns)
    if len(history) > max_turns:
        session_data["history"] = history[-max_turns:]
        history = session_data["history"]

    logger.debug("History synced: %d turns in session", len(history))
    return history


def append_assistant_message(session_data: dict, content: str) -> None:
    """Append an assistant message to the session's local history.

    This should be called by routers after a successful provider response so
    that the next turn can reconstruct full context.
    """
    if not content:
        return
    history: list[dict] = session_data.setdefault("history", [])
    history.append({"role": "assistant", "content": content})
    logger.debug("Appended assistant turn to history (%d total)", len(history))


def format_prompt_with_history(
    history: list[dict],
    current_user_prompt: str,
) -> str:
    """Format conversation history as a transcript prefix for a new session.

    When a provider-side chat session has expired (or never existed), call
    this to embed the full conversation context into the first user message of
    a fresh provider session.

    The transcript uses a simple, universally understood format::

        [Previous conversation]
        User: ...
        Assistant: ...
        ...
        [Current message]
        ...

    Parameters
    ----------
    history:
        The list of historical messages **excluding** the current turn.
    current_user_prompt:
        The actual user prompt for the current turn.

    Returns
    -------
    str
        A single string that can be passed as the ``prompt`` / ``message``
        parameter to the provider SDK.
    """
    # Only include turns before the current one (avoid duplicate)
    prior = [m for m in history if m.get("role") != "system"]
    # If the last entry is the user message for the current turn, exclude it
    if prior and prior[-1].get("role") == "user":
        last_content = extract_text(prior[-1].get("content", ""))
        if last_content.strip() == current_user_prompt.strip():
            prior = prior[:-1]

    if not prior:
        return current_user_prompt  # No prior history → send as-is

    lines = ["[Previous conversation]"]
    for msg in prior:
        role = msg.get("role", "unknown").capitalize()
        content = extract_text(msg.get("content", ""))
        lines.append(f"{role}: {content}")

    lines.append("")
    lines.append("[Current message]")
    lines.append(current_user_prompt)

    return "\n".join(lines)
