"""一手来源抓取策略（phase-2 task 6）的确定性回归测试。

覆盖范围：Wayback 403/反爬回退、PDF 真实解析 + mojibake 修复、arXiv 全文链接。
全部测试不触网：网页抓取走 httpx_mock，PDF 用手工构造的最小合法 PDF 字节。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from deep_research_agent.connectors.tools.arxiv_search import (
    arxiv_fulltext_url,
    format_arxiv_results,
    search_arxiv_papers,
)
from deep_research_agent.connectors.tools.page_fetch import fetch_page, wayback_url
from deep_research_agent.connectors.tools.pdf_reader import (
    extract_pdf_text,
    pdf_reader_tool,
    repair_mojibake,
)

_BLOCKED_PAGE = "https://example.com/report"
_WAYBACK_PAGE = "https://web.archive.org/web/2026id_/https://example.com/report"


# ---------------------------------------------------------------- helpers


def build_minimal_pdf(text: str = "Hello PDF 2026") -> bytes:
    """手工构造一个单页最小合法 PDF（含正确 xref 偏移），文本流包含给定字符串。"""
    stream = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        b"<< /Length "
        + str(len(stream)).encode("ascii")
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    body = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(body))
        body += f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"
    xref_pos = len(body)
    body += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    body += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        body += f"{offset:010d} 00000 n \n".encode("ascii")
    body += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    ).encode("ascii")
    return bytes(body)


_WAYBACK_HTML = (
    "<html><head><title>Archived Report 2026</title></head>"
    "<body><nav>nav noise</nav><article>"
    "<p>The origin was blocked, so this snapshot was served from the "
    "Wayback Machine instead.</p></article>"
    "<footer>footer noise</footer></body></html>"
)


def _fetch(url: str, **kwargs) -> dict:
    return fetch_page(url, **kwargs)


# ---------------------------------------------------------------- wayback_url


def test_wayback_url_construction() -> None:
    assert wayback_url("https://openai.com/research/foo") == (
        "https://web.archive.org/web/2026id_/https://openai.com/research/foo"
    )


def test_wayback_url_custom_timestamp() -> None:
    assert wayback_url("http://example.com/a", timestamp="20240101") == (
        "https://web.archive.org/web/20240101id_/http://example.com/a"
    )


def test_wayback_url_rejects_unsafe_inputs() -> None:
    with pytest.raises(ValueError, match="only supports http"):
        wayback_url("file:///etc/passwd")
    with pytest.raises(ValueError, match="refuses non-public host"):
        wayback_url("http://127.0.0.1/admin")
    with pytest.raises(ValueError, match="refuses non-public host"):
        wayback_url("http://localhost/x")
    with pytest.raises(ValueError, match="refuses non-public host"):
        wayback_url("http://192.168.1.10/x")


# ---------------------------------------------------------------- wayback fallback


def test_fetch_page_falls_back_to_wayback_on_403(httpx_mock) -> None:
    httpx_mock.add_response(url=_BLOCKED_PAGE, status_code=403)
    httpx_mock.add_response(url=_WAYBACK_PAGE, html=_WAYBACK_HTML)

    result = _fetch(_BLOCKED_PAGE)

    assert result["via_wayback"] is True
    assert result["url"] == _BLOCKED_PAGE
    assert result["original_url"] == _BLOCKED_PAGE
    assert result["final_url"] == _WAYBACK_PAGE
    assert result["fetch_status"] == "ok"
    assert "Wayback Machine instead" in str(result["content"])
    assert "nav noise" not in str(result["content"])


def test_fetch_page_falls_back_to_wayback_on_429(httpx_mock) -> None:
    httpx_mock.add_response(url=_BLOCKED_PAGE, status_code=429)
    httpx_mock.add_response(url=_WAYBACK_PAGE, html=_WAYBACK_HTML)

    result = _fetch(_BLOCKED_PAGE)

    assert result["via_wayback"] is True
    assert result["final_url"] == _WAYBACK_PAGE


def test_fetch_page_wayback_failure_reraises_original_error(httpx_mock) -> None:
    httpx_mock.add_response(url=_BLOCKED_PAGE, status_code=403)
    httpx_mock.add_response(url=_WAYBACK_PAGE, status_code=404)

    with pytest.raises(ValueError, match="could not retrieve"):
        _fetch(_BLOCKED_PAGE)


def test_fetch_page_no_wayback_fallback_when_disabled(httpx_mock) -> None:
    httpx_mock.add_response(url=_BLOCKED_PAGE, status_code=403)

    with pytest.raises(ValueError, match="could not retrieve"):
        _fetch(_BLOCKED_PAGE, wayback_fallback=False)


def test_fetch_page_direct_success_via_wayback_false(httpx_mock) -> None:
    html = (
        "<html><head><title>Direct Page</title></head>"
        "<body><article><p>Direct fetch works fine.</p></article></body></html>"
    )
    httpx_mock.add_response(url=_BLOCKED_PAGE, html=html)

    result = _fetch(_BLOCKED_PAGE)

    assert result["via_wayback"] is False
    assert "original_url" not in result
    assert result["final_url"] == _BLOCKED_PAGE
    assert result["source_type"] == "web_page"
    assert "Direct fetch works fine" in str(result["content"])


# ---------------------------------------------------------------- PDF parsing


def test_extract_pdf_text_parses_minimal_hand_built_pdf() -> None:
    pdf_bytes = build_minimal_pdf()

    assert extract_pdf_text(pdf_bytes) == "Hello PDF 2026"


def test_extract_pdf_text_respects_max_chars() -> None:
    pdf_bytes = build_minimal_pdf()

    assert extract_pdf_text(pdf_bytes, max_chars=7) == "Hello P"


def test_extract_pdf_text_repairs_mojibake_inside_pdf() -> None:
    pdf_bytes = build_minimal_pdf("Caf\u00c3\u00a9 2026")  # "CafÃ©" read as latin-1

    assert extract_pdf_text(pdf_bytes) == "Café 2026"


def test_extract_pdf_text_raises_on_garbage_bytes() -> None:
    with pytest.raises(ValueError, match="PDF 解析失败"):
        extract_pdf_text(b"\x00\x01\x02 not a pdf at all" * 10)


def test_pdf_reader_tool_reads_file_and_returns_text(tmp_path: Path) -> None:
    pdf_path = tmp_path / "hello.pdf"
    pdf_path.write_bytes(build_minimal_pdf())

    text = pdf_reader_tool.invoke({"file_path": str(pdf_path)})

    assert "Hello PDF 2026" in text


def test_pdf_reader_tool_raises_on_corrupt_file(tmp_path: Path) -> None:
    pdf_path = tmp_path / "broken.pdf"
    pdf_path.write_bytes(b"not a pdf")

    with pytest.raises(ValueError, match="PDF 解析失败"):
        pdf_reader_tool.invoke({"file_path": str(pdf_path)})


def test_fetch_page_parses_pdf_content_type(httpx_mock) -> None:
    httpx_mock.add_response(
        url="https://example.com/paper",
        content=build_minimal_pdf(),
        headers={"content-type": "application/pdf; charset=binary"},
    )

    result = _fetch("https://example.com/paper")

    assert result["via_wayback"] is False
    assert result["source_type"] == "pdf"
    assert result["fetch_status"] == "ok"
    assert "Hello PDF 2026" in str(result["content"])


# ---------------------------------------------------------------- repair_mojibake


@pytest.mark.parametrize(
    ("mojibake", "fixed"),
    [
        ("\u00e2\u20ac\u201c", "\u2013"),  # en dash
        ("\u00e2\u20ac\u201d", "\u2014"),  # em dash
        ("\u00e2\u20ac\u0152", "\u201c"),  # left double quote
        ("\u00e2\u20ac", "\u201d"),  # right double quote (undefined 3rd byte)
        ("\u00e2\u20ac\u2122", "\u2019"),  # right single quote
        ("\u00e2\u20ac\u02dc", "\u2018"),  # left single quote
        ("\u00c3\u00a9", "\u00e9"),  # é
        ("\u00c3\u00a4", "\u00e4"),  # ä
        ("\u00c3\u00bc", "\u00fc"),  # ü
        ("\u00c3\u00b1", "\u00f1"),  # ñ
        ("\u00c3\u0097", "\u00d7"),  # ×
    ],
)
def test_repair_mojibake_table(mojibake: str, fixed: str) -> None:
    assert repair_mojibake(f"before {mojibake} after") == f"before {fixed} after"


def test_repair_mojibake_longest_match_wins() -> None:
    assert repair_mojibake("a\u00e2\u20ac\u201db") == "a\u2014b"
    assert repair_mojibake("a\u00e2\u20acb") == "a\u201db"


def test_repair_mojibake_strips_control_characters() -> None:
    assert repair_mojibake("a\x00b\x08c\x0bd\x0ce\x0fe") == "abcdee"


def test_repair_mojibake_preserves_whitespace() -> None:
    assert repair_mojibake("line one\n\tline two\r") == "line one\n\tline two\r"


# ---------------------------------------------------------------- arXiv fulltext


@pytest.mark.parametrize(
    ("entry_id", "expected"),
    [
        ("https://arxiv.org/abs/2401.12345v2", "https://arxiv.org/html/2401.12345v2"),
        ("http://arxiv.org/abs/2401.12345", "https://arxiv.org/html/2401.12345"),
        ("https://arxiv.org/pdf/2401.12345v2.pdf", "https://arxiv.org/html/2401.12345v2"),
        ("https://arxiv.org/pdf/2401.12345.pdf", "https://arxiv.org/html/2401.12345"),
        ("2401.12345v2", "https://arxiv.org/html/2401.12345v2"),
        ("2401.12345", "https://arxiv.org/html/2401.12345"),
        ("https://arxiv.org/html/2401.12345v2", "https://arxiv.org/html/2401.12345v2"),
        ("http://arxiv.org/html/2401.12345", "https://arxiv.org/html/2401.12345"),
        ("arxiv.org/abs/2401.12345", "https://arxiv.org/html/2401.12345"),
        ("https://arxiv.org/abs/cond-mat/0309395", "https://arxiv.org/html/cond-mat/0309395"),
        ("cond-mat/0309395", "https://arxiv.org/html/cond-mat/0309395"),
        ("arXiv:2401.12345", ""),
        ("arxiv:2401.12345", ""),
        ("https://arxiv.org/abs/2401.12345X", ""),
        ("https://example.com/abs/2401.12345", ""),
        ("not-an-arxiv-id", ""),
        ("", ""),
    ],
)
def test_arxiv_fulltext_url_table(entry_id: str, expected: str) -> None:
    assert arxiv_fulltext_url(entry_id) == expected


def test_search_arxiv_papers_includes_fulltext_url(monkeypatch) -> None:
    import sys

    import deep_research_agent.connectors.tools.arxiv_search as arxiv_search

    class FakeClient:
        def results(self, search) -> list:
            return [
                SimpleNamespace(
                    entry_id="http://arxiv.org/abs/2401.12345v2",
                    title="A Paper",
                    summary="The abstract of the paper.",
                    authors=[SimpleNamespace(name="Alice")],
                    published=datetime(2026, 1, 15),
                )
            ]

    monkeypatch.setitem(
        sys.modules,
        "arxiv",
        SimpleNamespace(
            Client=FakeClient,
            Search=lambda **kwargs: kwargs,
            SortCriterion=SimpleNamespace(Relevance="relevance"),
        ),
    )
    monkeypatch.setattr(
        arxiv_search,
        "get_tracker",
        lambda: SimpleNamespace(record_search_call=lambda: None),
    )

    results = search_arxiv_papers("papers", max_results=5)

    assert results[0]["url"] == "http://arxiv.org/abs/2401.12345v2"
    assert results[0]["fulltext_url"] == "https://arxiv.org/html/2401.12345v2"


def test_format_arxiv_results_includes_fulltext_line() -> None:
    formatted = format_arxiv_results(
        [
            {
                "index": 1,
                "title": "A Paper",
                "authors": "Alice",
                "published_at": "2026-01-15",
                "url": "https://arxiv.org/abs/2401.12345",
                "snippet": "abstract",
                "fulltext_url": "https://arxiv.org/html/2401.12345",
            }
        ]
    )

    assert "全文: https://arxiv.org/html/2401.12345" in formatted
    assert "链接: https://arxiv.org/abs/2401.12345" in formatted


def test_format_arxiv_results_omits_empty_fulltext() -> None:
    formatted = format_arxiv_results(
        [
            {
                "index": 1,
                "title": "A Paper",
                "authors": "Alice",
                "published_at": "2026-01-15",
                "url": "https://arxiv.org/abs/2401.12345",
                "snippet": "abstract",
            }
        ]
    )

    assert "全文:" not in formatted
