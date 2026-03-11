"""成本与性能追踪器——记录 API 调用次数、Token 消耗和耗时。"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from loguru import logger


@dataclass
class CostMetrics:
    """单次研究任务的成本指标。"""

    total_time_seconds: float = 0.0
    llm_calls: int = 0
    search_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """总 Token 消耗。"""
        return self.total_input_tokens + self.total_output_tokens

    @property
    def estimated_cost_usd(self) -> float:
        """估算美元成本（基于 MiniMax 定价：约 $0.001/1K tokens）。"""
        return round(self.total_tokens * 0.001 / 1000, 4)

    def to_dict(self) -> dict:
        """转为字典。"""
        return {
            "total_time_seconds": round(self.total_time_seconds, 2),
            "llm_calls": self.llm_calls,
            "search_calls": self.search_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
        }


class CostTracker:
    """全局成本追踪器——使用上下文管理器记录单次研究的开销。"""

    def __init__(self) -> None:
        self._metrics = CostMetrics()
        self._start_time: Optional[float] = None

    @property
    def metrics(self) -> CostMetrics:
        return self._metrics

    @property
    def is_running(self) -> bool:
        """是否处于计时中。"""
        return self._start_time is not None

    def start(self) -> None:
        """开始计时。"""
        self._start_time = time.time()
        self._metrics = CostMetrics()

    def stop(self) -> CostMetrics:
        """停止计时并返回指标。"""
        if self._start_time is not None:
            self._metrics.total_time_seconds = time.time() - self._start_time
        self._start_time = None
        logger.info(
            "📊 成本追踪: time={:.1f}s, llm_calls={}, search_calls={}, tokens={}",
            self._metrics.total_time_seconds,
            self._metrics.llm_calls,
            self._metrics.search_calls,
            self._metrics.total_tokens,
        )
        return self._metrics

    def snapshot(self) -> CostMetrics:
        """返回当前指标快照。"""
        if self._start_time is not None:
            self._metrics.total_time_seconds = time.time() - self._start_time
        return self._metrics

    def record_llm_call(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        """记录一次 LLM API 调用。"""
        self._metrics.llm_calls += 1
        self._metrics.total_input_tokens += input_tokens
        self._metrics.total_output_tokens += output_tokens

    def record_search_call(self) -> None:
        """记录一次搜索 API 调用。"""
        self._metrics.search_calls += 1

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# 全局追踪器实例
_tracker: CostTracker | None = None


def get_tracker() -> CostTracker:
    """获取全局成本追踪器。"""
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
    return _tracker
