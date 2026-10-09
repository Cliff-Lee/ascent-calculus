"""AM-AI1 contract tests; all use an offline fake provider."""

from __future__ import annotations

import unittest

from ac.ai import (
    AIInvalidResponseError,
    AIProviderFailureError,
    AIProviderNotFoundError,
    AIRequestCancelledError,
    AIRequestTimeoutError,
    AIService,
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
    ProviderRegistry,
    ProviderReply,
)


FULL_DESCRIPTOR = ProviderDescriptor(
    "fake-local",
    "Offline test provider",
    frozenset({ProviderCapability.CHAT, ProviderCapability.STRUCTURED_OUTPUT, ProviderCapability.MODEL_LIST}),
    ProviderLocality.LOCAL,
)


class FakeProvider:
    def __init__(self, reply="hello", *, error=None, cancel_during_call=False, descriptor=FULL_DESCRIPTOR):
        self._descriptor = descriptor
        self.reply = reply
        self.error = error
        self.cancel_during_call = cancel_during_call
        self.seen_request = None
        self.seen_cancellation = None
        self.seen_timeout = None

    @property
    def descriptor(self):
        return self._descriptor

    def list_models(self, *, timeout_seconds, cancellation):
        self.seen_timeout = timeout_seconds
        cancellation.raise_if_cancelled()
        return (ModelInfo("fake-1", "Fake Model"),)

    def chat(self, request, *, cancellation):
        self.seen_request = request
        self.seen_cancellation = cancellation
        cancellation.raise_if_cancelled()
        if self.cancel_during_call:
            cancellation.cancel()
        if self.error:
            raise self.error
        if isinstance(self.reply, BaseException):
            raise self.reply
        return ProviderReply(self.reply, request.model or "fake-1")


def request(**kwargs):
    return ChatRequest((ChatMessage("user", "Suggest a testable ascent-sequence question."),), **kwargs)


class AMAI1ProviderTests(unittest.TestCase):
    def test_disconnected_mode_is_inert_and_clear(self):
        service = AIService()
        self.assertFalse(service.available)
        with self.assertRaises(AIUnavailableError):
            service.chat(request())

    def test_registry_creates_provider_only_when_selected(self):
        registry = ProviderRegistry()
        registry.register(FULL_DESCRIPTOR, lambda settings: FakeProvider())
        self.assertEqual(registry.descriptors(), (FULL_DESCRIPTOR,))
        service = registry.create_service("fake-local", {"model": "fake-1"})
        self.assertTrue(service.available)
        self.assertEqual(service.chat(request()).provider_id, "fake-local")

    def test_registry_rejects_duplicate_and_unknown_ids(self):
        registry = ProviderRegistry()
        registry.register(FULL_DESCRIPTOR, lambda _settings: FakeProvider())
        with self.assertRaises(ValueError):
            registry.register(FULL_DESCRIPTOR, lambda _settings: FakeProvider())
        with self.assertRaises(AIProviderNotFoundError):
            registry.create_service("missing")

    def test_model_discovery_is_capability_gated_and_timeout_is_passed(self):
        provider = FakeProvider()
        models = AIService(provider).list_models(timeout_seconds=2.5)
        self.assertEqual(models[0].model_id, "fake-1")
        self.assertEqual(provider.seen_timeout, 2.5)
        chat_only = ProviderDescriptor("chat-only", "Chat only", frozenset({ProviderCapability.CHAT}))
        with self.assertRaises(AIUnsupportedCapabilityError):
            AIService(FakeProvider(descriptor=chat_only)).list_models()
        for timeout in (0, float("inf"), float("nan")):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                AIService(provider).list_models(timeout_seconds=timeout)

    def test_structured_output_is_parsed_but_stays_unverified(self):
        provider = FakeProvider('{"claim":"candidate","tested_bound":5}')
        response = AIService(provider).chat(request(output_mode=OutputMode.JSON, json_schema={"type": "object"}))
        self.assertEqual(response.structured_data["tested_bound"], 5)
        self.assertEqual(response.verification_status, "unverified")
        self.assertEqual(provider.seen_request.json_schema, {"type": "object"})

    def test_invalid_structured_output_is_rejected(self):
        with self.assertRaises(AIInvalidResponseError):
            AIService(FakeProvider("not json")).chat(request(output_mode=OutputMode.JSON))
        chat_only = ProviderDescriptor("chat-only", "Chat only", frozenset({ProviderCapability.CHAT}))
        with self.assertRaises(AIUnsupportedCapabilityError):
            AIService(FakeProvider(descriptor=chat_only)).chat(request(output_mode=OutputMode.JSON))

    def test_service_rejects_invalid_provider_and_response_contracts(self):
        with self.assertRaises(TypeError):
            AIService(object())
        with self.assertRaises(AIInvalidResponseError):
            AIService(FakeProvider(ProviderReply("ok", model=17))).chat(request())

    def test_cancellation_is_checked_before_and_after_provider_call(self):
        cancelled = CancellationToken()
        cancelled.cancel()
        with self.assertRaises(AIRequestCancelledError):
            AIService(FakeProvider()).chat(request(), cancellation=cancelled)
        provider = FakeProvider(cancel_during_call=True)
        with self.assertRaises(AIRequestCancelledError):
            AIService(provider).chat(request())
        self.assertIs(provider.seen_cancellation.cancelled, True)

    def test_timeouts_and_unexpected_errors_are_normalized_without_raw_text(self):
        with self.assertRaises(AIRequestTimeoutError):
            AIService(FakeProvider(TimeoutError("secret endpoint token"))).chat(request())
        with self.assertRaises(AIProviderFailureError) as raised:
            AIService(FakeProvider(RuntimeError("secret endpoint token"))).chat(request())
        self.assertNotIn("secret endpoint token", str(raised.exception))

    def test_request_validation_rejects_invalid_budgets_and_schema_modes(self):
        with self.assertRaises(ValueError):
            request(timeout_seconds=0)
        with self.assertRaises(ValueError):
            request(max_tokens=0)
        with self.assertRaises(ValueError):
            request(json_schema={"type": "object"})
        with self.assertRaises(ValueError):
            ChatMessage("developer", "unsupported role")


if __name__ == "__main__":
    unittest.main()
