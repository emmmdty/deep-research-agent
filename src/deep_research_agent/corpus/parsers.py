"""Optional scholarly parser adapters with a deterministic fallback."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from .models import ParsedDocument


class ParserUnavailable(RuntimeError):
    """Raised when an optional external parser cannot process a document."""


@runtime_checkable
class ScholarlyParser(Protocol):
    name: str
    version: str

    def parse(self, content: bytes | str, *, media_type: str = "application/pdf") -> ParsedDocument:
        ...


def _as_text(content: bytes | str) -> str:
    return content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content


class GrobidParser:
    """GROBID adapter. A callable can be injected in tests or by deployment code."""

    name = "grobid"

    def __init__(
        self,
        *,
        version: str = "1",
        parse_fn: Callable[..., ParsedDocument | dict[str, Any]] | None = None,
        client: Any | None = None,
    ) -> None:
        self.version = version
        self.parse_fn = parse_fn
        self.client = client

    def parse(self, content: bytes | str, *, media_type: str = "application/pdf") -> ParsedDocument:
        if self.parse_fn is not None:
            try:
                result = self.parse_fn(content, media_type=media_type)
            except TypeError:
                result = self.parse_fn(content)
            return _normalize_parsed(result)
        if self.client is None:
            raise ParserUnavailable("GROBID service is not configured")
        result = self.client.parse(content, media_type=media_type)
        return _normalize_parsed(result)


class DoclingParser:
    """Docling adapter; plain text extraction keeps unit tests dependency-free."""

    name = "docling"

    def __init__(
        self,
        *,
        version: str = "1",
        parse_fn: Callable[..., ParsedDocument | dict[str, Any]] | None = None,
    ) -> None:
        self.version = version
        self.parse_fn = parse_fn

    def parse(self, content: bytes | str, *, media_type: str = "application/pdf") -> ParsedDocument:
        if self.parse_fn is not None:
            try:
                result = self.parse_fn(content, media_type=media_type)
            except TypeError:
                result = self.parse_fn(content)
            return _normalize_parsed(result)
        text = _as_text(content)
        return ParsedDocument(text=text)


def _normalize_parsed(value: ParsedDocument | dict[str, Any]) -> ParsedDocument:
    return value if isinstance(value, ParsedDocument) else ParsedDocument.model_validate(value)


def parse_with_fallback(
    content: bytes | str,
    *,
    media_type: str,
    parsers: list[ScholarlyParser],
) -> tuple[ParsedDocument, ScholarlyParser]:
    errors: list[str] = []
    for parser in parsers:
        try:
            return parser.parse(content, media_type=media_type), parser
        except Exception as exc:  # parser services are optional and fail independently
            errors.append(f"{parser.name}: {exc}")
    raise ParserUnavailable("all scholarly parsers failed: " + "; ".join(errors))
