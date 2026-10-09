"""Ollama adapter checks with mocked HTTP responses; never needs Ollama/network."""

from __future__ import annotations

import io
import json
import queue
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request

from ac.ai import (
    AIModelNotSelectedError,
    AIModelUnavailableError,
    AIRequestCancelledError,
    AIService,
    CancellationToken,
    ChatMessage,
    ChatRequest,
    OllamaProvider,
    OutputMode,
    ProviderRegistry,
    ProviderLocality,
    register_ollama_provider,
)
from ac.ai.ollama import _NoRedirectHandler, _open_local_url


class _InterruptibleSocket:
    def __init__(self, response):
        self.response = response

    def shutdown(self, _how):
        self.response.interrupted.set()


class FakeResponse:
    def __init__(self, value, *, block_after_lines=False):
        self.body = value if isinstance(value, bytes) else None
        self.lines = list(value) if not isinstance(value, bytes) else []
        self.block_after_lines = block_after_lines
        self.interrupted = threading.Event()
        self.read_waiting = threading.Event()
        self.closed = False
        self.fp = SimpleNamespace(raw=SimpleNamespace(_sock=_InterruptibleSocket(self)))

    def read(self, _size=-1):
        return self.body or b""

    def readline(self):
        if self.lines:
            return self.lines.pop(0)
        if self.block_after_lines:
            self.read_waiting.set()
            if self.interrupted.wait(2):
                raise OSError("mock socket shutdown")
        return b""

    def close(self):
        self.closed = True


def _line(content, *, model="qwen3.5:9b", done=False):
    return (json.dumps({"model": model, "message": {"role": "assistant", "content": content}, "done": done}) + "\n").encode()


class AMAI2OllamaTests(unittest.TestCase):
    endpoint = "http://127.0.0.1:11434"

    def service(self, *, default_model=None):
        registry = ProviderRegistry()
        register_ollama_provider(registry)
        return registry.create_service(
            "ollama-loopback",
            {"endpoint": self.endpoint, "default_model": default_model},
        )

    def test_default_provider_is_local_and_does_not_probe_until_called(self):
        service = self.service(default_model="qwen3.5:9b")
        self.assertEqual(service.provider_id, "ollama-loopback")
        with patch("ac.ai.ollama._open_local_url") as open_url:
            self.assertFalse(open_url.called)
            response = FakeResponse(b'{"models":[{"name":"qwen3.5:9b","model":"qwen3.5:9b"},{"name":"gpt-oss:20b-cloud","model":"gpt-oss:20b-cloud","remote_model":"gpt-oss:20b"}]}')
            open_url.return_value = response
            models = service.list_models()
        self.assertEqual(models[0].model_id, "qwen3.5:9b")
        self.assertIs(models[0].inference_locality, ProviderLocality.LOCAL)
        self.assertIs(models[1].inference_locality, ProviderLocality.REMOTE)
        self.assertTrue(response.closed)
        request = open_url.call_args.args[0]
        self.assertEqual(request.full_url, f"{self.endpoint}/api/tags")
        self.assertEqual(request.get_method(), "GET")

    def test_chat_stream_is_joined_and_schema_options_are_forwarded(self):
        service = self.service(default_model="qwen3.5:9b")
        schema = {
            "type": "object",
            "properties": {"candidate_count": {"type": "integer"}},
            "required": ["candidate_count"],
        }
        chat_request = ChatRequest(
            (ChatMessage("system", "Suggest bounded experiments."), ChatMessage("user", "Search this family.")),
            output_mode=OutputMode.JSON,
            json_schema=schema,
            temperature=0,
            max_tokens=120,
        )
        response = FakeResponse([_line('{"candidate_count":'), _line("3}", done=True)])
        with patch("ac.ai.ollama._open_local_url", return_value=response) as open_url:
            result = service.chat(chat_request)
        sent_request = open_url.call_args.args[0]
        sent = json.loads(sent_request.data)
        self.assertEqual(result.structured_data, {"candidate_count": 3})
        self.assertEqual(result.model, "qwen3.5:9b")
        self.assertTrue(sent["stream"])
        self.assertEqual(sent["format"], schema)
        self.assertEqual(sent["options"], {"temperature": 0, "num_predict": 120})
        self.assertEqual([item["role"] for item in sent["messages"]], ["system", "user"])
        self.assertEqual(sent_request.full_url, f"{self.endpoint}/api/chat")
        self.assertEqual(sent_request.get_method(), "POST")
        self.assertTrue(response.closed)

    def test_missing_model_is_a_clear_error(self):
        with self.assertRaises(AIModelNotSelectedError):
            self.service().chat(ChatRequest((ChatMessage("user", "hello"),)))
        body = io.BytesIO(b'{"error":"model \'missing-model\' not found"}')
        http_error = HTTPError(f"{self.endpoint}/api/chat", 404, "Not Found", {}, body)
        with patch("ac.ai.ollama._open_local_url", side_effect=http_error):
            with self.assertRaises(AIModelUnavailableError):
                self.service().chat(ChatRequest((ChatMessage("user", "hello"),), model="missing-model"))

    def test_endpoint_is_restricted_to_http_loopback(self):
        for endpoint in (
            "https://localhost:11434",
            "http://example.com:11434",
            "http://user:password@localhost:11434",
            "http://localhost:11434/base-path",
        ):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                OllamaProvider(endpoint)
        self.assertEqual(OllamaProvider("http://[::1]:11434").base_url, "http://[::1]:11434")

    def test_transport_bypasses_proxies_and_refuses_redirects(self):
        request = Request("http://localhost:11434/api/tags")
        with patch("ac.ai.ollama.build_opener") as build_opener:
            opener = Mock()
            build_opener.return_value = opener
            _open_local_url(request, 3)
        handlers = build_opener.call_args.args
        self.assertIsInstance(handlers[0], ProxyHandler)
        self.assertEqual(handlers[0].proxies, {})
        self.assertIsInstance(handlers[1], _NoRedirectHandler)
        self.assertIsNone(
            handlers[1].redirect_request(request, None, 302, "Found", {}, "http://example.org/steal")
        )

    def test_cancel_interrupts_a_live_stream(self):
        token = CancellationToken()
        results: queue.Queue[BaseException | None] = queue.Queue()
        response = FakeResponse([_line("partial", model="cancel-test")], block_after_lines=True)
        chat_request = ChatRequest((ChatMessage("user", "wait"),), model="cancel-test", timeout_seconds=5)

        def call_provider():
            try:
                with patch("ac.ai.ollama._open_local_url", return_value=response):
                    self.service().chat(chat_request, cancellation=token)
            except BaseException as exc:
                results.put(exc)
            else:
                results.put(None)

        worker = threading.Thread(target=call_provider, daemon=True)
        worker.start()
        self.assertTrue(response.read_waiting.wait(2), "provider did not begin reading the next stream chunk")
        token.cancel()
        worker.join(timeout=2)
        self.assertFalse(worker.is_alive(), "cancel did not release the active response")
        self.assertIsInstance(results.get_nowait(), AIRequestCancelledError)
        self.assertTrue(response.closed)


if __name__ == "__main__":
    unittest.main()
