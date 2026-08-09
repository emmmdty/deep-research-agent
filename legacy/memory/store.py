"""研究记忆存储——管理 workspace、notes、sources、summaries 的持久化。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from loguru import logger


class MemoryStore:
    """研究记忆管理器，将中间结果持久化到文件系统。

    目录结构：
        workspace/
        ├── notes/       # 研究笔记
        ├── sources/     # 来源记录
        └── summaries/   # 任务总结
    """

    def __init__(self, workspace_dir: str = "workspace") -> None:
        self.root = Path(workspace_dir)
        self.notes_dir = self.root / "notes"
        self.sources_dir = self.root / "sources"
        self.summaries_dir = self.root / "summaries"

        # 创建目录
        for d in [self.notes_dir, self.sources_dir, self.summaries_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def save_note(self, title: str, content: str, topic: str = "") -> Path:
        """保存研究笔记。"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{_sanitize(title)}.md"
        filepath = self.notes_dir / filename

        header = f"# {title}\n\n"
        if topic:
            header += f"**研究主题**: {topic}\n\n"
        header += f"**创建时间**: {datetime.now().isoformat()}\n\n---\n\n"

        filepath.write_text(header + content, encoding="utf-8")
        logger.info("📝 笔记已保存: {}", filepath)
        return filepath

    def save_sources(self, topic: str, sources: list[str]) -> Path:
        """保存来源记录。"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{_sanitize(topic)}_sources.json"
        filepath = self.sources_dir / filename

        data = {
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "sources": sources,
        }
        filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("📚 来源已保存: {}", filepath)
        return filepath

    def save_summary(self, topic: str, summary: str) -> Path:
        """保存任务总结。"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{_sanitize(topic)}.md"
        filepath = self.summaries_dir / filename

        filepath.write_text(summary, encoding="utf-8")
        logger.info("📋 总结已保存: {}", filepath)
        return filepath

    def list_notes(self) -> list[Path]:
        """列出所有研究笔记。"""
        return sorted(self.notes_dir.glob("*.md"), reverse=True)

    def list_summaries(self) -> list[Path]:
        """列出所有任务总结。"""
        return sorted(self.summaries_dir.glob("*.md"), reverse=True)


def _sanitize(text: str) -> str:
    """清理文件名中的非法字符。"""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text[:30])
