"""Explicit provider registration; importing the package never probes a service."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .contracts import (
    AIProvider,
    AIProviderFailureError,
    AIProviderNotFoundError,
    ProviderDescriptor,
)
from .service import AIService


ProviderFactory = Callable[[Mapping[str, Any]], AIProvider]


@dataclass(frozen=True, slots=True)
class _Registration:
    descriptor: ProviderDescriptor
    factory: ProviderFactory


class ProviderRegistry:
    """In-memory factory registry for built-in and optional provider adapters."""

    def __init__(self) -> None:
        self._providers: dict[str, _Registration] = {}

    def register(self, descriptor: ProviderDescriptor, factory: ProviderFactory) -> None:
        if not isinstance(descriptor, ProviderDescriptor):
            raise TypeError("descriptor must be a ProviderDescriptor")
        if not callable(factory):
            raise TypeError("factory must be callable")
        if descriptor.provider_id in self._providers:
            raise ValueError(f"provider {descriptor.provider_id!r} is already registered")
        self._providers[descriptor.provider_id] = _Registration(descriptor, factory)

    def descriptors(self) -> tuple[ProviderDescriptor, ...]:
        return tuple(registration.descriptor for registration in self._providers.values())

    def create_service(
        self,
        provider_id: str,
        settings: Mapping[str, Any] | None = None,
    ) -> AIService:
        registration = self._providers.get(provider_id)
        if registration is None:
            raise AIProviderNotFoundError(f"No AI provider is registered as {provider_id!r}.")
        try:
            provider = registration.factory(dict(settings or {}))
        except Exception as exc:
            raise AIProviderFailureError(provider_id, type(exc).__name__) from None
        try:
            actual = getattr(provider, "descriptor", None)
        except Exception as exc:
            raise AIProviderFailureError(provider_id, type(exc).__name__) from None
        if actual != registration.descriptor:
            raise AIProviderFailureError(provider_id, "descriptor_mismatch")
        return AIService(provider)
