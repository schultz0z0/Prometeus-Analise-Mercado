import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from prometeus.infrastructure.apify.discovery_mcp import DISCOVERY_URL
from prometeus.infrastructure.apify.discovery_mcp import ApifyDiscoveryMCP


async def main():
    async with streamable_http_client(DISCOVERY_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            for tool in tools.tools:
                if tool.name == "fetch-actor-details":
                    print(json.dumps({"tool": tool.name, "schema_fields": list(tool.inputSchema.get("properties", {}))}))
    result = await ApifyDiscoveryMCP(enabled=True).lookup("fetch-actor-details", {"actor": "apify/google-search-scraper"})
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "transport": "official MCP Python SDK 1.28.1 / Streamable HTTP",
        "endpoint": "https://mcp.apify.com",
        "tools": ["fetch-actor-details"],
        "actor": "apify/google-search-scraper",
        "paid_execution": False,
        "status": result.status,
        "error_code": result.error_code,
        "untrusted": result.untrusted,
        "data_keys": list(result.data) if isinstance(result.data, dict) else [],
    }
    Path("output/homologation-2026-11-04/apify-mcp-readonly-verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


asyncio.run(main())
