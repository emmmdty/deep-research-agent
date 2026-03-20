"""通用 MCP 运行时与配置回归测试。"""

from __future__ import annotations

import sys
from pathlib import Path

from workflows.states import MCPServerConfig


def test_load_mcp_server_configs_supports_yaml_and_env_fallback(tmp_path: Path):
    """应支持从 YAML 读取 MCP server，并在缺失时回退到原始配置。"""
    from capabilities.mcp import load_mcp_server_configs

    config_path = tmp_path / "mcp_servers.yaml"
    config_path.write_text(
        """
servers:
  - name: browser
    transport: stdio
    command: uvx
    args:
      - mcp-server-browser
    tool_allowlist:
      - browser.search
  - name: docs
    transport: streamable-http
    url: http://127.0.0.1:8123/mcp
    headers_env:
      Authorization: TEST_TOKEN
""",
        encoding="utf-8",
    )

    configs = load_mcp_server_configs(
        config_path=config_path,
        raw_servers=[
            {
                "name": "fallback",
                "transport": "stdio",
                "command": "python",
            }
        ],
    )

    assert [item.name for item in configs] == ["browser", "docs"]
    assert configs[0].transport == "stdio"
    assert configs[0].tool_allowlist == ["browser.search"]
    assert configs[1].transport == "streamable-http"
    assert configs[1].url == "http://127.0.0.1:8123/mcp"
    assert configs[1].headers_env == {"Authorization": "TEST_TOKEN"}


def test_mcp_runtime_discovers_stdio_tools_and_writes_cache(tmp_path: Path):
    """stdio MCP server 应能被发现并写入 cache。"""
    from capabilities.mcp import MCPRuntime

    server_script = tmp_path / "stdio_server.py"
    server_script.write_text(
        """
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("test-docs")

@mcp.tool()
def search_docs(query: str, limit: int = 5) -> list[dict]:
    return [{"title": f"Result for {query}", "url": "https://example.com", "snippet": "doc"}][:limit]

if __name__ == "__main__":
    mcp.run(transport="stdio")
""",
        encoding="utf-8",
    )

    runtime = MCPRuntime(cache_dir=tmp_path / "cache")
    server = MCPServerConfig(
        name="docs",
        transport="stdio",
        command=sys.executable,
        args=[str(server_script)],
    )

    tools = runtime.discover_server_tools(server)

    assert [tool.name for tool in tools] == ["search_docs"]
    cache_path = runtime.cache_dir / "docs.json"
    assert cache_path.exists()
    assert "search_docs" in cache_path.read_text(encoding="utf-8")


def test_build_mcp_capabilities_discovers_runtime_tools(monkeypatch, tmp_path: Path):
    """能力构建应优先使用 runtime 发现的工具定义。"""
    from capabilities import mcp as mcp_module

    class _FakeRuntime:
        cache_dir = tmp_path / "cache"

        def discover_server_tools(self, server):
            return [
                mcp_module.MCPToolDefinition(
                    name="remote.search",
                    description="Search remote docs",
                    input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                )
            ]

    monkeypatch.setattr(mcp_module, "MCPRuntime", lambda *args, **kwargs: _FakeRuntime())

    capabilities = mcp_module.build_mcp_capabilities(
        raw_servers=[
            {
                "name": "docs",
                "transport": "streamable-http",
                "url": "http://127.0.0.1:8123/mcp",
            }
        ],
        workspace_dir=str(tmp_path / "workspace"),
    )

    assert [cap.name for cap in capabilities] == ["mcp.remote.search"]
    assert capabilities[0].metadata["server_name"] == "docs"
    assert capabilities[0].metadata["transport"] == "streamable-http"

