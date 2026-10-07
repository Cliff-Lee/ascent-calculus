"""Launch the AC workbench in a native desktop window.

The workbench UI still talks to the Python engine through its local HTTP API.
This launcher starts that API inside the application process and opens it in a
native webview, so users do not install Python or manage a server themselves.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import traceback
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.request import urlopen

# Use an absolute import because this file is also the PyInstaller entry script.
# A relative import can fail when the frozen executable runs it as __main__.
from ac.gui.server import Handler


def _start_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    address, port = server.server_address
    return server, server_thread, f"http://{address}:{port}"


def _stop_server(server, server_thread) -> None:
    server.shutdown()
    server.server_close()
    server_thread.join(timeout=2)


def _startup_check() -> None:
    """Exercise the frozen imports, static bundle and local API without opening a window."""
    try:
        import webview  # noqa: F401
    except ImportError as exc:  # pragma: no cover - packaging-only failure
        raise RuntimeError("pywebview is missing from the desktop bundle") from exc

    server, server_thread, base_url = _start_server()
    try:
        with urlopen(f"{base_url}/api/status", timeout=5) as response:
            if response.status != 200:
                raise RuntimeError(f"status endpoint returned HTTP {response.status}")
            payload = json.load(response)
            if "status" not in payload or "contract" not in payload:
                raise RuntimeError("status endpoint returned an incomplete payload")
        with urlopen(f"{base_url}/", timeout=5) as response:
            if response.status != 200:
                raise RuntimeError(f"workbench root returned HTTP {response.status}")
            if b"Ascent" not in response.read(4096):
                raise RuntimeError("workbench root did not contain the expected UI")
    finally:
        _stop_server(server, server_thread)


def _log_startup_failure() -> Path | None:
    try:
        if sys.platform == "darwin":
            log_dir = Path.home() / "Library" / "Logs" / "AscentCalculus"
        else:
            log_dir = Path.home() / ".ascent-calculus"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "startup.log"
        with log_path.open("w", encoding="utf-8") as stream:
            traceback.print_exc(file=stream)
        return log_path
    except Exception:
        return None


def _show_macos_failure(log_path: Path | None) -> None:
    if sys.platform != "darwin":
        return
    detail = f"\n\nCrash log: {log_path}" if log_path else ""
    message = f"Ascent Calculus could not start.{detail}"
    script = (
        'display dialog '
        + json.dumps(message)
        + ' with title "Ascent Calculus" buttons {"OK"} default button "OK"'
    )
    try:
        subprocess.run(["osascript", "-e", script], check=False, timeout=15)
    except Exception:
        pass


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--startup-check", action="store_true")
    args, _ = parser.parse_known_args(argv)

    try:
        if args.startup_check:
            _startup_check()
            return

        try:
            import webview
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError(
                "Desktop dependencies are missing. Install with "
                "python -m pip install 'ascent-calculus[desktop]'"
            ) from exc

        server, server_thread, base_url = _start_server()
        try:
            webview.create_window(
                "Ascent Calculus — Alpha",
                f"{base_url}/",
                width=1440,
                height=960,
                min_size=(960, 680),
            )
            webview.start()
        finally:
            _stop_server(server, server_thread)
    except Exception:
        log_path = _log_startup_failure()
        _show_macos_failure(log_path)
        raise


if __name__ == "__main__":
    main()
