import time
import asyncio
import logging
from typing import Any, AsyncGenerator

from fastapi import Request
from fastapi.responses import JSONResponse, StreamingResponse
from gemini_webapi import ChatSession

from core.services.base import BaseProviderStrategy
from core.load_balancer import load_balancer, NoActiveProfileError
from core.profile import record_profile_request
from core.utils import extract_text, make_stream_chunk, make_error_chunk, STREAM_END
from core.session.history import sync_and_get_history, append_assistant_message, format_prompt_with_history

logger = logging.getLogger(__name__)



class ChatExecutionService:
    """Unified Chat Execution Pipeline (Strategy + Decorator Pattern)."""

    @staticmethod
    def _has_provider_session(provider_name: str, session_data: dict) -> bool:
        if provider_name == "gemini":
            cid = session_data.get("gemini_cid")
            metadata = session_data.get("gemini_metadata")
            return bool(cid or (metadata and isinstance(metadata, list) and len(metadata) > 0 and metadata[0]))
        elif provider_name == "deepseek":
            return bool(session_data.get("deepseek_chat_session_id")) and not session_data.get("deepseek_force_virtual")
        return False

    @classmethod
    async def resolve_client(
        cls, strategy: BaseProviderStrategy, request: Request, session_data: dict
    ) -> tuple[Any, str | None, JSONResponse | None]:
        """Select an active profile and resolve client instance."""
        provider_name = strategy.provider_name
        active_profiles = load_balancer.get_active_profiles(provider_name)
        max_attempts = max(1, len(active_profiles))

        for attempt in range(max_attempts):
            profile_id = None
            try:
                profile, _ = load_balancer.select_profile(provider_name, session_data=session_data)
                profile_id = profile.get("id")
                client = await strategy.get_or_create_client(profile, request)
                return client, profile_id, None
            except NoActiveProfileError:
                try:
                    client = await strategy.get_or_create_client(None, request)
                    return client, None, None
                except Exception as e:
                    return None, None, JSONResponse(
                        {"error": {"message": str(e), "type": "authentication_error", "code": "no_credentials"}},
                        status_code=503,
                    )
            except Exception as e:
                err_str = str(e)
                logger.warning("Profile '%s' init failed (%s). Failing over...", profile_id, err_str)
                if profile_id and strategy.is_retryable_error(err_str):
                    is_auth = load_balancer.is_auth_failure(err_str)
                    load_balancer.handle_profile_failure(profile_id, session_data, is_permanent=is_auth)
                    await strategy.handle_profile_cleanup(profile_id)
                if attempt < max_attempts - 1 and load_balancer.get_active_profiles(provider_name):
                    continue
                return None, None, JSONResponse(
                    {"error": {"message": f"Profile error: {err_str}", "type": "server_error", "code": "upstream_error"}},
                    status_code=500,
                )

        return None, None, JSONResponse(
            {"error": {"message": f"No active {provider_name} profile available.", "type": "server_error", "code": "no_active_profile"}},
            status_code=503,
        )

    @classmethod
    async def execute_chat(
        cls,
        strategy: BaseProviderStrategy,
        request: Request,
        messages: list,
        model: str,
        session_data: dict,
        adapter,
    ) -> JSONResponse:
        """Execute non-streaming chat with session resilience and profile failover."""
        provider_name = strategy.provider_name
        active_profiles = load_balancer.get_active_profiles(provider_name)
        max_profile_attempts = max(1, len(active_profiles))

        raw_prompt = extract_text(messages[-1].get("content") if isinstance(messages[-1], dict) else messages[-1].content) if messages else ""
        sync_and_get_history(messages, session_data)
        history = session_data.get("history", [])

        last_error_resp = None

        for p_attempt in range(max_profile_attempts):
            client, profile_id, err_resp = await cls.resolve_client(strategy, request, session_data)
            if err_resp or not client:
                return err_resp or JSONResponse(
                    {"error": {"message": "Client not initialized.", "type": "server_error", "code": "upstream_error"}},
                    status_code=500,
                )

            if profile_id:
                asyncio.create_task(asyncio.to_thread(record_profile_request, profile_id))

            should_failover = False

            for attempt in range(2):
                has_session = cls._has_provider_session(provider_name, session_data) and attempt == 0
                prompt = raw_prompt if has_session else format_prompt_with_history(history, raw_prompt)

                # Build session kwargs
                inject_kwargs = {"client": client}
                if provider_name == "gemini":
                    inject_kwargs["chat_cls"] = ChatSession
                session_kwargs = adapter.inject(session_data, inject_kwargs)

                try:
                    content, thoughts = await strategy.execute_chat(client, prompt, model, session_kwargs)
                except Exception as e:
                    err_str = str(e)
                    if strategy.is_retryable_error(err_str):
                        is_auth = load_balancer.is_auth_failure(err_str)
                        logger.warning("Profile '%s' error (%s). is_permanent=%s", profile_id, err_str, is_auth)
                        if profile_id:
                            load_balancer.handle_profile_failure(profile_id, session_data, is_permanent=is_auth)
                            await strategy.handle_profile_cleanup(profile_id)
                        if p_attempt < max_profile_attempts - 1 and load_balancer.get_active_profiles(provider_name):
                            should_failover = True
                            break

                    if attempt == 0 and cls._has_provider_session(provider_name, session_data):
                        logger.warning("%s provider session error, resetting and retrying with prompt history...", provider_name)
                        adapter.clear_provider_session(session_data)
                        continue

                    logger.error("%s execution error: %s", provider_name, err_str)
                    last_error_resp = JSONResponse(
                        {"error": {"message": err_str, "type": "server_error", "code": "upstream_error"}},
                        status_code=500,
                    )
                    break

                # Extract updated session state
                if "chat" in session_kwargs:
                    session_data.update(adapter.extract(session_kwargs["chat"], session_data))

                append_assistant_message(session_data, content)

                response_data = {
                    "id": f"chatcmpl-{int(time.time())}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": content},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": len(content.split()) if content else 0,
                        "total_tokens": len(content.split()) if content else 0,
                    },
                }

                if thoughts:
                    response_data["choices"][0]["message"]["reasoning_content"] = thoughts

                return JSONResponse(response_data)

            if should_failover:
                continue

            if last_error_resp:
                return last_error_resp

        return last_error_resp or JSONResponse(
            {"error": {"message": "All available profiles failed", "type": "server_error", "code": "upstream_error"}},
            status_code=500,
        )

    @classmethod
    async def execute_stream(
        cls,
        strategy: BaseProviderStrategy,
        request: Request,
        messages: list,
        model: str,
        session_data: dict,
        adapter,
    ) -> StreamingResponse | JSONResponse:
        """Execute streaming chat with unified session resilience and profile failover."""
        client, profile_id, err_resp = await cls.resolve_client(strategy, request, session_data)
        if err_resp or not client:
            return err_resp or JSONResponse(
                {"error": {"message": "Client not initialized.", "type": "server_error", "code": "upstream_error"}},
                status_code=500,
            )

        if profile_id:
            asyncio.create_task(asyncio.to_thread(record_profile_request, profile_id))

        provider_name = strategy.provider_name
        raw_prompt = extract_text(messages[-1].get("content") if isinstance(messages[-1], dict) else messages[-1].content) if messages else ""
        sync_and_get_history(messages, session_data)
        history = session_data.get("history", [])

        async def stream_generator():

            response_id = f"chatcmpl-{int(time.time())}"
            has_session = cls._has_provider_session(provider_name, session_data)
            prompt = raw_prompt if has_session else format_prompt_with_history(history, raw_prompt)

            inject_kwargs = {"client": client}
            if provider_name == "gemini":
                inject_kwargs["chat_cls"] = ChatSession
            session_kwargs = adapter.inject(session_data, inject_kwargs)

            collected_chunks = []
            first = True
            try:
                gen = strategy.execute_stream(client, prompt, model, session_kwargs)
                async for delta in gen:
                    if delta:
                        collected_chunks.append(delta)
                        yield make_stream_chunk(model, delta, response_id, is_first=first)
                        first = False

                # Extract updated session state
                if "chat" in session_kwargs:
                    session_data.update(adapter.extract(session_kwargs["chat"], session_data))

                full_response = "".join(collected_chunks)
                append_assistant_message(session_data, full_response)
                yield make_stream_chunk(model, "", response_id, is_final=True)
                yield STREAM_END
            except Exception as e:
                err_str = str(e)
                if strategy.is_retryable_error(err_str):
                    is_auth = load_balancer.is_auth_failure(err_str)
                    logger.warning("Profile '%s' failed on stream (%s). is_permanent=%s", profile_id, err_str, is_auth)
                    if profile_id:
                        load_balancer.handle_profile_failure(profile_id, session_data, is_permanent=is_auth)
                        await strategy.handle_profile_cleanup(profile_id)
                logger.error("%s stream execution error: %s", provider_name, err_str)
                yield make_error_chunk(err_str)
                yield STREAM_END

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )



chat_service = ChatExecutionService()
