"""Small per-user store for saved experiments and the current research draft."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


MAX_STATE_BYTES = 1_000_000
MAX_SAVED_EXPERIMENTS = 30


def state_path() -> Path:
    """Return the platform-appropriate user data path (or a test override)."""
    override = os.environ.get("ASCENT_ENGINE_DATA_DIR")
    if override:
        root = Path(override).expanduser()
    elif os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "AscentEngine"
    elif __import__("sys").platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / "AscentEngine"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "ascent-engine"
    return root / "research-state.json"


def read_state() -> dict:
    path = state_path()
    try:
        if path.stat().st_size > MAX_STATE_BYTES:
            return {"draft": {}, "saved": []}
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"draft": {}, "saved": []}
    if not isinstance(value, dict):
        return {"draft": {}, "saved": []}
    return {
        "draft": value.get("draft", {}) if isinstance(value.get("draft", {}), dict) else {},
        "saved": value.get("saved", []) if isinstance(value.get("saved", []), list) else [],
    }


def write_state(value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Research state must be a JSON object")
    draft = value.get("draft", {})
    saved = value.get("saved", [])
    if not isinstance(draft, dict) or not isinstance(saved, list):
        raise ValueError("Research state needs a draft object and a saved-tests list")
    if len(saved) > MAX_SAVED_EXPERIMENTS:
        raise ValueError(f"Keep at most {MAX_SAVED_EXPERIMENTS} saved tests")
    if any(not isinstance(item, dict) or not isinstance(item.get("specification"), dict) for item in saved):
        raise ValueError("Each saved test must include an experiment specification")
    if any(not isinstance(k, str) or not isinstance(v, str) or len(k) > 80 or len(v) > 20_000 for k, v in draft.items()):
        raise ValueError("Draft fields must be short text values")
    encoded = json.dumps({"draft": draft, "saved": saved}, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_STATE_BYTES:
        raise ValueError("Research state is too large to save")

    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix="research-state-", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    temp_path.replace(path)
    return {"draft": draft, "saved": saved}
