import json

import httpx
import pytest


@pytest.mark.asyncio
async def test_discovery_uses_official_sdk_handshake_and_readonly_tools():
    pytest.importorskip("mcp", reason="optional apify-mcp extra")
    from prometeus.infrastructure.apify.discovery_mcp import ApifyDiscoveryMCP

    methods = []
    calls = []

    def handler(request):
        assert request.url.host == "mcp.apify.com"
        assert "Authorization" not in request.headers
        assert "call-actor" not in request.url.query.decode()
        body = json.loads(request.content)
        methods.append(body["method"])
        if "id" not in body:
            return httpx.Response(202)
        result = {}
        if body["method"] == "initialize":
            result = {"protocolVersion": "2025-11-25", "capabilities": {"tools": {}},
                      "serverInfo": {"name": "Apify test", "version": "1"}}
        elif body["method"] == "tools/list":
            result = {"tools": [{"name": "search-actors", "inputSchema": {"type": "object"}}]}
        elif body["method"] == "tools/call":
            calls.append(body["params"])
            result = {"content": [{"type": "text", "text": '{"actors":[{"id":"approved-later"}]}'}]}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": body["id"], "result": result})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        result = await ApifyDiscoveryMCP(enabled=True, http_client=http_client).lookup(
            "search-actors", {"keywords": "google search"}
        )
    assert result.status == "ok"
    assert result.untrusted is True
    assert result.data == {"actors": [{"id": "approved-later"}]}
    assert methods == ["initialize", "notifications/initialized", "tools/list", "tools/call"]
    assert calls[0]["name"] == "search-actors"


@pytest.mark.asyncio
async def test_execution_tool_is_rejected_before_transport():
    from prometeus.infrastructure.apify.discovery_mcp import ApifyDiscoveryMCP

    result = await ApifyDiscoveryMCP(enabled=True).lookup("call-actor", {})
    assert result.status == "rejected"
    assert result.error_code == "tool_not_allowed"


@pytest.mark.asyncio
async def test_disabled_discovery_is_optional_and_never_opens_transport():
    from prometeus.infrastructure.apify.discovery_mcp import ApifyDiscoveryMCP

    result = await ApifyDiscoveryMCP().lookup("search-actors", {"keywords": "scraper"})
    assert result.status == "disabled"


@pytest.mark.asyncio
async def test_discovery_failure_does_not_leak_remote_secrets():
    from prometeus.infrastructure.apify.discovery_mcp import ApifyDiscoveryMCP

    def handler(request):
        raise httpx.ConnectError("secret-api-token", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        result = await ApifyDiscoveryMCP(enabled=True, http_client=http_client).lookup(
            "search-actors", {"keywords": "scraper"}
        )
    assert result.status == "unavailable"
    assert "secret-api-token" not in result.model_dump_json()


@pytest.mark.asyncio
async def test_admin_discovery_endpoint_uses_readonly_client(monkeypatch):
    import prometeus.entrypoints.rest.app as module
    from prometeus.infrastructure.apify.discovery_mcp import ApifyDiscoveryMCP, DiscoveryResult

    async def lookup(self, tool, arguments):
        assert tool == "fetch-actor-details"
        assert arguments == {"actor": "apify/google-search-scraper"}
        return DiscoveryResult(status="ok", tool=tool, data={"schema": {}})

    monkeypatch.setattr(ApifyDiscoveryMCP, "lookup", lookup)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=module.app), base_url="http://test",
        headers={"Authorization": "Bearer test-admin-key-12345678901234567890"},
    ) as client:
        response = await client.post("/v1/settings/apify/discovery", json={
            "tool": "fetch-actor-details", "arguments": {"actor": "apify/google-search-scraper"},
        })
    assert response.status_code == 200
    assert response.json()["untrusted"] is True


@pytest.mark.asyncio
async def test_admin_discovery_rejects_execution_tool_at_api_boundary():
    import prometeus.entrypoints.rest.app as module

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=module.app), base_url="http://test",
        headers={"Authorization": "Bearer test-admin-key-12345678901234567890"},
    ) as client:
        response = await client.post("/v1/settings/apify/discovery", json={
            "tool": "call-actor", "arguments": {},
        })
    assert response.status_code == 422
