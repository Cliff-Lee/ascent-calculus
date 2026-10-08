"""Provider-independent validation and error handling for optional AI calls."""

from __future__ import annotations

import json
import math
from typing import Sequence

from .contracts import (
    AIError,
    AIInvalidResponseError,
    AIProvider,
    AIProviderFailureError,
    AIRequestCancelledError,
    AIRequestTimeoutError,
    AIResponse,
    AIUnavailableError,
    AIUnsupportedCapabilityError,
    CancellationToken,
    ChatRequest,
    ModelInfo,
    OutputMode,
    ProviderCapability,
    ProviderDescriptor,
    ProviderReply,
)


class AIService:
    """Small facade used by research features without coupling them to a vendor.

    A missing provider is an ordinary disconnected mode. No network or model
    process is started unless a caller explicitly supplies a provider.
    """

    def __init__(self, provider: AIProvider | None = None):
        if provider is not None and not isinstance(getattr(provider, "descriptor", None), ProviderDescriptor):
            raise TypeError("provider must expose a ProviderDescriptor")
        self._provider = provider

    @property
    def available(self) -> bool:
        return self._provider is not None

    @property
    def provider_id(self) -> str | None:
        return self._provider.descriptor.provider_id if self._provider else None

    def _require(self, capability: ProviderCapability) -> AIProvider:
        if self._provider is None:
            raise AIUnavailableError("AI assistance is not configured.")
        if capability not in self._provider.descriptor.capabilities:
            raise AIUnsupportedCapabilityError(
                f"Provider {self._provider.descriptor.provider_id!r} does not support {capability.value}."
            )
        return self._provider

    @staticmethod
    def _token(cancellation: CancellationToken | None) -> CancellationToken:
        token = cancellation or CancellationToken()
        token.raise_if_cancelled()
        return token

    def list_models(
        self,
        *,
        timeout_seconds: float = 5.0,
        cancellation: CancellationToken | None = None,
    ) -> tuple[ModelInfo, ...]:
        provider = self._require(ProviderCapability.MODEL_LIST)
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise ValueError("timeout_seconds must be a positive finite number")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive finite number")
        token = self._token(cancellation)
        try:
            models = tuple(provider.list_models(timeout_seconds=timeout_seconds, cancellation=token))
        except AIError:
            raise
        except TimeoutError:
            raise AIRequestTimeoutError("AI model discovery timed out.") from None
        except Exception as exc:
            raise AIProviderFailureError(provider.descriptor.provider_id, type(exc).__name__) from None
        token.raise_if_cancelled()
        if any(not isinstance(model, ModelInfo) for model in models):
            raise AIInvalidResponseError("Provider returned an invalid model list.")
        ids = [model.model_id for model in models]
        if len(ids) != len(set(ids)):
            raise AIInvalidResponseError("Provider returned duplicate model identifiers.")
        return models

    def chat(
        self,
        request: ChatRequest,
        *,
        cancellation: CancellationToken | None = None,
    ) -> AIResponse:
        if not isinstance(request, ChatRequest):
            raise TypeError("request must be a ChatRequest")
        provider = self._require(ProviderCapability.CHAT)
        if request.output_mode is OutputMode.JSON:
            self._require(ProviderCapability.STRUCTURED_OUTPUT)
        token = self._token(cancellation)
        try:
            reply = provider.chat(request, cancellation=token)
        except AIError:
            raise
        except TimeoutError:
            raise AIRequestTimeoutError("AI request timed out.") from None
        except Exception as exc:
            raise AIProviderFailureError(provider.descriptor.provider_id, type(exc).__name__) from None
        token.raise_if_cancelled()
        if not isinstance(reply, ProviderReply) or not isinstance(reply.text, str):
            raise AIInvalidResponseError("Provider returned an invalid chat response.")
        if reply.model is not None and not isinstance(reply.model, str):
            raise AIInvalidResponseError("Provider returned an invalid model identifier.")
        structured_data = None
        if request.output_mode is OutputMode.JSON:
            try:
                structured_data = json.loads(reply.text, parse_constant=_reject_json_constant)
            except (json.JSONDecodeError, ValueError) as exc:
                raise AIInvalidResponseError("Provider did not return valid JSON.") from None
        return AIResponse(
            provider_id=provider.descriptor.provider_id,
            model=reply.model or request.model,
            text=reply.text,
            structured_data=structured_data,
        )


def _reject_json_constant(value: str):
    raise ValueError(f"invalid JSON constant: {value}")
