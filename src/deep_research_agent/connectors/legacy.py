"""基于旧 tools 的 connector adapter。"""

from __future__ import annotations

from typing import Any, Callable

from deep_research_agent.connectors.models import ConnectorCandidate, ConnectorFetchResult
from deep_research_agent.connectors.utils import canonicalize_uri


class LegacyConnectorAdapter:
    """把现有 search/fetch 工具包装成统一 connector。"""

    def __init__(
        self,
        *,
        source_name: str,
        search_fn: Callable[..., list[dict[str, Any]]],
        fetch_fn: Callable[[str], dict[str, Any]] | Callable[[str], str] | None = None,
        supports_critical_claims: bool | None = None,
        source_role: str | None = None,
    ) -> None:
        self.source_name = source_name
        self.search_fn = search_fn
        self.fetch_fn = fetch_fn
        self.supports_critical_claims = (
            source_name in {"arxiv", "acl", "pmlr", "jmlr", "tmlr"}
            if supports_critical_claims is None
            else supports_critical_claims
        )
        self.source_role = source_role or (
            "primary_publication" if self.supports_critical_claims else "discovery"
        )

    @property
    def connector_name(self) -> str:
        return "open_web" if self.source_name == "web" else self.source_name

    def search(self, query: str, *, max_results: int = 5) -> list[ConnectorCandidate]:
        """执行 search，并归一成 candidate。"""
        items = self.search_fn(query, max_results=max_results)
        candidates: list[ConnectorCandidate] = []
        for item in items:
            canonical_uri = canonicalize_uri(str(item.get("url") or ""))
            candidates.append(
                ConnectorCandidate(
                    connector_name=self.connector_name,
                    source_type=str(item.get("source_type") or self.source_name),
                    title=str(item.get("title") or "无标题"),
                    canonical_uri=canonical_uri,
                    query=str(item.get("query") or query),
                    snippet=str(item.get("snippet") or ""),
                    published_at=item.get("published_at"),
                    auth_scope=str(item.get("auth_scope") or "public"),
                    metadata={
                        key: value
                        for key, value in item.items()
                        if key
                        not in {"index", "source_type", "title", "url", "query", "snippet", "published_at", "auth_scope"}
                    },
                )
            )
        return candidates

    def fetch(self, candidate: ConnectorCandidate) -> ConnectorFetchResult:
        """执行 fetch，并归一成文档。"""
        text = candidate.snippet or candidate.title
        mime_type = "text/plain"
        metadata = dict(candidate.metadata)
        if self.fetch_fn is not None:
            response = self.fetch_fn(candidate.canonical_uri)
            if isinstance(response, dict):
                text = str(response.get("text") or text)
                mime_type = str(response.get("mime_type") or mime_type)
                metadata = {**metadata, **{k: v for k, v in response.items() if k not in {"text", "mime_type"}}}
            else:
                text = str(response)

        freshness_metadata = {"published_at": candidate.published_at, **metadata}
        return ConnectorFetchResult(
            connector_name=candidate.connector_name,
            source_type=candidate.source_type,
            title=candidate.title,
            canonical_uri=candidate.canonical_uri,
            query=candidate.query,
            text=text,
            snippet=candidate.snippet,
            mime_type=mime_type,
            auth_scope=candidate.auth_scope,
            supports_critical_claims=self.supports_critical_claims,
            source_role=self.source_role,
            freshness_metadata=freshness_metadata,
            metadata=metadata,
            url=candidate.canonical_uri,
        )

    @property
    def critical_claims_allowed(self) -> bool:
        """Whether this connector can supply evidence for a critical claim."""

        return self.supports_critical_claims

    def source_descriptor(self):
        """Build the typed corpus policy declaration for this connector."""

        from deep_research_agent.corpus.models import SourceDescriptor

        return SourceDescriptor(
            source_id=self.source_name,
            source_role=self.source_role,
            trust_tier=1 if self.supports_critical_claims else 4,
            official_base_uri={
                "arxiv": "https://arxiv.org",
                "acl": "https://aclanthology.org",
                "pmlr": "https://proceedings.mlr.press",
                "jmlr": "https://jmlr.org",
                "tmlr": "https://jmlr.org/tmlr",
            }.get(self.source_name, ""),
            access_method="connector",
            storage_policy="internal_processing" if self.supports_critical_claims else "link_only",
            redistribution_policy="item-license",
            parser_name="grobid",
            parser_version="1",
            supports_critical_claims=self.supports_critical_claims,
        )

    def fetch_corpus(self, candidate: ConnectorCandidate) -> ConnectorFetchResult:
        """Explicit typed-corpus entrypoint; discovery connectors remain typed candidates only."""

        if not self.supports_critical_claims:
            raise PermissionError(
                f"connector {self.connector_name!r} is discovery-only and cannot support critical claims"
            )
        return self.fetch(candidate)
