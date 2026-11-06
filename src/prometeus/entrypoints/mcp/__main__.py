"""Transporte MCP stdio: processo local confiável, mensagens JSON em linhas UTF-8."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

from prometeus.entrypoints.mcp.server import PrometeusMCPServer
from prometeus.infrastructure.db.session import get_session_factory


async def serve_stdio() -> None:
    server = PrometeusMCPServer(get_session_factory())
    while True:
        result: dict[str, Any] | None
        line = await asyncio.to_thread(sys.stdin.readline)
        if not line:
            return
        try:
            request = json.loads(line)
            if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
                result = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32600, "message": "Invalid Request"},
                }
            else:
                result = await server.handle_request(request)
        except (ValueError, TypeError):
            result = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
        if result is not None:
            print(json.dumps(result, ensure_ascii=False), flush=True)


def main() -> None:
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    for stream in (sys.stdin, sys.stdout):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")
    asyncio.run(serve_stdio())


if __name__ == "__main__":
    main()
