"""Provider-neutral contracts for optional AI assistance.

AI output is advisory. It is never a verification result and must be checked
by the deterministic Ascent Calculus engine before it is treated as evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import math
import re
import threading
from typing import Any, Callable, Literal, Mapping, Protocol, Sequence, runtime_checkable


class ProviderCapability(str, Enum):
    CHAT = "chat"
    STRUCTURED_OUTPUT = "structured_output"
    MODEL_LIST = "model_list"


class ProviderLocality(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"
    UNKNOWN = "unknown"


class OutputMode(str, Enum):
    TEXT = "text"
    JSON = "json"


class AIError(RuntimeError):
    """Base class for safe, user-presentable AI integration errors."""


class AIUnavailableError(AIError):
    """Raised when AI assistance is disabled or no provider is configured."""


class AIProviderNotFoundError(AIError):
    """Raised when a provider id is not registered."""


class AIModelNotSelectedError(AIError):
    """Raised when a chat call has no explicit or configured model."""


class AIModelUnavailableError(AIError):
    """Raised when the selected provider does not have the requested model."""


class AIUnsupportedCapabilityError(AIError):
    """Raised when a provider does not implement a requested capability."""


class AIRequestCancelledError(AIError):
    """Raised when a caller cancels an AI request."""


class AIRequestTimeoutError(AIError):
    """Raised when a provider does not finish within the request timeout."""


class AIInvalidResponseError(AIError):
    """Raised when a provider returns data outside the agreed response shape."""


class AIProviderFailureError(AIError):
    """Safe provider failure; raw exception text is intentionally not exposed."""

    def __init__(self, provider_id: str, diagnostic_type: str = "provider_error"):
        self.provider_id = provider_id
        self.diagnostic_type = diagnostic_type
        super().__init__(f"AI provider {provider_id!r} failed ({diagnostic_type}).")


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    provider_id: str
    display_name: str
    capabilities: frozenset[ProviderCapability]
    locality: ProviderLocality = ProviderLocality.UNKNOWN
    description: str = ""

    def __post_init__(self) -> None:
        if re.fullmatch(r"[a-z][a-z0-9._-]{0,63}", self.provider_id or "") is None:
            raise ValueError("provider_id must be a lowercase identifier")
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValueError("display_name must be non-empty")
        try:
            capabilities = frozenset(ProviderCapability(item) for item in self.capabilities)
            locality = ProviderLocality(self.locality)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid provider capability or locality") from exc
        if ProviderCapability.CHAT not in capabilities:
            raise ValueError("providers must declare chat capability")
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "locality", locality)


@dataclass(frozen=True, slots=True)
class ModelInfo:
    model_id: str
    display_name: str | None = None
    details: str | None = None
    inference_locality: ProviderLocality = ProviderLocality.UNKNOWN

    def __post_init__(self) -> None:
        if not isinstance(self.model_id, str) or not self.model_id.strip():
            raise ValueError("model_id must be non-empty")
        try:
            object.__setattr__(self, "inference_locality", ProviderLocality(self.inference_locality))
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid model inference locality") from exc


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str

    def __post_init__(self) -> None:
        if not isinstance(self.role, str) or self.role not in {"system", "user", "assistant"}:
            raise ValueError("message role must be system, user, or assistant")
        if not isinstance(self.content, str):
            raise TypeError("message content must be text")


@dataclass(frozen=True, slots=True)
class ChatRequest:
    messages: tuple[ChatMessage, ...]
    model: str | None = None
    timeout_seconds: float = 60.0
    temperature: float | None = None
    max_tokens: int | None = None
    output_mode: OutputMode = OutputMode.TEXT
    json_schema: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        messages = tuple(self.messages)
        if not messages or any(not isinstance(item, ChatMessage) for item in messages):
            raise ValueError("messages must contain at least one ChatMessage")
        object.__setattr__(self, "messages", messages)
        if self.model is not None and (not isinstance(self.model, str) or not self.model.strip()):
            raise ValueError("model must be non-empty when provided")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)):
            raise ValueError("timeout_seconds must be a positive finite number")
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive finite number")
        if self.temperature is not None:
            if isinstance(self.temperature, bool) or not isinstance(self.temperature, (int, float)):
                raise ValueError("temperature must be finite and between 0 and 2")
            if not math.isfinite(self.temperature) or not 0 <= self.temperature <= 2:
                raise ValueError("temperature must be finite and between 0 and 2")
        if self.max_tokens is not None and (
            isinstance(self.max_tokens, bool)
            or not isinstance(self.max_tokens, int)
            or self.max_tokens < 1
        ):
            raise ValueError("max_tokens must be a positive integer")
        try:
            output_mode = OutputMode(self.output_mode)
        except (TypeError, ValueError) as exc:
            raise ValueError("output_mode must be text or json") from exc
        object.__setattr__(self, "output_mode", output_mode)
        if self.json_schema is not None:
            if output_mode is not OutputMode.JSON:
                raise ValueError("json_schema requires JSON output mode")
            if not isinstance(self.json_schema, Mapping):
                raise ValueError("json_schema must be a JSON object")
            try:
                encoded = json.dumps(dict(self.json_schema), allow_nan=False)
                schema_copy = json.loads(encoded)
            except (TypeError, ValueError) as exc:
                raise ValueError("json_schema must contain JSON-compatible values") from exc
            object.__setattr__(self, "json_schema", schema_copy)


@dataclass(frozen=True, slots=True)
class ProviderReply:
    text: str
    model: str | None = None


@dataclass(frozen=True, slots=True)
class AIResponse:
    provider_id: str
    model: str | None
    text: str
    structured_data: Any = None
    verification_status: Literal["unverified"] = "unverified"


class CancellationToken:
    """Thread-safe cooperative cancellation shared by the UI and provider."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._callbacks: dict[int, Callable[[], None]] = {}
        self._next_callback_id = 0

    def cancel(self) -> None:
        with self._lock:
            if self._event.is_set():
                return
            self._event.set()
            callbacks = tuple(self._callbacks.values())
            self._callbacks.clear()
        for callback in callbacks:
            try:
                callback()
            except Exception:
                # Cancellation remains reliable even if one adapter's cleanup
                # hook fails; the adapter will observe the event separately.
                pass

    def add_cancel_callback(self, callback: Callable[[], None]) -> Callable[[], None]:
        """Run callback once cancellation occurs; return an unregister function."""
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            callback_id = self._next_callback_id
            self._next_callback_id += 1
            already_cancelled = self._event.is_set()
            if not already_cancelled:
                self._callbacks[callback_id] = callback
        if already_cancelled:
            callback()

        def unregister() -> None:
            with self._lock:
                self._callbacks.pop(callback_id, None)

        return unregister

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise AIRequestCancelledError("AI request cancelled.")


@runtime_checkable
class AIProvider(Protocol):
    @property
    def descriptor(self) -> ProviderDescriptor: ...

    def list_models(
        self,
        *,
        timeout_seconds: float,
        cancellation: CancellationToken,
    ) -> Sequence[ModelInfo]: ...

    def chat(
        self,
        request: ChatRequest,
        *,
        cancellation: CancellationToken,
    ) -> ProviderReply: ...
