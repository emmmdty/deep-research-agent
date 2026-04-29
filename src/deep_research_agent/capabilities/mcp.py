"""通用 MCP 配置、发现与适配。"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

import httpx
import yaml
from loguru import logger

from deep_research_agent.runtime.states import MCPServerConfig, MCPToolDefinition, ToolCapability

try:  # pragma: no cover - 由集成测试覆盖
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.sse import sse_client
    from mcp.client.stdio import stdio_client
    from mcp.client.streamable_http import streamable_http_client
except ImportError:  # pragma: no cover - 允许在无 mcp 依赖时退化
    ClientSession = None
    StdioServerParameters = None
    sse_client = None
    stdio_client = None
    streamable_http_client = None


def load_mcp_server_configs(
    *,
    config_path: str | Path | None = None,
    raw_servers: list[dict[str, Any]] | list[MCPServerConfig] | None = None,
) -> list[MCPServerConfig]:
    """按文件优先、环境回退的顺序加载 MCP server 配置。"""
    resolved_path = Path(config_path).expanduser() if config_path else None
    if resolved_path and resolved_path.exists():
        payload = yaml.safe_load(resolved_path.read_text(encoding="utf-8")) or {}
        servers = payload.get("servers", payload) if isinstance(payload, dict) else payload
        return parse_mcp_servers(servers or [])
    return parse_mcp_servers(raw_servers or [])


def parse_mcp_servers(raw_servers: list[dict[str, Any]] | list[MCPServerConfig]) -> list[MCPServerConfig]:
    """把 settings 中的 MCP 配置标准化。"""
    servers: list[MCPServerConfig] = []
    for raw in raw_servers:
        if isinstance(raw, MCPServerConfig):
            servers.append(raw)
            continue

        tools = [MCPToolDefinition.model_validate(tool) for tool in raw.get("tools", [])]
        servers.append(
            MCPServerConfig(
                name=raw["name"],
                transport=raw.get("transport") or ("stdio" if raw.get("command") else "streamable-http"),
                command=raw.get("command"),
                args=list(raw.get("args", [])),
                url=raw.get("url"),
                env=dict(raw.get("env", {})),
                headers_env=dict(raw.get("headers_env", {})),
                auth_env=raw.get("auth_env"),
                timeout_seconds=float(raw.get("timeout_seconds", 10.0)),
                tool_allowlist=list(raw.get("tool_allowlist", [])),
                tool_denylist=list(raw.get("tool_denylist", [])),
                enabled=bool(raw.get("enabled", True)),
                tools=tools,
            )
        )
    return servers


class MCPRuntime:
    """MCP 运行时：负责连接、发现、缓存和调用。"""

    def __init__(self, *, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def discover_server_tools(self, server: MCPServerConfig) -> list[MCPToolDefinition]:
        """发现单个 server 暴露的工具，并回写 cache。"""
        if not server.enabled:
            return []

        try:
            tools = asyncio.run(self._discover_tools_async(server))
            filtered = _filter_tools(tools, server)
            self._write_cache(server, filtered)
            return filtered
        except Exception as exc:
            logger.warning("MCP 工具发现失败，回退到 cache/static: server={}, error={}", server.name, exc)
            cached = self._read_cache(server)
            if cached:
                return _filter_tools(cached, server)
            return _filter_tools(server.tools, server)

    def call_tool(
        self,
        server: MCPServerConfig,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """调用远程 MCP 工具。"""
        if not server.enabled:
            raise RuntimeError(f"MCP server 已禁用: {server.name}")
        return asyncio.run(self._call_tool_async(server, tool_name, arguments or {}))

    def _write_cache(self, server: MCPServerConfig, tools: list[MCPToolDefinition]) -> None:
        cache_path = self.cache_dir / f"{server.name}.json"
        payload = {
            "server": server.name,
            "transport": server.transport,
            "tools": [tool.model_dump() for tool in tools],
        }
        cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read_cache(self, server: MCPServerConfig) -> list[MCPToolDefinition]:
        cache_path = self.cache_dir / f"{server.name}.json"
        if not cache_path.exists():
            return []
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        return [MCPToolDefinition.model_validate(item) for item in payload.get("tools", [])]

    async def _discover_tools_async(self, server: MCPServerConfig) -> list[MCPToolDefinition]:
        async with _open_session(server) as session:
            response = await session.list_tools()
            tools: list[MCPToolDefinition] = []
            for tool in getattr(response, "tools", []):
                input_schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", {}) or {}
                tools.append(
                    MCPToolDefinition(
                        name=getattr(tool, "name", ""),
                        description=getattr(tool, "description", "") or "",
                        input_schema=dict(input_schema),
                    )
                )
            return tools

    async def _call_tool_async(
        self,
        server: MCPServerConfig,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        async with _open_session(server) as session:
            result = await session.call_tool(tool_name, arguments=arguments)
            content = []
            for item in getattr(result, "content", []) or []:
                text = getattr(item, "text", None)
                if text:
                    content.append(text)
            return {
                "content": content,
                "structured_content": getattr(result, "structuredContent", None),
                "is_error": bool(getattr(result, "isError", False)),
            }


def build_mcp_capabilities(
    raw_servers: list[dict[str, Any]] | list[MCPServerConfig] | None,
    *,
    config_path: str | Path | None = None,
    workspace_dir: str | Path = "workspace",
) -> list[ToolCapability]:
    """从 MCP server 配置构建统一能力对象。"""
    server_configs = load_mcp_server_configs(config_path=config_path, raw_servers=raw_servers)
    runtime = MCPRuntime(cache_dir=Path(workspace_dir) / "mcp_cache")

    capabilities: list[ToolCapability] = []
    for server in server_configs:
        if server.tools and not server.command and not server.url:
            tools = _filter_tools(server.tools, server)
        else:
            tools = runtime.discover_server_tools(server)
        for tool in tools:
            capabilities.append(
                ToolCapability(
                    name=f"mcp.{tool.name}",
                    kind="mcp",
                    description=tool.description,
                    tags=["mcp", server.name, server.transport],
                    priority=50,
                    metadata={
                        "server_name": server.name,
                        "transport": server.transport,
                        "command": server.command,
                        "args": server.args,
                        "url": server.url,
                        "input_schema": tool.input_schema,
                    },
                )
            )
    return capabilities


def invoke_mcp_capability(
    capability: ToolCapability,
    *,
    query: str,
    max_results: int = 5,
    config_path: str | Path | None = None,
    raw_servers: list[dict[str, Any]] | list[MCPServerConfig] | None = None,
    workspace_dir: str | Path = "workspace",
) -> list[dict[str, Any]]:
    """调用单个 MCP capability，并尽量归一化为来源列表。"""
    server_name = capability.metadata.get("server_name")
    tool_name = capability.name.removeprefix("mcp.")
    if not server_name or not tool_name:
        return []

    server_index = {
        server.name: server
        for server in load_mcp_server_configs(config_path=config_path, raw_servers=raw_servers)
    }
    server = server_index.get(server_name)
    if server is None:
        return []

    runtime = MCPRuntime(cache_dir=Path(workspace_dir) / "mcp_cache")
    arguments = _build_tool_arguments(capability.metadata.get("input_schema", {}), query=query, max_results=max_results)
    response = runtime.call_tool(server, tool_name, arguments=arguments)
    return _normalize_tool_result(response, capability)


def _filter_tools(tools: list[MCPToolDefinition], server: MCPServerConfig) -> list[MCPToolDefinition]:
    allowlist = set(server.tool_allowlist)
    denylist = set(server.tool_denylist)
    filtered: list[MCPToolDefinition] = []
    for tool in tools:
        if allowlist and tool.name not in allowlist:
            continue
        if denylist and tool.name in denylist:
            continue
        filtered.append(tool)
    return filtered


def _build_tool_arguments(input_schema: dict[str, Any], *, query: str, max_results: int) -> dict[str, Any]:
    properties = input_schema.get("properties", {}) if isinstance(input_schema, dict) else {}
    arguments: dict[str, Any] = {}
    for key in properties:
        lowered = key.lower()
        if lowered in {"query", "q", "search", "text", "prompt", "topic"}:
            arguments[key] = query
        elif lowered in {"max_results", "limit", "top_k", "topn"}:
            arguments[key] = max_results
    return arguments


def _normalize_tool_result(response: dict[str, Any], capability: ToolCapability) -> list[dict[str, Any]]:
    structured = response.get("structured_content")
    source_name = capability.metadata.get("server_name", "mcp")

    if isinstance(structured, dict) and isinstance(structured.get("results"), list):
        return [_normalize_result_item(item, source_name) for item in structured["results"]]
    if isinstance(structured, list):
        return [_normalize_result_item(item, source_name) for item in structured]

    content = response.get("content") or []
    if not content:
        return []
    return [
        {
            "source_type": "web",
            "title": capability.description or capability.name,
            "url": "",
            "snippet": "\n".join(str(item) for item in content)[:500],
            "mcp_server": source_name,
        }
    ]


def _normalize_result_item(item: Any, server_name: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {
            "source_type": "web",
            "title": f"{server_name} result",
            "url": "",
            "snippet": str(item),
            "mcp_server": server_name,
        }
    return {
        "source_type": item.get("source_type", "web"),
        "title": item.get("title", f"{server_name} result"),
        "url": item.get("url", ""),
        "snippet": item.get("snippet") or item.get("content") or item.get("text") or "",
        "mcp_server": server_name,
    }


def _resolve_headers(server: MCPServerConfig) -> dict[str, str]:
    headers = {
        header: os.getenv(env_name, "")
        for header, env_name in server.headers_env.items()
        if os.getenv(env_name)
    }
    if server.auth_env and os.getenv(server.auth_env):
        headers.setdefault("Authorization", f"Bearer {os.getenv(server.auth_env)}")
    return headers


def _resolve_stdio_env(server: MCPServerConfig) -> dict[str, str]:
    return {**os.environ, **server.env}


async def _open_transport(server: MCPServerConfig):
    if ClientSession is None:
        raise RuntimeError("mcp 依赖不可用")

    if server.transport == "stdio":
        if not server.command or StdioServerParameters is None or stdio_client is None:
            raise RuntimeError(f"stdio MCP 配置不完整: {server.name}")
        params = StdioServerParameters(
            command=server.command,
            args=server.args,
            env=_resolve_stdio_env(server),
        )
        return stdio_client(params)

    if server.transport == "sse":
        if not server.url or sse_client is None:
            raise RuntimeError(f"SSE MCP 配置不完整: {server.name}")
        return sse_client(
            server.url,
            headers=_resolve_headers(server),
            timeout=server.timeout_seconds,
        )

    if server.transport in {"streamable-http", "http"}:
        if not server.url or streamable_http_client is None:
            raise RuntimeError(f"HTTP MCP 配置不完整: {server.name}")
        http_client = httpx.AsyncClient(
            headers=_resolve_headers(server),
            timeout=server.timeout_seconds,
        )
        return streamable_http_client(server.url, http_client=http_client)

    raise ValueError(f"不支持的 MCP transport: {server.transport}")


class _SessionContext:
    def __init__(self, server: MCPServerConfig) -> None:
        self.server = server
        self.transport_cm = None
        self.transport = None
        self.session = None

    async def __aenter__(self):
        self.transport_cm = await _open_transport(self.server)
        self.transport = await self.transport_cm.__aenter__()
        if self.server.transport in {"streamable-http", "http"}:
            read_stream, write_stream, _ = self.transport
        else:
            read_stream, write_stream = self.transport
        self.session = ClientSession(read_stream, write_stream)
        await self.session.__aenter__()
        await self.session.initialize()
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        if self.session is not None:
            await self.session.__aexit__(exc_type, exc, tb)
        if self.transport_cm is not None:
            await self.transport_cm.__aexit__(exc_type, exc, tb)


def _open_session(server: MCPServerConfig) -> _SessionContext:
    return _SessionContext(server)
