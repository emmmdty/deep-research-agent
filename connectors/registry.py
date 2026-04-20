"""Connector registry。"""

from __future__ import annotations

from collections.abc import Iterable

from connectors.files import LocalFileIngestor
from connectors.legacy import LegacyConnectorAdapter
from tools.arxiv_search import search_arxiv_papers
from tools.github_search import search_github_repositories
from tools.web_scraper import web_scraper_tool
from tools.web_search import search_web


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
    text = web_scraper_tool.invoke({"url": url})
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
