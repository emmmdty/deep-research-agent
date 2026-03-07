"""工具系统模块——提供研究所需的各种工具。"""

from tools.web_search import web_search_tool
from tools.web_scraper import web_scraper_tool
from tools.arxiv_search import arxiv_search_tool

__all__ = [
    "web_search_tool",
    "web_scraper_tool",
    "arxiv_search_tool",
]
