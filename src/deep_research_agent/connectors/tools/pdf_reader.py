"""PDF 文档解析工具——提取 PDF 文件的文本内容。"""

from __future__ import annotations

from langchain_core.tools import tool
from loguru import logger


@tool
def pdf_reader_tool(file_path: str) -> str:
    """读取并提取 PDF 文件的文本内容。

    Args:
        file_path: PDF 文件的本地路径。

    Returns:
        提取的 PDF 文本内容（前 10000 字符）。
    """
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(file_path)
        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        full_text = "\n\n".join(text_parts)

        if len(full_text) > 10000:
            full_text = full_text[:10000] + "\n...(内容已截断)"

        logger.info("PDF 解析完成: path='{}', 页数={}", file_path, len(reader.pages))
        return full_text or "PDF 文件无法提取文本内容。"

    except Exception as e:
        logger.error("PDF 解析失败: path='{}', 错误={}", file_path, e)
        return f"PDF 解析失败: {e}"
