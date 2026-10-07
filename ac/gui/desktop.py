"""Launch the AC workbench in a native desktop window.

The workbench UI talks to the Python engine through a private local HTTP API.
This launcher starts that API in-process and records each native-window startup
stage so a packaged app that exits early leaves useful diagnostics.
"""
from __future__ import annotations

import atexit
import argparse
import faulthandler
import json
import os
import platform
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread
from urllib.request import urlopen

# This module is also used as the PyInstaller entry script.
from ac.gui.server import Handler

_LOG_STREAM = None
_LOG_LOCK = threading.Lock()
_EXIT_HOOK_INSTALLED = False


def _log_path() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "AscentCalculus" / "startup.log"
    return Path.home() / ".ascent-calculus" / "startup.log"


def _log(event: str, **details) -> None:
    stream = _LOG_STREAM
    if stream is None:
        return
    record = {
        "time": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **details,
    }
    try:
        with _LOG_LOCK:
            stream.write(json.dumps(record, default=str, sort_keys=True) + "\n")
            stream.flush()
    except Exception:
        pass


def _finish_log() -> None:
    global _LOG_STREAM
    _log("process_exit")
    stream = _LOG_STREAM
    if stream is not None:
        try:
            stream.flush()
            stream.close()
        except Exception:
            pass
        _LOG_STREAM = None


def _open_startup_log() -> Path | None:
    global _LOG_STREAM, _EXIT_HOOK_INSTALLED
    path = _log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _LOG_STREAM = path.open("a", encoding="utf-8", buffering=1)
        faulthandler.enable(_LOG_STREAM, all_threads=True)
        if not _EXIT_HOOK_INSTALLED:
            atexit.register(_finish_log)
            _EXIT_HOOK_INSTALLED = True
        _log(
            "process_started",
            pid=os.getpid(),
            platform=platform.platform(),
            architecture=platform.machine(),
            executable=sys.executable,
            argv=sys.argv,
        )
        return path
    except Exception:
        _LOG_STREAM = None
        return None


def _start_server():
    _log("server_starting")
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    address, port = server.server_address
    base_url = f"http://{address}:{port}"
    _log("server_started", url=base_url)
    return server, server_thread, base_url


def _stop_server(server, server_thread) -> None:
    _log("server_stopping")
    try:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)
    finally:
        _log("server_stopped", thread_alive=server_thread.is_alive())


def _probe_backend(base_url: str) -> None:
    _log("backend_probe_started")
    with urlopen(f"{base_url}/api/status", timeout=5) as response:
        payload = json.load(response)
        if response.status != 200:
            raise RuntimeError(f"status endpoint returned HTTP {response.status}")
        if "status" not in payload or "contract" not in payload:
            raise RuntimeError("status endpoint returned an incomplete payload")
    with urlopen(f"{base_url}/", timeout=5) as response:
        body = response.read(4096)
        if response.status != 200:
            raise RuntimeError(f"workbench root returned HTTP {response.status}")
        if b"Ascent" not in body:
            raise RuntimeError("workbench root did not contain the expected UI")
    _log("backend_probe_passed")


def _startup_check() -> None:
    """Check frozen imports, local API, and packaged UI without opening a window."""
    try:
        import webview  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("pywebview is missing from the desktop bundle") from exc

    server, server_thread, base_url = _start_server()
    try:
        _probe_backend(base_url)
    finally:
        _stop_server(server, server_thread)


def _window_smoke_check() -> None:
    """Open the real native webview, verify its document, and close it automatically."""
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError("pywebview is missing from the desktop bundle") from exc

    server, server_thread, base_url = _start_server()
    shown = Event()
    loaded = Event()
    evidence = {"page_ready": False, "probe": None, "probe_error": None}
    try:
        _probe_backend(base_url)
        window = webview.create_window(
            "Ascent Calculus — Launch Check",
            f"{base_url}/",
            width=1000,
            height=720,
            min_size=(800, 600),
        )
        window.events.shown += lambda *args: (shown.set(), _log("window_shown"))
        window.events.loaded += lambda *args: (loaded.set(), _log("page_loaded"))

        def on_response(response):
            _log(
                "webview_response",
                url=getattr(response, "url", None),
                status=getattr(response, "status", None),
            )

        window.events.response_received += on_response

        def close_after_load(target):
            if not shown.wait(timeout=20):
                evidence["error"] = "native window was never shown"
                _log("window_smoke_timeout", stage="shown")
                target.destroy()
                return

            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                try:
                    probe = target.evaluate_js(
                        "JSON.stringify({"
                        "ready: document.readyState,"
                        "title: document.title,"
                        "text: (document.body ? document.body.innerText : '').slice(0, 300),"
                        "contentLength: document.documentElement ? "
                        "document.documentElement.innerHTML.length : 0"
                        "})"
                    )
                    evidence["probe"] = probe
                    result = json.loads(probe) if isinstance(probe, str) else probe
                    page_ready = (
                        result.get("ready") in {"interactive", "complete"}
                        and result.get("contentLength", 0) > 100
                        and bool(result.get("text", "").strip())
                    )
                    if page_ready:
                        evidence["page_ready"] = True
                        _log(
                            "page_probe_passed",
                            title=result.get("title"),
                            content_length=result.get("contentLength"),
                            loaded_event=loaded.is_set(),
                        )
                        time.sleep(1)
                        break
                except Exception as exc:
                    evidence["probe_error"] = repr(exc)
                time.sleep(0.25)

            if not evidence["page_ready"]:
                evidence["error"] = "webview document did not become ready"
                _log(
                    "page_probe_failed",
                    loaded_event=loaded.is_set(),
                    probe=evidence["probe"],
                    probe_error=evidence["probe_error"],
                )
            _log("window_smoke_closing")
            target.destroy()

        _log("window_smoke_starting")
        webview.start(close_after_load, window)
        if not shown.is_set():
            raise RuntimeError("native window was never shown")
        if not evidence["page_ready"]:
            raise RuntimeError(
                "workbench page did not become ready in the native window: "
                + str(evidence)
            )
        _log("window_smoke_passed", loaded_event=loaded.is_set())
    finally:
        _stop_server(server, server_thread)

def _show_macos_failure(log_path: Path | None) -> None:
    if sys.platform != "darwin":
        return
    detail = f"\n\nDiagnostic log: {log_path}" if log_path else ""
    message = f"Ascent Calculus could not start.{detail}"
    script = (
        "display dialog "
        + json.dumps(message)
        + ' with title "Ascent Calculus" buttons {"OK"} default button "OK"'
    )
    try:
        subprocess.run(["osascript", "-e", script], check=False, timeout=15)
    except Exception as exc:
        _log("failure_dialog_error", error=repr(exc))


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--startup-check", action="store_true")
    parser.add_argument("--window-smoke-check", action="store_true")
    args, _ = parser.parse_known_args(argv)

    log_path = _open_startup_log()
    _log(
        "main_entered",
        mode=(
            "window_smoke_check" if args.window_smoke_check
            else "startup_check" if args.startup_check
            else "desktop"
        ),
    )
    server = None
    server_thread = None
    try:
        if args.startup_check:
            _startup_check()
            _log("startup_check_passed")
            return
        if args.window_smoke_check:
            _window_smoke_check()
            return

        try:
            import webview
        except ImportError as exc:
            raise RuntimeError(
                "Desktop dependencies are missing. Install with "
                "python -m pip install 'ascent-calculus[desktop]'"
            ) from exc

        _log("webview_imported", version=getattr(webview, "__version__", "unknown"))
        server, server_thread, base_url = _start_server()
        _probe_backend(base_url)
        window = webview.create_window(
            "Ascent Calculus — Alpha",
            f"{base_url}/",
            width=1200,
            height=820,
            min_size=(900, 640),
        )
        window.events.initialized += lambda renderer: _log(
            "webview_initialized", renderer=renderer
        )
        window.events.before_show += lambda *args: _log("window_before_show")
        window.events.shown += lambda *args: _log("window_shown")
        window.events.loaded += lambda *args: _log("page_loaded")
        window.events.closing += lambda *args: _log("window_closing")
        window.events.closed += lambda *args: _log("window_closed")
        _log("webview_start_entered")
        webview.start()
        _log("webview_start_returned")
    except Exception:
        _log("fatal_exception", traceback=traceback.format_exc())
        _show_macos_failure(log_path)
        raise
    finally:
        if server is not None and server_thread is not None:
            _stop_server(server, server_thread)
        _log("main_finished")


if __name__ == "__main__":
    main()
