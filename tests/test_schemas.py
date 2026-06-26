import pytest
from pydantic import ValidationError
from core.schemas import ChatCompletionRequest, ChatMessage, ChatCompletionResponse


class TestChatCompletionRequest:
    def test_valid_request(self):
        req = ChatCompletionRequest(
            model="deepseek-v3",
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert req.model == "deepseek-v3"
        assert len(req.messages) == 1
        assert req.stream is False

    def test_valid_request_with_stream(self):
        req = ChatCompletionRequest(
            model="gemini-3-flash",
            messages=[{"role": "user", "content": "Hi"}],
            stream=True,
        )
        assert req.stream is True

    def test_missing_messages_fails(self):
        with pytest.raises(ValidationError):
            ChatCompletionRequest(model="deepseek-v3", messages=[])

    def test_extra_fields_ignored(self):
        req = ChatCompletionRequest(
            model="deepseek-v3",
            messages=[{"role": "user", "content": "Hello"}],
            extra_field="ignored",
        )
        assert not hasattr(req, "extra_field")


class TestChatMessage:
    def test_valid_message(self):
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_content_none_allowed(self):
        msg = ChatMessage(role="assistant", content=None)
        assert msg.content is None

    def test_content_list_allowed(self):
        msg = ChatMessage(role="user", content=[{"type": "text", "text": "Hello"}])
        assert isinstance(msg.content, list)


class TestChatCompletionResponse:
    def test_valid_response(self):
        resp = ChatCompletionResponse(
            id="chatcmpl-123",
            created=1700000000,
            model="deepseek-v3",
            choices=[{"index": 0, "message": {"role": "assistant", "content": "Hello"}, "finish_reason": "stop"}],
            usage={"prompt_tokens": 0, "completion_tokens": 1, "total_tokens": 1},
        )
        assert resp.choices[0].message.content == "Hello"
        assert resp.choices[0].message.reasoning_content is None

    def test_with_reasoning_content(self):
        resp = ChatCompletionResponse(
            id="chatcmpl-123",
            created=1700000000,
            model="deepseek-r1",
            choices=[{"index": 0, "message": {"role": "assistant", "content": "Answer", "reasoning_content": "Thinking..."}, "finish_reason": "stop"}],
            usage={"prompt_tokens": 0, "completion_tokens": 1, "total_tokens": 1},
        )
        assert resp.choices[0].message.reasoning_content == "Thinking..."
