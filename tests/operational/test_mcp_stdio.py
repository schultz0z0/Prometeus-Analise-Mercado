import json
import subprocess
import sys


def test_real_stdio_transport_handshake_notifications_and_tools():
    messages = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    result = subprocess.run(
        [sys.executable, "-m", "prometeus.entrypoints.mcp"],
        input="\n".join(json.dumps(item) for item in messages) + "\n",
        capture_output=True,
        encoding="utf-8",
        check=True,
        timeout=20,
    )
    responses = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(responses) == 2
    assert responses[0]["result"]["protocolVersion"] == "2025-11-25"
    assert len(responses[1]["result"]["tools"]) == 5
