from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import urlparse

from .viewmodel import (
    bounded_check,
    inspect_word,
    interface_contract,
    research_status,
    trace_gap_swap_repair,
)
from .experiments import browse_objects, find_unmatched_objects, run_experiment, validate_pattern
from .transform_experiments import run_transform_experiment


STATIC = files("ac.gui.static")


class Handler(BaseHTTPRequestHandler):
    server_version = "ACGUI3/0.1"

    def _json(self, payload, status=200):
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        size = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(size) if size else b"{}"
        return json.loads(data.decode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            return self._json({"status": research_status(), "contract": interface_contract()})
        if path in {"/", "/index.html"}:
            target = STATIC.joinpath("index.html")
        elif path.startswith("/static/"):
            target = STATIC.joinpath(path.removeprefix("/static/"))
        else:
            self.send_error(404)
            return
        try:
            data = target.read_bytes()
        except FileNotFoundError:
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = self._body()
            if path == "/api/inspect":
                return self._json(inspect_word(body.get("word", "")))
            if path == "/api/trace":
                return self._json(trace_gap_swap_repair(
                    body.get("word", ""),
                    left_repeats=int(body.get("left_repeats", 2)),
                    right_repeats=int(body.get("right_repeats", 1)),
                ))
            if path == "/api/check":
                return self._json(bounded_check(
                    body.get("source", "m2122"),
                    body.get("target", "m2212"),
                    body.get("transform", "repair21"),
                    int(body.get("max_n", 8)),
                ))
            if path == "/api/experiment/validate-pattern":
                return self._json(validate_pattern(body.get("pattern", "")))
            if path == "/api/experiment/run":
                return self._json(run_experiment(body))
            if path == "/api/experiment/objects":
                return self._json(browse_objects(
                    body.get("specification", {}), body.get("side", "left"),
                    body.get("n", 1), body.get("offset", 0), body.get("limit", 25),
                    body.get("filters"),
                ))
            if path == "/api/experiment/unmatched":
                return self._json(find_unmatched_objects(body.get("specification", {}), body.get("n", 1)))
            if path == "/api/transform-experiment/run":
                return self._json(run_transform_experiment(body))
            self.send_error(404)
        except Exception as exc:
            self._json({"error": type(exc).__name__, "detail": str(exc)}, status=400)

    def log_message(self, fmt, *args):
        # Quiet default; launch with the browser devtools/network tab when debugging.
        pass


def main(argv=None):
    p = argparse.ArgumentParser(description="Run the Ascent Calculus research workbench")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Ascent Calculus Research Workbench: http://{args.host}:{args.port}")
    print("Research prototype: bounded verification is never displayed as proof.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
