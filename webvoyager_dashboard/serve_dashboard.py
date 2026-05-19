#!/usr/bin/env python3
from __future__ import annotations

import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".md": "text/markdown; charset=utf-8",
    }

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def main() -> None:
    handler = functools.partial(Handler, directory=str(ROOT))
    server = ThreadingHTTPServer(("0.0.0.0", 5188), handler)
    print(f"Serving {ROOT} on http://0.0.0.0:5188/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
