"""Connector registry。"""

from __future__ import annotations

from collections.abc import Iterable

from deep_research_agent.connectors.files import LocalFileIngestor
from deep_research_agent.connectors.legacy import LegacyConnectorAdapter
from deep_research_agent.connectors.utils import canonicalize_uri, fetch_uri_block_reason
from deep_research_agent.connectors.tools.arxiv_search import search_arxiv_papers
from deep_research_agent.connectors.tools.github_search import search_github_repositories
from deep_research_agent.connectors.tools.web_scraper import web_scraper_tool
from deep_research_agent.connectors.tools.web_search import search_web


class ConnectorRegistry:
    """统一 connector 注册表。"""

    def __init__(self, connectors: dict[str, object]) -> None:
        self.connectors = connectors

    def get(self, name: str):
        connector = self.connectors.get(name)
        if connector is None and name == "web":
            connector = self.connectors.get("open_web")
        if connector is None:
            raise KeyError(f"未知 connector: {name}")
        return connector

    def list_names(self) -> list[str]:
        return sorted(self.connectors)

    def subset(self, names: Iterable[str]) -> dict[str, object]:
        return {name: self.get(name) for name in names}


def _web_fetch(url: str) -> dict[str, str]:
    canonical_url = canonicalize_uri(url)
    block_reason = fetch_uri_block_reason(canonical_url)
    if block_reason:
        raise ValueError(block_reason)
    text = web_scraper_tool.invoke({"url": canonical_url})
    return {"text": text, "mime_type": "text/html"}


def build_connector_registry(_settings=None) -> ConnectorRegistry:
    """构建 phase03 connector registry。"""
    return ConnectorRegistry(
        connectors={
            "open_web": LegacyConnectorAdapter(source_name="web", search_fn=search_web, fetch_fn=_web_fetch),
            "github": LegacyConnectorAdapter(source_name="github", search_fn=search_github_repositories),
            "arxiv": LegacyConnectorAdapter(source_name="arxiv", search_fn=search_arxiv_papers),
            "files": LocalFileIngestor(),
        }
    )
