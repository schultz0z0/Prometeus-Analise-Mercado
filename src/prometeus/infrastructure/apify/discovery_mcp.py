"""Consulta opcional do MCP Apify, sem ferramentas de execução ou pagamentos."""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from typing import Any, Literal
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel

DISCOVERY_TOOLS = frozenset({
    "search-actors", "fetch-actor-details", "search-apify-docs", "fetch-apify-docs",
})
DISCOVERY_URL = "https://mcp.apify.com?" + urlencode({
    "tools": ",".join(sorted(DISCOVERY_TOOLS)), "telemetry-enabled": "false",
})


class DiscoveryResult(BaseModel):
    status: Literal["ok", "disabled", "rejected", "unavailable", "invalid_response", "tool_error"]
    tool: str
    data: dict[str, Any] | list[Any] | None = None
    error_code: str | None = None
    untrusted: Literal[True] = True


class ApifyDiscoveryMCP:
    """Descoberta não promove Actors para o catálogo autorizado de execução."""

    def __init__(
        self, *, enabled: bool = False, timeout_seconds: float = 20,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.enabled = enabled
        self.timeout_seconds = max(0.1, min(timeout_seconds, 30))
        self.http_client = http_client

    async def lookup(self, tool: str, arguments: dict[str, Any]) -> DiscoveryResult:
        if tool not in DISCOVERY_TOOLS:
            return DiscoveryResult(status="rejected", tool=tool, error_code="tool_not_allowed")
        if not self.enabled:
            return DiscoveryResult(status="disabled", tool=tool)
        try:
            serialized = json.dumps(arguments, allow_nan=False)
        except (TypeError, ValueError):
            return DiscoveryResult(status="rejected", tool=tool, error_code="invalid_arguments")
        if len(serialized) > 4000:
            return DiscoveryResult(status="rejected", tool=tool, error_code="arguments_too_large")
        if tool == "fetch-actor-details" and "output" not in arguments:
            arguments = {
                **arguments,
                "output": {"description": True, "pricing": True, "metadata": True},
            }
        try:
            # Optional extra: missing SDK cannot break the normal API collector.
            from mcp import ClientSession
            from mcp.client.streamable_http import streamable_http_client

            async with asyncio.timeout(self.timeout_seconds):
                async with streamable_http_client(
                    DISCOVERY_URL, http_client=self.http_client,
                ) as (read_stream, write_stream, _):
                    async with ClientSession(
                        read_stream, write_stream,
                        read_timeout_seconds=timedelta(seconds=self.timeout_seconds),
                    ) as session:
                        await session.initialize()
                        catalog = await session.list_tools()
                        if tool not in {entry.name for entry in catalog.tools}:
                            return DiscoveryResult(
                                status="unavailable", tool=tool, error_code="tool_unavailable",
                            )
                        result = await session.call_tool(tool, arguments)
            if result.isError:
                return DiscoveryResult(status="tool_error", tool=tool, error_code="remote_tool_error")
            if len(result.model_dump_json().encode("utf-8")) > 262144:
                return DiscoveryResult(status="invalid_response", tool=tool, error_code="response_too_large")
            if result.structuredContent is not None:
                data = result.structuredContent
            else:
                texts = [block.text for block in result.content if block.type == "text"]
                if len(texts) != len(result.content) or not texts:
                    return DiscoveryResult(status="invalid_response", tool=tool, error_code="unsupported_content")
                content = "\n".join(texts)
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    data = {"text": content}
                if not isinstance(data, dict | list):
                    return DiscoveryResult(status="invalid_response", tool=tool, error_code="invalid_content")
            return DiscoveryResult(status="ok", tool=tool, data=data)
        except ImportError:
            return DiscoveryResult(status="unavailable", tool=tool, error_code="sdk_not_installed")
        except TimeoutError:
            return DiscoveryResult(status="unavailable", tool=tool, error_code="mcp_timeout")
        except Exception:
            # Remote diagnostics may carry secrets or hostile text; never echo them.
            return DiscoveryResult(status="unavailable", tool=tool, error_code="mcp_unavailable")
