"""Optional, provider-neutral AI assistance for Ascent Calculus."""

from .contracts import (
    AIError,
    AIInvalidResponseError,
    AIModelNotSelectedError,
    AIModelUnavailableError,
    AIProvider,
    AIProviderFailureError,
    AIProviderNotFoundError,
    AIRequestCancelledError,
    AIRequestTimeoutError,
    AIResponse,
    AIUnavailableError,
    AIUnsupportedCapabilityError,
    CancellationToken,
    ChatMessage,
    ChatRequest,
    ModelInfo,
    OutputMode,
    ProviderCapability,
    ProviderDescriptor,
    ProviderLocality,
    ProviderReply,
)
from .registry import ProviderRegistry
from .service import AIService
from .ollama import OLLAMA_DESCRIPTOR, OllamaProvider, register_ollama_provider
from .provenance import (
    AI_REVIEW_FORMAT,
    AI_REVIEW_VERSION,
    create_assistant_review,
    validate_assistant_review,
)
from .settings import AIAssistantSettings, default_ai_settings_path, load_ai_settings, save_ai_settings

__all__ = [name for name in globals() if not name.startswith("_")]
