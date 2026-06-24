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


class ChatCompletionRequestGemini(ChatCompletionRequest):
    files: list[str] = Field(
        default_factory=list,
        description="List of file paths to attach",
        examples=[["/path/to/image.jpg", "/path/to/doc.pdf"]],
    )


# === NotebookLM Artifacts ===

class NLMGenerateRequest(BaseModel):
    source_ids: list[str] | None = Field(None, description="Specific source IDs to use")
    language: str = Field("en", description="Output language code")
    instructions: str | None = Field(None, description="Free-text generation instructions")


class NLMAudioGenerateRequest(NLMGenerateRequest):
    audio_format: str | None = Field(None, description="Audio format: deep_dive, brief, critique, debate")
    audio_length: str | None = Field(None, description="Audio length: short, default, long")


class NLMVideoGenerateRequest(NLMGenerateRequest):
    video_format: str | None = Field(None, description="Video format: explainer, brief, cinematic")
    video_style: str | None = Field(None, description="Visual style: auto_select, classic, whiteboard, anime, etc.")
    style_prompt: str | None = Field(None, description="Custom style prompt (requires video_style=custom)")


class NLMReportGenerateRequest(NLMGenerateRequest):
    report_format: str = Field("briefing_doc", description="Report format: briefing_doc, study_guide, blog_post, custom")
    custom_prompt: str | None = Field(None, description="Custom report prompt (for 'custom' format)")
    extra_instructions: str | None = Field(None, description="Extra instructions for generation")


class NLMStudyGuideGenerateRequest(NLMGenerateRequest):
    extra_instructions: str | None = Field(None, description="Extra instructions for generation")


class NLMQuizFlashcardsGenerateRequest(NLMGenerateRequest):
    quantity: str | None = Field(None, description="Quantity: fewer, standard, more")
    difficulty: str | None = Field(None, description="Difficulty: easy, medium, hard")


class NLMInfographicGenerateRequest(NLMGenerateRequest):
    orientation: str | None = Field(None, description="Orientation: landscape, portrait, square")
    detail_level: str | None = Field(None, description="Detail: concise, standard, detailed")
    style: str | None = Field(None, description="Visual style: auto_select, sketch_note, professional, etc.")


class NLMSlideDeckGenerateRequest(NLMGenerateRequest):
    slide_format: str | None = Field(None, description="Format: detailed_deck, presenter_slides")
    slide_length: str | None = Field(None, description="Length: default, short")


class NLMDataTableGenerateRequest(NLMGenerateRequest):
    pass


class NLMMindMapGenerateRequest(NLMGenerateRequest):
    wait: bool = Field(True, description="Wait for completion before returning")


class NLMGenerationStatusResponse(BaseModel):
    task_id: str = Field(..., description="Task/artifact ID for polling")
    status: str = Field(..., description="Generation status")
    url: str | None = Field(None, description="Download URL (when available)")
    error: str | None = Field(None, description="Error message")
    error_code: str | None = Field(None, description="Error code (e.g. USER_DISPLAYABLE_ERROR)")


class NLMArtifactResponse(BaseModel):
    id: str = Field(..., description="Artifact ID")
    title: str = Field("", description="Artifact title")
    kind: str = Field(..., description="Artifact type: audio, video, report, quiz, flashcards, mind_map, infographic, slide_deck, data_table")
    status: int = Field(0, description="Status code: 1=processing, 2=pending, 3=completed, 4=failed")
    status_str: str = Field("unknown", description="Human-readable status")
    created_at: str | None = Field(None, description="Creation timestamp")
    url: str | None = Field(None, description="Download URL")
    report_subtype: str | None = Field(None, description="Report subtype: briefing_doc, study_guide, blog_post")


class NLMArtifactListResponse(BaseModel):
    object: str = "list"
    data: list[NLMArtifactResponse] = Field(..., description="List of artifacts")


class NLMRenameRequest(BaseModel):
    title: str = Field(..., description="New artifact title", min_length=1)


class NLMReviseSlideRequest(BaseModel):
    slide_index: int = Field(..., description="Slide index to revise", ge=0)
    prompt: str = Field(..., description="Revision prompt", min_length=1)


class NLMWaitRequest(BaseModel):
    timeout: float = Field(300.0, description="Max seconds to wait", gt=0)
    initial_interval: float = Field(2.0, description="Initial poll interval", gt=0)
    max_interval: float = Field(10.0, description="Max poll interval", gt=0)


class NLMExportRequest(BaseModel):
    title: str = Field("Export", description="Export document title")


class NLMReportSuggestionResponse(BaseModel):
    title: str = Field(..., description="Suggested report title")
    description: str = Field("", description="Suggested report description")
    prompt: str = Field("", description="Prompt to use for generation")


class NLMReportSuggestionListResponse(BaseModel):
    object: str = "list"
    data: list[NLMReportSuggestionResponse] = Field(..., description="Suggested report formats")


class NLMArtifactDownloadUrlResponse(BaseModel):
    url: str | None = Field(None, description="Download URL (for media artifacts)")
    format: str | None = Field(None, description="Content format: pdf, pptx, markdown, csv, json, html")
    content: str | dict | list | None = Field(None, description="Inline content (for non-media artifacts)")


# === NotebookLM Notes ===

class NLMNoteCreateRequest(BaseModel):
    title: str = Field("New Note", description="Note title")
    content: str = Field("", description="Note content (markdown)")


class NLMNoteUpdateRequest(BaseModel):
    title: str = Field(..., description="New note title", min_length=1)
    content: str = Field(..., description="New note content (markdown)")


class NLMNoteResponse(BaseModel):
    id: str = Field(..., description="Note ID")
    notebook_id: str = Field(..., description="Notebook ID")
    title: str = Field("", description="Note title")
    content: str = Field("", description="Note content (markdown)")
    created_at: str | None = Field(None, description="Creation timestamp")


class NLMNoteListResponse(BaseModel):
    object: str = "list"
    data: list[NLMNoteResponse] = Field(..., description="List of notes")


# === NotebookLM Sources ===

class NLMSourceAddUrlRequest(BaseModel):
    url: str = Field(..., description="Source URL", min_length=1)
    wait: bool = Field(False, description="Wait for processing to complete")


class NLMSourceAddTextRequest(BaseModel):
    title: str = Field("Source", description="Source title")
    content: str = Field(..., description="Source content (markdown)", min_length=1)
    wait: bool = Field(False, description="Wait for processing to complete")
    idempotent: bool = Field(False, description="Skip if identical text already exists")


class NLMSourceAddDriveRequest(BaseModel):
    file_id: str = Field(..., description="Google Drive file ID", min_length=1)
    title: str = Field("Drive Source", description="Source title")
    mime_type: str = Field("application/vnd.google-apps.document", description="Drive file MIME type")
    wait: bool = Field(False, description="Wait for processing to complete")


class NLMSourceRenameRequest(BaseModel):
    title: str = Field(..., description="New source title", min_length=1)


class NLMSourceWaitRequest(BaseModel):
    timeout: float = Field(120.0, description="Max seconds to wait", gt=0)
    initial_interval: float = Field(1.0, description="Initial poll interval (seconds)", gt=0)
    max_interval: float = Field(10.0, description="Max poll interval (seconds)", gt=0)


class NLMSourceDetailResponse(BaseModel):
    id: str = Field(..., description="Source ID")
    title: str | None = Field(None, description="Source title")
    source_type: str | None = Field(None, description="Source type kind")
    url: str | None = Field(None, description="Source URL")
    status: int = Field(2, description="Status code: 1=processing, 2=ready, 3=error, 5=preparing")
    status_str: str = Field("ready", description="Human-readable status")
    created_at: str | None = Field(None, description="Creation timestamp")
    is_ready: bool = Field(True, description="Whether source content is ready")
    is_processing: bool = Field(False, description="Whether source is still being processed")
    is_error: bool = Field(False, description="Whether source is in error state")


class NLMSourceListResponse(BaseModel):
    object: str = "list"
    data: list[NLMSourceDetailResponse] = Field(..., description="List of sources")


class NLMSourceGuideResponse(BaseModel):
    source_id: str = Field(..., description="Source ID")
    summary: str = Field("", description="AI-generated summary")
    keywords: list[str] = Field(default_factory=list, description="Key topics/keywords")


class NLMSourceFulltextResponse(BaseModel):
    source_id: str = Field(..., description="Source ID")
    title: str = Field("", description="Source title")
    content: str = Field("", description="Full text content")
    char_count: int = Field(0, description="Character count")
    url: str | None = Field(None, description="Source URL")
    source_type: str | None = Field(None, description="Source type kind")


# === NotebookLM Chat ===

class NLMChatConfigureRequest(BaseModel):
    goal: str | None = Field(None, description="Chat persona: default, custom, learning_guide")
    response_length: str | None = Field(None, description="Response verbosity: default, longer, shorter")
    custom_prompt: str | None = Field(None, description="Custom instructions (required if goal=custom)")


class NLMChatModeRequest(BaseModel):
    mode: str = Field("default", description="Chat mode: default, learning_guide, concise, detailed")


class NLMChatSaveNoteRequest(BaseModel):
    title: str | None = Field(None, description="Note title (auto-derived from answer if omitted)")


class NLMChatReferenceResponse(BaseModel):
    source_id: str = Field("", description="Referenced source ID")
    citation_number: int | None = Field(None, description="Citation number")
    cited_text: str | None = Field(None, description="Cited text excerpt")
    start_char: int | None = Field(None, description="Start character position")
    end_char: int | None = Field(None, description="End character position")


class NLMChatTurnResponse(BaseModel):
    query: str = Field("", description="User question")
    answer: str = Field("", description="Model answer")
    turn_number: int = Field(0, description="Turn index")


class NLMChatHistoryResponse(BaseModel):
    conversation_id: str = Field(..., description="Conversation ID")
    turns: list[NLMChatTurnResponse] = Field(default_factory=list, description="Chat history turns")


# === NotebookLM Research ===

class NLMResearchStartRequest(BaseModel):
    query: str = Field(..., description="Research query", min_length=1)
    source: str = Field("web", description="Source: web or drive")
    mode: str = Field("fast", description="Research mode: fast or deep")


class NLMResearchStartResponse(BaseModel):
    task_id: str = Field("", description="Research task ID")
    report_id: str | None = Field(None, description="Report ID (if available)")
    notebook_id: str = Field("", description="Notebook ID")
    query: str = Field("", description="Research query")
    mode: str = Field("", description="Research mode")


class NLMResearchSourceResponse(BaseModel):
    url: str = Field("", description="Source URL")
    title: str = Field("", description="Source title")
    result_type: int = Field(1, description="Result type: 1=web, 2=drive, 5=report")
    research_task_id: str | None = Field(None, description="Research task ID (for report sources)")
    report_markdown: str = Field("", description="Report markdown (for report sources)")


class NLMResearchTaskResponse(BaseModel):
    task_id: str = Field(..., description="Research task ID")
    status: str = Field("in_progress", description="Status: in_progress, completed, failed, no_research, not_found")
    query: str = Field("", description="Research query")
    sources: list[NLMResearchSourceResponse] = Field(default_factory=list, description="Discovered sources")
    summary: str = Field("", description="Research summary")
    report: str = Field("", description="Full research report")
    subtasks: list["NLMResearchTaskResponse"] = Field(default_factory=list, description="Sub-tasks (deep research)")


class NLMResearchWaitRequest(BaseModel):
    timeout: float = Field(1800.0, description="Max seconds to wait", gt=0)
    interval: float = Field(5.0, description="Poll interval in seconds", gt=0)


class NLMResearchImportSource(BaseModel):
    url: str = Field(..., description="Source URL", min_length=1)
    title: str = Field("", description="Source title")


class NLMResearchImportRequest(BaseModel):
    sources: list[NLMResearchImportSource] = Field(..., description="Sources to import into notebook", min_length=1)


class NLMResearchImportResponse(BaseModel):
    imported: list[dict] = Field(default_factory=list, description="Imported sources with id and title")


# === NotebookLM Sharing ===

class NLMSharingUserResponse(BaseModel):
    email: str = Field("", description="User email")
    permission: int = Field(3, description="Permission: 1=owner, 2=editor, 3=viewer")
    display_name: str | None = Field(None, description="User display name")
    avatar_url: str | None = Field(None, description="Avatar URL")


class NLMShareStatusResponse(BaseModel):
    notebook_id: str = Field(..., description="Notebook ID")
    is_public: bool = Field(False, description="Whether public link sharing is enabled")
    access: int = Field(0, description="Access: 0=restricted, 1=anyone_with_link")
    view_level: int = Field(0, description="View level: 0=full_notebook, 1=chat_only")
    shared_users: list[NLMSharingUserResponse] = Field(default_factory=list, description="Shared users")
    share_url: str | None = Field(None, description="Public share URL")


class NLMSharingSetPublicRequest(BaseModel):
    public: bool = Field(True, description="Enable public link sharing")


class NLMSharingSetViewLevelRequest(BaseModel):
    level: int = Field(0, description="View level: 0=full_notebook, 1=chat_only")


class NLMSharingAddUserRequest(BaseModel):
    email: str = Field(..., description="User email address", min_length=1)
    permission: int = Field(3, description="Permission: 2=editor, 3=viewer")
    notify: bool = Field(True, description="Send email notification")
    welcome_message: str = Field("", description="Welcome message")


class NLMSharingUpdateUserRequest(BaseModel):
    email: str = Field(..., description="User email address", min_length=1)
    permission: int = Field(3, description="New permission: 2=editor, 3=viewer")


class NLMSharingRemoveUserRequest(BaseModel):
    email: str = Field(..., description="User email address to remove", min_length=1)


# === NotebookLM Settings ===

class NLMSetLanguageRequest(BaseModel):
    language: str = Field("en", description="Language code (e.g. en, zh_Hans, ja)", min_length=1)


class NLMAccountLimitsResponse(BaseModel):
    notebook_limit: int | None = Field(None, description="Max notebooks allowed")
    source_limit: int | None = Field(None, description="Max sources per notebook")


class NLMAccountTierResponse(BaseModel):
    tier: str | None = Field(None, description="Raw tier string")
    plan_name: str | None = Field(None, description="Friendly plan name")


# === NotebookLM Mind Maps ===

class NLMMindMapGenerateRequest(BaseModel):
    source_ids: list[str] | None = Field(None, description="Specific source IDs")
    kind: str = Field("interactive", description="Mind map kind: note_backed or interactive")
    language: str = Field("en", description="Language code")
    instructions: str | None = Field(None, description="Optional generation instructions")
    wait: bool = Field(True, description="Wait for completion before returning")


class NLMMindMapRenameRequest(BaseModel):
    title: str = Field(..., description="New title", min_length=1)
    kind: str | None = Field(None, description="Mind map kind (auto-detected if omitted)")


class NLMMindMapTreeResponse(BaseModel):
    name: str = Field("", description="Root node name")
    children: list = Field(default_factory=list, description="Child nodes")


class NLMMindMapResponse(BaseModel):
    id: str = Field(..., description="Mind map ID")
    notebook_id: str = Field(..., description="Notebook ID")
    title: str = Field("", description="Mind map title")
    kind: str = Field("interactive", description="Mind map kind")
    created_at: str | None = Field(None, description="Creation timestamp")
    tree: dict | None = Field(None, description="Node tree (for note-backed maps)")


class NLMMindMapListResponse(BaseModel):
    object: str = "list"
    data: list[NLMMindMapResponse] = Field(..., description="List of mind maps")
