"""Optional loopback Ollama HTTP adapter using only the Python standard library."""

from __future__ import annotations

import ipaddress
import json
import math
import re
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from collections.abc import Mapping
from typing import Any

from .contracts import (
    AIError,
    AIInvalidResponseError,
    AIModelNotSelectedError,
    AIModelUnavailableError,
    AIProviderFailureError,
    AIRequestCancelledError,
    AIRequestTimeoutError,
    AIProvider,
    CancellationToken,
    ChatRequest,
    ModelInfo,
    OutputMode,
    ProviderCapability,
    ProviderDescriptor,
    ProviderLocality,
    ProviderReply,
)
from .registry import ProviderRegistry


DEFAULT_OLLAMA_URL = "http://localhost:11434"
OLLAMA_DESCRIPTOR = ProviderDescriptor(
    provider_id="ollama-loopback",
    display_name="Ollama API (loopback)",
    capabilities=frozenset(
        {
            ProviderCapability.CHAT,
            ProviderCapability.STRUCTURED_OUTPUT,
            ProviderCapability.MODEL_LIST,
        }
    ),
    locality=ProviderLocality.LOCAL,
    description="Connects to the local Ollama API; inference may be local or offloaded depending on the selected model.",
)


def _normalize_local_url(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Ollama endpoint must be a local HTTP URL")
    parsed = urlsplit(value.strip())
    if parsed.scheme != "http" or parsed.username or parsed.password:
        raise ValueError("Ollama endpoint must use local HTTP without credentials")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("Ollama endpoint must be an origin such as http://localhost:11434")
    host = (parsed.hostname or "").lower()
    is_loopback = host == "localhost"
    if not is_loopback:
        try:
            is_loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            is_loopback = False
    if not is_loopback:
        raise ValueError("Ollama endpoint must resolve to localhost or a loopback IP")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Ollama endpoint has an invalid port") from exc
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Ollama endpoint has an invalid port")
    return f"http://{parsed.netloc}".rstrip("/")


def _likely_cloud_model(model_id: str) -> bool:
    return re.search(r"(?:[:_-])cloud(?:$|[:_-])", model_id, flags=re.IGNORECASE) is not None


def _as_object(raw: bytes, *, operation: str) -> dict[str, Any]:
    try:
        result = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise AIInvalidResponseError(f"Ollama returned invalid JSON for {operation}.") from None
    if not isinstance(result, dict):
        raise AIInvalidResponseError(f"Ollama returned an invalid {operation} response.")
    return result


def _interrupt_response(response: Any) -> None:
    """Shut down the socket without contending with a reader's buffered-file lock."""
    try:
        socket_file = response.fp
        sock = socket_file.raw._sock
        sock.shutdown(socket.SHUT_RDWR)
    except Exception:
        # The caller also checks the cancellation event after every read and
        # closes the response in its own thread's finally block.
        pass


def _set_read_timeout(response: Any, timeout_seconds: float) -> None:
    try:
        response.fp.raw._sock.settimeout(timeout_seconds)
    except Exception:
        # A test double or alternate urllib implementation may not expose the
        # underlying socket. urlopen's original timeout still applies there.
        pass


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, _request, _response, _code, _message, _headers, _newurl):
        # Never forward local research prompts or responses to a redirect host.
        return None


def _open_local_url(request: Request, timeout: float):
    opener = build_opener(ProxyHandler({}), _NoRedirectHandler())
    return opener.open(request, timeout=timeout)


class OllamaProvider:
    """Local-endpoint provider; model inference locality depends on Ollama's model."""

    def __init__(self, base_url: str = DEFAULT_OLLAMA_URL, default_model: str | None = None):
        self.base_url = _normalize_local_url(base_url)
        if default_model is not None and (not isinstance(default_model, str) or not default_model.strip()):
            raise ValueError("default_model must be non-empty when provided")
        self.default_model = default_model

    @property
    def descriptor(self) -> ProviderDescriptor:
        return OLLAMA_DESCRIPTOR

    def list_models(
        self,
        *,
        timeout_seconds: float,
        cancellation: CancellationToken,
    ) -> tuple[ModelInfo, ...]:
        timeout = _validate_timeout(timeout_seconds)
        cancellation.raise_if_cancelled()
        request = Request(
            f"{self.base_url}/api/tags",
            headers={"Accept": "application/json"},
            method="GET",
        )
        deadline = time.monotonic() + timeout
        response = self._open(request, timeout, cancellation, operation="model discovery")
        unregister = cancellation.add_cancel_callback(lambda: _interrupt_response(response))
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AIRequestTimeoutError("Ollama model discovery timed out.")
            _set_read_timeout(response, remaining)
            raw = response.read()
        except Exception as exc:
            if cancellation.cancelled:
                raise AIRequestCancelledError("AI request cancelled.") from None
            if isinstance(exc, (TimeoutError, socket.timeout)):
                raise AIRequestTimeoutError("Ollama model discovery timed out.") from None
            raise AIProviderFailureError(OLLAMA_DESCRIPTOR.provider_id, type(exc).__name__) from None
        finally:
            unregister()
            response.close()
        cancellation.raise_if_cancelled()
        payload = _as_object(raw, operation="model discovery")
        models = payload.get("models")
        if not isinstance(models, list):
            raise AIInvalidResponseError("Ollama model discovery response has no model list.")
        output: list[ModelInfo] = []
        for item in models:
            if not isinstance(item, dict):
                raise AIInvalidResponseError("Ollama returned an invalid model entry.")
            model_id = item.get("model") or item.get("name")
            display_name = item.get("name") or model_id
            if not isinstance(model_id, str) or not model_id.strip():
                raise AIInvalidResponseError("Ollama returned a model without a name.")
            remote_model = item.get("remote_model")
            locality = ProviderLocality.REMOTE if remote_model or _likely_cloud_model(model_id) else ProviderLocality.LOCAL
            details = f"Remote model: {remote_model}" if remote_model else None
            output.append(ModelInfo(model_id=model_id, display_name=display_name, details=details, inference_locality=locality))
        return tuple(output)

    def chat(self, request: ChatRequest, *, cancellation: CancellationToken) -> ProviderReply:
        model = request.model or self.default_model
        if not model:
            raise AIModelNotSelectedError("Select an installed Ollama model before requesting AI assistance.")
        cancellation.raise_if_cancelled()
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": message.role, "content": message.content} for message in request.messages],
            "stream": True,
        }
        options: dict[str, Any] = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens
        if options:
            payload["options"] = options
        if request.output_mode is OutputMode.JSON:
            payload["format"] = dict(request.json_schema) if request.json_schema is not None else "json"
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        http_request = Request(
            f"{self.base_url}/api/chat",
            data=encoded,
            headers={"Accept": "application/x-ndjson", "Content-Type": "application/json"},
            method="POST",
        )
        timeout = float(request.timeout_seconds)
        deadline = time.monotonic() + timeout
        response = self._open(http_request, timeout, cancellation, operation="chat", model=model)
        unregister = cancellation.add_cancel_callback(lambda: _interrupt_response(response))
        chunks: list[str] = []
        response_model: str | None = None
        finished = False
        try:
            while True:
                cancellation.raise_if_cancelled()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AIRequestTimeoutError("Ollama chat request timed out.")
                _set_read_timeout(response, remaining)
                line = response.readline()
                if not line:
                    break
                entry = _as_object(line, operation="chat stream")
                error_text = entry.get("error")
                if error_text:
                    normalized_error = str(error_text).lower()
                    if "model" in normalized_error and "not found" in normalized_error:
                        raise AIModelUnavailableError(f"Ollama does not have model {model!r} installed.")
                    raise AIProviderFailureError(OLLAMA_DESCRIPTOR.provider_id, "model_error")
                message = entry.get("message")
                if not isinstance(message, dict):
                    raise AIInvalidResponseError("Ollama chat response has no message object.")
                content = message.get("content", "")
                if not isinstance(content, str):
                    raise AIInvalidResponseError("Ollama returned non-text message content.")
                chunks.append(content)
                reported_model = entry.get("model")
                if reported_model is not None and not isinstance(reported_model, str):
                    raise AIInvalidResponseError("Ollama returned an invalid model identifier.")
                response_model = reported_model or response_model
                if entry.get("done") is True:
                    finished = True
                    break
        except AIError:
            raise
        except Exception as exc:
            if cancellation.cancelled:
                raise AIRequestCancelledError("AI request cancelled.") from None
            if isinstance(exc, (TimeoutError, socket.timeout)):
                raise AIRequestTimeoutError("Ollama chat request timed out.") from None
            raise AIProviderFailureError(OLLAMA_DESCRIPTOR.provider_id, type(exc).__name__) from None
        finally:
            unregister()
            response.close()
        cancellation.raise_if_cancelled()
        if not finished:
            raise AIInvalidResponseError("Ollama chat stream ended before its completion marker.")
        return ProviderReply(text="".join(chunks), model=response_model or model)

    @staticmethod
    def _open(request: Request, timeout: float, cancellation: CancellationToken, *, operation: str, model: str | None = None):
        cancellation.raise_if_cancelled()
        try:
            return _open_local_url(request, timeout)
        except HTTPError as exc:
            error_detail = ""
            try:
                error_body = json.loads(exc.read(8192))
                if isinstance(error_body, dict):
                    error_detail = str(error_body.get("error", "")).lower()
            except Exception:
                pass
            if exc.code == 404 and model and "model" in error_detail and "not found" in error_detail:
                raise AIModelUnavailableError(f"Ollama does not have model {model!r} installed.") from None
            raise AIProviderFailureError(OLLAMA_DESCRIPTOR.provider_id, f"http_{exc.code}") from None
        except (TimeoutError, socket.timeout):
            if cancellation.cancelled:
                raise AIRequestCancelledError("AI request cancelled.") from None
            raise AIRequestTimeoutError(f"Ollama {operation} timed out.") from None
        except URLError as exc:
            if cancellation.cancelled:
                raise AIRequestCancelledError("AI request cancelled.") from None
            reason = exc.reason
            if isinstance(reason, (TimeoutError, socket.timeout)):
                raise AIRequestTimeoutError(f"Ollama {operation} timed out.") from None
            if isinstance(reason, ConnectionRefusedError):
                diagnostic = "connection_refused"
            else:
                diagnostic = type(reason).__name__
            raise AIProviderFailureError(OLLAMA_DESCRIPTOR.provider_id, diagnostic) from None
        except OSError as exc:
            if cancellation.cancelled:
                raise AIRequestCancelledError("AI request cancelled.") from None
            raise AIProviderFailureError(OLLAMA_DESCRIPTOR.provider_id, type(exc).__name__) from None


def _validate_timeout(timeout_seconds: float) -> float:
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
        raise ValueError("timeout_seconds must be a positive finite number")
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be a positive finite number")
    return float(timeout_seconds)


def register_ollama_provider(registry: ProviderRegistry) -> None:
    """Register the adapter factory without probing or contacting Ollama."""
    if not isinstance(registry, ProviderRegistry):
        raise TypeError("registry must be a ProviderRegistry")

    def factory(settings: Mapping[str, Any]) -> AIProvider:
        endpoint = settings.get("endpoint", DEFAULT_OLLAMA_URL)
        default_model = settings.get("default_model")
        return OllamaProvider(base_url=endpoint, default_model=default_model)

    registry.register(OLLAMA_DESCRIPTOR, factory)
