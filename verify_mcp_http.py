"""
Verify MCP HTTP server initialize + tools calls (local server on 127.0.0.1:8000)
"""
import json
import urllib.request
import urllib.error

URL = "http://127.0.0.1:8000/"
HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


def post_json(url, body, headers):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            status = resp.status
            mcp_sid = resp.headers.get("mcp-session-id")
            return status, mcp_sid, content
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8", errors="ignore")
        return e.code, e.headers.get("mcp-session-id"), content


def main():
    init = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "mcp-http-verify", "version": "1.0"},
        },
        "id": 1,
    }

    status, sid, content = post_json(URL, init, HEADERS)
    print(f"INIT_STATUS: {status}")
    print(f"SESSION: {sid}")
    print(content)

    if not sid:
        return

    tool_headers = dict(HEADERS)
    tool_headers["mcp-session-id"] = sid

    # List tools first to get exact names
    tools_list = {
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 10,
    }
    sl_status, _, sl_content = post_json(URL, tools_list, tool_headers)
    print(f"TOOLS_LIST: {sl_status}")
    print(sl_content)

    # Attempt to call tools
    idx = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "indexing_status"},
        "id": 2,
    }
    status2, _, content2 = post_json(URL, idx, tool_headers)
    print(f"INDEXING_STATUS: {status2}")
    print(content2)

    vs = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "vector_status"},
        "id": 3,
    }
    status3, _, content3 = post_json(URL, vs, tool_headers)
    print(f"VECTOR_STATUS: {status3}")
    print(content3)


if __name__ == "__main__":
    main()

