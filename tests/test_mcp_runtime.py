"""通用 MCP 运行时与配置回归测试。"""

from __future__ import annotations

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


def test_mcp_runtime_discovers_tools_and_writes_cache(monkeypatch, tmp_path: Path):
    """发现到的 tools 应写入 cache。"""
    from capabilities import mcp as mcp_module

    async def _fake_discover(self, server):
        return [
            mcp_module.MCPToolDefinition(
                name="search_docs",
                description="Search docs",
                input_schema={"type": "object"},
            )
        ]

    monkeypatch.setattr(mcp_module.MCPRuntime, "_discover_tools_async", _fake_discover)

    runtime = mcp_module.MCPRuntime(cache_dir=tmp_path / "cache")
    server = MCPServerConfig(name="docs", transport="stdio", command="python")

    tools = runtime.discover_server_tools(server)

    assert [tool.name for tool in tools] == ["search_docs"]
    assert (runtime.cache_dir / "docs.json").exists()


def test_mcp_runtime_falls_back_to_cache_after_discovery_failure(monkeypatch, tmp_path: Path):
    """discover 失败时应回退到已写入的 cache。"""
    from capabilities import mcp as mcp_module

    async def _success(self, server):
        return [
            mcp_module.MCPToolDefinition(
                name="search_docs",
                description="Search docs",
                input_schema={"type": "object"},
            )
        ]

    async def _failure(self, server):
        raise RuntimeError("stdio discovery failed")

    runtime = mcp_module.MCPRuntime(cache_dir=tmp_path / "cache")
    server = MCPServerConfig(name="docs", transport="stdio", command="python")

    monkeypatch.setattr(mcp_module.MCPRuntime, "_discover_tools_async", _success)
    first = runtime.discover_server_tools(server)

    monkeypatch.setattr(mcp_module.MCPRuntime, "_discover_tools_async", _failure)
    second = runtime.discover_server_tools(server)

    assert [tool.name for tool in first] == ["search_docs"]
    assert [tool.name for tool in second] == ["search_docs"]


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
