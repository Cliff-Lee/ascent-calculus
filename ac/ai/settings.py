"""Opt-in local-endpoint Ollama settings stored without credentials."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any

from .ollama import DEFAULT_OLLAMA_URL, OllamaProvider


SETTINGS_FORMAT = "ascent-calculus-ai-settings"
SETTINGS_VERSION = 1


def default_ai_settings_path() -> Path:
    return Path.home() / ".ascent-calculus" / "ai-settings.json"


@dataclass(frozen=True, slots=True)
class AIAssistantSettings:
    enabled: bool = False
    endpoint: str = DEFAULT_OLLAMA_URL
    model: str = ""
    timeout_seconds: float = 180.0

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be true or false")
        if not isinstance(self.model, str):
            raise ValueError("model must be text")
        # Constructor validation also enforces HTTP loopback-only routing.
        OllamaProvider(self.endpoint, default_model=self.model or None)
        if self.enabled and not self.model.strip():
            raise ValueError("choose an installed Ollama model before enabling AI")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)):
            raise ValueError("timeout_seconds must be a finite number from 1 to 3600")
        if not math.isfinite(self.timeout_seconds) or not 1 <= self.timeout_seconds <= 3600:
            raise ValueError("timeout_seconds must be a finite number from 1 to 3600")


def load_ai_settings(path: str | os.PathLike[str] | None = None) -> AIAssistantSettings:
    target = Path(path) if path is not None else default_ai_settings_path()
    if not target.exists():
        return AIAssistantSettings()
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError
        if document.get("format") != SETTINGS_FORMAT or document.get("version") != SETTINGS_VERSION:
            raise ValueError
        return AIAssistantSettings(
            enabled=document.get("enabled", False),
            endpoint=document.get("endpoint", DEFAULT_OLLAMA_URL),
            model=document.get("model", ""),
            timeout_seconds=document.get("timeout_seconds", 180.0),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ValueError("AI settings could not be read; open the local AI settings to replace them.") from exc


def save_ai_settings(
    settings: AIAssistantSettings,
    path: str | os.PathLike[str] | None = None,
) -> Path:
    if not isinstance(settings, AIAssistantSettings):
        raise TypeError("settings must be AIAssistantSettings")
    target = Path(path) if path is not None else default_ai_settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    document: dict[str, Any] = {
        "format": SETTINGS_FORMAT,
        "version": SETTINGS_VERSION,
        "enabled": settings.enabled,
        "endpoint": settings.endpoint,
        "model": settings.model,
        "timeout_seconds": settings.timeout_seconds,
    }
    fd, temporary_path = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    temporary = Path(temporary_path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
        os.replace(temporary, target)
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
        return target
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
