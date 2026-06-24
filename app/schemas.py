from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(
        ..., description="Role of the message", examples=["user", "assistant"]
    )
    content: str = Field(
        ..., description="Content of the message", examples=["Hello!", "Tell me about AI"]
    )


class ChatCompletionRequest(BaseModel):
    model: str = Field(
        ...,
        description="Model ID to use",
        examples=[
            "deepseek-v3",
            "deepseek-r1",
            "deepseek-v4",
            "deepseek-r4",
            "gemini-3-flash",
            "gemini-3-pro",
            "gemini-3-flash-thinking",
        ],
    )
    messages: list[ChatMessage] = Field(
        ..., description="List of chat messages", min_length=1
    )
    stream: bool = Field(
        False, description="Whether to stream the response"
    )


class Usage(BaseModel):
    prompt_tokens: int = Field(0, description="Number of prompt tokens")
    completion_tokens: int = Field(0, description="Number of completion tokens")
    total_tokens: int = Field(0, description="Total number of tokens")


class ResponseMessage(BaseModel):
    role: str = Field("assistant", description="Role of the response")
    content: str = Field("", description="Content of the response")
    reasoning_content: str | None = Field(
        None, description="Reasoning/thinking content (for reasoning models)"
    )


class Choice(BaseModel):
    index: int = Field(0, description="Choice index")
    message: ResponseMessage = Field(..., description="Response message")
    finish_reason: str = Field("stop", description="Reason for finishing")


class ChatCompletionResponse(BaseModel):
    id: str = Field(..., description="Unique chat completion ID", examples=["chatcmpl-1234567890"])
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation")
    model: str = Field(..., description="Model used")
    choices: list[Choice] = Field(..., description="List of completion choices")
    usage: Usage = Field(..., description="Token usage statistics")


class ModelObject(BaseModel):
    id: str = Field(..., description="Model ID")
    object: str = Field("model", description="Object type")
    created: int = Field(1704067200, description="Creation timestamp")
    owned_by: str = Field(..., description="Provider name")
    description: str = Field(..., description="Model description")


class ModelList(BaseModel):
    object: str = Field("list", description="Object type")
    data: list[ModelObject] = Field(..., description="List of available models")
