from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    model_config = {"extra": "ignore"}
    role: str = Field(
        ..., description="Role of the message", examples=["user", "assistant"]
    )
    content: str | list | None = Field(
        None, description="Content of the message", examples=["Hello!", "Tell me about AI"]
    )


class ChatCompletionRequest(BaseModel):
    model_config = {"extra": "ignore"}
    model: str = Field(
        ...,
        description="Model ID to use",
        examples=[
            "deepseek-v3",
            "deepseek-r1",
            "gemini-3-flash",
            "gemini-3-pro",
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
    model_config = {"extra": "ignore"}
    id: str = Field(..., description="Unique chat completion ID", examples=["chatcmpl-1234567890"])
    object: str = Field("chat.completion", description="Object type")
    created: int = Field(..., description="Unix timestamp of creation")
    model: str = Field(..., description="Model used")
    choices: list[Choice] = Field(..., description="List of completion choices")
    usage: Usage = Field(..., description="Token usage statistics")
    citation: str | None = Field(None, description="Citation (DeepSeek)")
    title: str | None = Field(None, description="Title (DeepSeek)")


class ModelObject(BaseModel):
    id: str = Field(..., description="Model ID")
    object: str = Field("model", description="Object type")
    created: int = Field(1704067200, description="Creation timestamp")
    owned_by: str = Field(..., description="Provider name")
    description: str = Field(..., description="Model description")


class ModelList(BaseModel):
    object: str = Field("list", description="Object type")
    data: list[ModelObject] = Field(..., description="List of available models")


# === Gemini Chat History ===

class ChatInfoSchema(BaseModel):
    cid: str = Field(..., description="Chat ID")
    title: str = Field("", description="Chat title")
    is_pinned: bool = Field(False, description="Whether chat is pinned")
    timestamp: float = Field(0.0, description="Last modification timestamp")


class ChatTurnSchema(BaseModel):
    role: str = Field(..., description="Message role", examples=["user", "model"])
    text: str = Field("", description="Message content")


class ChatHistorySchema(BaseModel):
    cid: str = Field(..., description="Chat ID")
    turns: list[ChatTurnSchema] = Field(default_factory=list, description="Chat messages")


# === Gemini Gems ===

class GemSchema(BaseModel):
    id: str = Field(..., description="Gem ID")
    name: str = Field(..., description="Gem name")
    description: str | None = Field(None, description="Gem description")
    prompt: str | None = Field(None, description="System prompt")
    predefined: bool = Field(False, description="Whether gem is predefined")


class GemCreateRequest(BaseModel):
    name: str = Field(..., description="Gem name", min_length=1)
    prompt: str = Field(..., description="System prompt", min_length=1)
    description: str = Field("", description="Optional description")


class GemUpdateRequest(BaseModel):
    name: str = Field(..., description="New gem name")
    prompt: str = Field(..., description="New system prompt")
    description: str = Field("", description="New description")


# === Deep Research ===

class DeepResearchPlanSchema(BaseModel):
    research_id: str | None = Field(None, description="Research ID after confirmation")
    title: str | None = Field(None, description="Research title")
    query: str | None = Field(None, description="Original query")
    steps: list[str] = Field(default_factory=list, description="Research steps")
    eta_text: str | None = Field(None, description="Estimated time")
    confirm_prompt: str | None = Field(None, description="Prompt to confirm start")
    cid: str | None = Field(None, description="Chat session ID")


class DeepResearchPlanRequest(BaseModel):
    prompt: str = Field(..., description="Research topic or question", min_length=1)
    model: str | None = Field(None, description="Model to use")


class DeepResearchPlanResponse(BaseModel):
    plan: DeepResearchPlanSchema
    response_text: str | None = Field(None, description="Full model response text")


class DeepResearchFullRequest(BaseModel):
    prompt: str = Field(..., description="Research topic or question", min_length=1)
    model: str | None = Field(None, description="Model to use")
    poll_interval: float = Field(10.0, description="Seconds between status polls", gt=0)
    timeout: float = Field(600.0, description="Max seconds to wait", gt=0)


class DeepResearchStartRequest(BaseModel):
    plan: DeepResearchPlanSchema = Field(..., description="Plan from create endpoint")
    confirm_prompt: str | None = Field(None, description="Override confirmation prompt")


class DeepResearchStatusSchema(BaseModel):
    research_id: str = Field(..., description="Research ID")
    state: str = Field("running", description="Current state")
    title: str | None = Field(None, description="Research title")
    query: str | None = Field(None, description="Original query")
    cid: str | None = Field(None, description="Chat session ID")
    notes: list[str] = Field(default_factory=list, description="Research notes")
    done: bool = Field(False, description="Whether research is complete")
