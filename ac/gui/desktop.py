"""Launch the AC workbench in a native desktop window.

The workbench UI still talks to the Python engine through its local HTTP API.
This launcher starts that API inside the application process and opens it in a
native webview, so users do not install Python or manage a server themselves.
"""

from __future__ import annotations

from http.server import ThreadingHTTPServer
from threading import Thread

from .server import Handler


def main() -> None:
    try:
        import webview
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise SystemExit(
            "Desktop dependencies are missing. Install with "
            "python -m pip install 'ascent-calculus[desktop]'"
        ) from exc

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    address, port = server.server_address

    try:
        webview.create_window(
            "Ascent Calculus — Alpha",
            f"http://{address}:{port}/",
            width=1440,
            height=960,
            min_size=(960, 680),
        )
        webview.start()
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)


if __name__ == "__main__":
    main()
