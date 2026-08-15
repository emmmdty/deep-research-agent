"""PDF 文档解析工具——提取 PDF 文件的文本内容。

真实 PDF 解析（不再把截断的字节流当文本）：按 pypdf -> PyPDF2 -> docling
顺序尝试可用后端，任一后端产出非空文本即胜出；提取结果统一经过
``repair_mojibake`` 修复 "UTF-8 被按 latin-1/Windows-1252 误读" 产生的乱码。
pypdf 与 docling 都不是声明的依赖，全部在调用时惰性导入；失败必须上抛
ValueError，绝不返回伪装成内容的错误文本。
"""

from __future__ import annotations

import io
from pathlib import Path

from langchain_core.tools import tool
from loguru import logger

# 乱码修复表：UTF-8 字节序列被按 latin-1/Windows-1252 解码后的字符序列 -> 正确字符。
# 表项按"长串优先"排序（str.replace 按序执行），保证 â€ 前缀的短模式不会
# 提前吞掉更完整的 3 字符模式（如 â€" -> — 必须先于 â€ -> " 生效）。
_MOJIBAKE_PAIRS: tuple[tuple[str, str], ...] = (
    ("\u00e2\u20ac\u201c", "\u2013"),  # en dash –  (E2 80 93)
    ("\u00e2\u20ac\u201d", "\u2014"),  # em dash —  (E2 80 94)
    ("\u00e2\u20ac\u0152", "\u201c"),  # left double quote " (E2 80 9C)
    ("\u00e2\u20ac\u2122", "\u2019"),  # right single quote ' (E2 80 99)
    ("\u00e2\u20ac\u02dc", "\u2018"),  # left single quote ' (E2 80 98)
    ("\u00e2\u20ac\u00a6", "\u2026"),  # ellipsis … (E2 80 A6)
    ("\u00e2\u20ac", "\u201d"),  # right double quote " (E2 80 9D，0x9D 在 cp1252 未定义)
    # 2 字节 UTF-8 按 latin-1 误读的小写字母。
    ("\u00c3\u00a0", "\u00e0"),  # à
    ("\u00c3\u00a1", "\u00e1"),  # á
    ("\u00c3\u00a2", "\u00e2"),  # â
    ("\u00c3\u00a3", "\u00e3"),  # ã
    ("\u00c3\u00a4", "\u00e4"),  # ä
    ("\u00c3\u00a5", "\u00e5"),  # å
    ("\u00c3\u00a7", "\u00e7"),  # ç
    ("\u00c3\u00a8", "\u00e8"),  # è
    ("\u00c3\u00a9", "\u00e9"),  # é
    ("\u00c3\u00aa", "\u00ea"),  # ê
    ("\u00c3\u00ab", "\u00eb"),  # ë
    ("\u00c3\u00ac", "\u00ec"),  # ì
    ("\u00c3\u00ad", "\u00ed"),  # í
    ("\u00c3\u00ae", "\u00ee"),  # î
    ("\u00c3\u00af", "\u00ef"),  # ï
    ("\u00c3\u00b1", "\u00f1"),  # ñ
    ("\u00c3\u00b2", "\u00f2"),  # ò
    ("\u00c3\u00b3", "\u00f3"),  # ó
    ("\u00c3\u00b4", "\u00f4"),  # ô
    ("\u00c3\u00b5", "\u00f5"),  # õ
    ("\u00c3\u00b6", "\u00f6"),  # ö
    ("\u00c3\u00b9", "\u00f9"),  # ù
    ("\u00c3\u00ba", "\u00fa"),  # ú
    ("\u00c3\u00bb", "\u00fb"),  # û
    ("\u00c3\u00bc", "\u00fc"),  # ü
    ("\u00c3\u00bd", "\u00fd"),  # ý
    ("\u00c3\u00be", "\u00fe"),  # þ
    ("\u00c3\u00bf", "\u00ff"),  # ÿ
    # 2 字节 UTF-8 按 latin-1 误读的大写字母与符号。
    ("\u00c3\u0080", "\u00c0"),  # À
    ("\u00c3\u0081", "\u00c1"),  # Á
    ("\u00c3\u0082", "\u00c2"),  # Â
    ("\u00c3\u0083", "\u00c3"),  # Ã
    ("\u00c3\u0084", "\u00c4"),  # Ä
    ("\u00c3\u0085", "\u00c5"),  # Å
    ("\u00c3\u0086", "\u00c6"),  # Æ
    ("\u00c3\u0087", "\u00c7"),  # Ç
    ("\u00c3\u0088", "\u00c8"),  # È
    ("\u00c3\u0089", "\u00c9"),  # É
    ("\u00c3\u008a", "\u00ca"),  # Ê
    ("\u00c3\u008b", "\u00cb"),  # Ë
    ("\u00c3\u008c", "\u00cc"),  # Ì
    ("\u00c3\u008d", "\u00cd"),  # Í
    ("\u00c3\u008e", "\u00ce"),  # Î
    ("\u00c3\u008f", "\u00cf"),  # Ï
    ("\u00c3\u0091", "\u00d1"),  # Ñ
    ("\u00c3\u0092", "\u00d2"),  # Ò
    ("\u00c3\u0093", "\u00d3"),  # Ó
    ("\u00c3\u0094", "\u00d4"),  # Ô
    ("\u00c3\u0095", "\u00d5"),  # Õ
    ("\u00c3\u0096", "\u00d6"),  # Ö
    ("\u00c3\u0097", "\u00d7"),  # ×
    ("\u00c3\u0098", "\u00d8"),  # Ø
    ("\u00c3\u0099", "\u00d9"),  # Ù
    ("\u00c3\u009a", "\u00da"),  # Ú
    ("\u00c3\u009b", "\u00db"),  # Û
    ("\u00c3\u009c", "\u00dc"),  # Ü
    ("\u00c3\u009d", "\u00dd"),  # Ý
    ("\u00c3\u009e", "\u00de"),  # Þ
    ("\u00c3\u009f", "\u00df"),  # ß
    ("\u00c2\u00a0", "\u00a0"),  # nbsp
    ("\u00c2\u00a1", "\u00a1"),  # ¡
    ("\u00c2\u00a2", "\u00a2"),  # ¢
    ("\u00c2\u00a3", "\u00a3"),  # £
    ("\u00c2\u00a5", "\u00a5"),  # ¥
    ("\u00c2\u00a7", "\u00a7"),  # §
    ("\u00c2\u00a9", "\u00a9"),  # ©
    ("\u00c2\u00ab", "\u00ab"),  # «
    ("\u00c2\u00ae", "\u00ae"),  # ®
    ("\u00c2\u00b0", "\u00b0"),  # °
    ("\u00c2\u00b1", "\u00b1"),  # ±
    ("\u00c2\u00b2", "\u00b2"),  # ²
    ("\u00c2\u00b3", "\u00b3"),  # ³
    ("\u00c2\u00b4", "\u00b4"),  # ´
    ("\u00c2\u00b5", "\u00b5"),  # µ
    ("\u00c2\u00b6", "\u00b6"),  # ¶
    ("\u00c2\u00b7", "\u00b7"),  # ·
    ("\u00c2\u00bb", "\u00bb"),  # »
    ("\u00c2\u00bc", "\u00bc"),  # ¼
    ("\u00c2\u00bd", "\u00bd"),  # ½
    ("\u00c2\u00be", "\u00be"),  # ¾
    ("\u00c2\u00bf", "\u00bf"),  # ¿
)

# 需要丢弃的控制字符：\x00-\x08、\x0b、\x0c、\x0e-\x1f（保留 \t \n \r）。
_CONTROL_STRIP_TRANSLATION = str.maketrans(
    "",
    "",
    "".join(chr(code) for code in [*range(0x00, 0x09), 0x0B, 0x0C, *range(0x0E, 0x20)]),
)


def repair_mojibake(text: str) -> str:
    """修复常见乱码并丢弃控制字符。

    修复 "UTF-8 字节被按 latin-1/Windows-1252 解码" 的经典损坏
    （â€" -> —、â€œ -> "、â€ -> "、â€™ -> '、Ã© -> é、Ã¤ -> ä、Ã¼ -> ü、
    Ã± -> ñ、Ã— -> × 等），表项见 ``_MOJIBAKE_PAIRS``（长串优先，确定性）；
    随后丢弃 \\x00-\\x08、\\x0b、\\x0c、\\x0e-\\x1f 控制字符，保留
    \\t、\\n、\\r。
    """

    for mojibake, fixed in _MOJIBAKE_PAIRS:
        text = text.replace(mojibake, fixed)
    return text.translate(_CONTROL_STRIP_TRANSLATION)


def extract_pdf_text(pdf_bytes: bytes, *, max_chars: int = 100_000) -> str:
    """从 PDF 字节中提取文本，按可用后端依次尝试。

    后端顺序：pypdf -> PyPDF2 -> docling，各自在 try/except 内惰性导入
    （pyproject.toml 只声明了 pypdf2，pypdf/docling 为可选）；第一个产出
    非空文本的后端胜出。提取结果经过 :func:`repair_mojibake` 修复乱码并
    截断到 ``max_chars``。无可用后端或全部失败时抛出 ValueError——绝不
    返回伪装的"文本"。
    """

    failures: list[str] = []
    for name, extract in (
        ("pypdf", _extract_with_pypdf),
        ("PyPDF2", _extract_with_pypdf2),
        ("docling", _extract_with_docling),
    ):
        try:
            candidate = extract(pdf_bytes)
        except Exception as exc:  # 后端不可用/解析失败，记录后尝试下一个
            failures.append(f"{name}: {exc}")
            continue
        if candidate and candidate.strip():
            logger.info("PDF 文本提取: 后端='{}', 字符数={}", name, len(candidate))
            return repair_mojibake(candidate)[:max_chars]

    reason = "; ".join(failures) if failures else "无可用 PDF 解析后端"
    raise ValueError(f"PDF 解析失败: {reason}")


def _extract_with_pypdf(pdf_bytes: bytes) -> str:
    from pypdf import PdfReader  # 惰性导入：pypdf 非声明依赖

    return _join_page_texts(PdfReader(io.BytesIO(pdf_bytes)).pages)


def _extract_with_pypdf2(pdf_bytes: bytes) -> str:
    from PyPDF2 import PdfReader

    return _join_page_texts(PdfReader(io.BytesIO(pdf_bytes)).pages)


def _extract_with_docling(pdf_bytes: bytes) -> str:
    from docling.document_converter import DocumentConverter  # 惰性导入：docling 非声明依赖

    result = DocumentConverter().convert(io.BytesIO(pdf_bytes))
    return result.document.export_to_markdown()


def _join_page_texts(pages) -> str:
    """逐页提取文本；单页失败跳过，不影响其余页面。"""

    parts: list[str] = []
    for page in pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:
            continue
        if page_text.strip():
            parts.append(page_text)
    return "\n\n".join(parts)


@tool
def pdf_reader_tool(file_path: str) -> str:
    """读取并提取 PDF 文件的文本内容。

    Args:
        file_path: PDF 文件的本地路径。

    Returns:
        提取的 PDF 文本内容（由 extract_pdf_text 按 max_chars 截断）。
    """
    try:
        pdf_bytes = Path(file_path).read_bytes()
        text = extract_pdf_text(pdf_bytes)
        logger.info("PDF 解析完成: path='{}', 文本长度={}", file_path, len(text))
        return text
    except Exception as e:
        logger.error("PDF 解析失败: path='{}', 错误={}", file_path, e)
        # 失败必须上抛：错误文本伪装成"内容"后会被缓存并进入 grounding 管线。
        raise ValueError(f"PDF 解析失败: {file_path}: {e}") from e
