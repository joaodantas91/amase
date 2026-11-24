#!/usr/bin/env python3
"""
AMASE Universal UI Validation MCP Server (scripts/ui_mcp_server.py)

Exposes the 'validate_ui' tool over the standard Model Context Protocol (MCP) JSON-RPC
over stdio. Usable by external AI orchestrators and IDEs (Claude Code, Cursor, OpenCode,
Windsurf, Antigravity) to inspect web pages at ultra-low token cost (<150 tokens).
"""

import io
import json
import os
import sys
from typing import Dict, Any, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    from ui_validator import validate_page
    from ui_formatter import format_ui_report
except ImportError:
    from scripts.ui_validator import validate_page
    from scripts.ui_formatter import format_ui_report

SERVER_NAME = "amase-ui-lens"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"

TOOLS_SCHEMA = [
    {
        "name": "validate_ui",
        "description": (
            "Headless UI layout and runtime validator for web pages. Deterministically detects "
            "horizontal viewport overflows (mobile/desktop), interactive element collisions/overlaps, "
            "broken images (404/naturalWidth=0), and uncaught console errors, returning a compact "
            "<150-token markdown diagnostic with exact selector coordinates (0 image tokens)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Target web page URL (e.g. 'http://localhost:3000' or 'http://localhost:5173/dashboard')"
                },
                "viewport": {
                    "type": "string",
                    "description": "Viewport dimensions WxH (default: '375x812' for mobile, or '1280x800' for desktop)",
                    "default": "375x812"
                }
            },
            "required": ["url"]
        }
    }
]


def handle_rpc_request(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process a single JSON-RPC 2.0 request and return the appropriate response."""
    msg_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    if not method:
        return None

    # 1. Initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION
                }
            }
        }

    # 2. Initialized Notification (No response needed)
    if method in ("notifications/initialized", "initialized"):
        return None

    # 3. Ping
    if method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {}
        }

    # 4. List Tools
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": TOOLS_SCHEMA
            }
        }

    # 5. Call Tool
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name == "validate_ui":
            target_url = arguments.get("url", "")
            viewport = arguments.get("viewport", "375x812")

            if not target_url:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32602,
                        "message": "Missing required argument: 'url'"
                    }
                }

            # In mock test or offline dry run, provide deterministic structured summary
            if target_url.startswith("mock://"):
                mock_layout = {
                    "overflows": [{"selector": "button#submit", "overflowPx": 45}],
                    "overlaps": [{"elementA": "button#submit", "elementB": "a.cancel"}],
                    "tinyTargets": []
                }
                mock_network = {
                    "failed_requests": [{"status": 404, "url": f"{target_url}/logo.svg"}],
                    "broken_images": [],
                    "console_errors": []
                }
                text_result = format_ui_report(target_url, mock_layout, mock_network, viewport)
            else:
                audit_res = validate_page(target_url, viewport_label=viewport)
                text_result = audit_res["condensed_report"]

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": text_result
                        }
                    ],
                    "isError": False
                }
            }

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Method not found or unknown tool: {tool_name}"
            }
        }

    # Unknown method
    if msg_id is not None:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

    return None


def run_stdio_server():
    """Run interactive stdio MCP server loop."""
    sys.stderr.write(f"[+] Starting AMASE UI Lens MCP Server ({SERVER_NAME} v{SERVER_VERSION}) on stdio...\n")
    sys.stderr.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = handle_rpc_request(req)
            if resp:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"[-] Error processing JSON-RPC message: {e}\n")
            sys.stderr.flush()


def run_mock_test():
    """Verify MCP protocol compliance (initialize, tools/list, tools/call) via self-test."""
    print("[+] Running ui_mcp_server.py self-test harness...")

    # 1. Test initialize
    init_req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    init_resp = handle_rpc_request(init_req)
    assert init_resp["id"] == 1
    assert init_resp["result"]["serverInfo"]["name"] == SERVER_NAME
    assert "tools" in init_resp["result"]["capabilities"]
    print("✓ MCP 'initialize' handshake passed.")

    # 2. Test tools/list
    list_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    list_resp = handle_rpc_request(list_req)
    assert list_resp["id"] == 2
    tools = list_resp["result"]["tools"]
    assert any(t["name"] == "validate_ui" for t in tools)
    print("✓ MCP 'tools/list' schema catalog passed.")

    # 3. Test tools/call
    call_req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "validate_ui",
            "arguments": {
                "url": "mock://test-suite/dashboard",
                "viewport": "375x812"
            }
        }
    }
    call_resp = handle_rpc_request(call_req)
    assert call_resp["id"] == 3
    content = call_resp["result"]["content"][0]["text"]
    assert "[UI FAIL]" in content
    assert "button#submit" in content
    print("✓ MCP 'tools/call' for 'validate_ui' passed with condensed text.")

    print("[+] ui_mcp_server.py self-test PASSED (exit code 0).")


def main():
    if "--mock-test" in sys.argv:
        run_mock_test()
        sys.exit(0)

    if "--help" in sys.argv or "-h" in sys.argv:
        print("AMASE UI Validation MCP Server")
        print("Usage: scripts/ui_mcp_server.py [--mock-test]")
        print("Runs standard JSON-RPC 2.0 MCP protocol over stdio.")
        sys.exit(0)

    run_stdio_server()


if __name__ == "__main__":
    main()
