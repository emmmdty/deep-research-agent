"""本地文件 ingestor。"""

from __future__ import annotations

from pathlib import Path

from connectors.models import ConnectorFetchResult
from connectors.utils import canonicalize_uri

from tools.pdf_reader import pdf_reader_tool


class LocalFileIngestor:
    """解析本地文件为统一 fetch 结果。"""

    SUPPORTED_SUFFIXES = {".pdf", ".md", ".txt"}

    connector_name = "files"

    def ingest(self, path: str, *, query: str = "") -> ConnectorFetchResult:
        file_path = Path(path).resolve()
        suffix = file_path.suffix.lower()
        if suffix not in self.SUPPORTED_SUFFIXES:
            raise ValueError(f"不支持的文件类型: {suffix}")
        if suffix == ".pdf":
            text = pdf_reader_tool.invoke({"file_path": str(file_path)})
            mime_type = "application/pdf"
        else:
            text = file_path.read_text(encoding="utf-8")
            mime_type = "text/markdown" if suffix == ".md" else "text/plain"
        return ConnectorFetchResult(
            connector_name=self.connector_name,
            source_type="files",
            title=file_path.name,
            canonical_uri=canonicalize_uri(str(file_path)),
            query=query,
            text=text,
            snippet=text[:300].replace("\n", " "),
            mime_type=mime_type,
            auth_scope="private",
            freshness_metadata={"file_name": file_path.name, "file_path": str(file_path)},
            metadata={"file_path": str(file_path)},
            url=file_path.as_uri(),
        )
