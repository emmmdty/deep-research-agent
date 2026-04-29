"""Canonical connector helper tools."""

from deep_research_agent.connectors.tools.arxiv_search import arxiv_search_tool, search_arxiv_papers
from deep_research_agent.connectors.tools.github_search import github_search_tool, search_github_repositories
from deep_research_agent.connectors.tools.web_scraper import web_scraper_tool
from deep_research_agent.connectors.tools.web_search import search_web, web_search_tool

__all__ = [
    "arxiv_search_tool",
    "github_search_tool",
    "search_arxiv_papers",
    "search_github_repositories",
    "search_web",
    "web_scraper_tool",
    "web_search_tool",
]
