"""Cost and performance tracker used by providers and connector tools.

Records are attributed to the job bound in the ``research.job_id`` contextvar
(set by the orchestration boundary), with calls outside any job bucketed under
``"global"``. Optional Prometheus counters/gauges are updated lazily so the
``/metrics`` endpoint works without a hard dependency.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Mapping
from contextvars import ContextVar, Token
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

JOB_ID_CONTEXT: ContextVar[str] = ContextVar("research.job_id", default="global")

_DEFAULT_PRICE_TABLE: dict[str, dict[str, float]] = {
    "default": {"in_per_million": 1.0, "out_per_million": 1.0}
}

# Lazily built Prometheus state: (registry, counters, gauges). Kept at module
# scope so tests can swap in an isolated registry deterministically.
_REGISTRY: Any = None
_COUNTERS: dict[str, Any] | None = None
_GAUGES: dict[str, Any] | None = None
_PROMETHEUS_UNAVAILABLE = False


def current_job_id() -> str:
    """Return the job id attributed to the current orchestration context."""
    return JOB_ID_CONTEXT.get()


def set_job_id(job_id: str) -> Token[str]:
    """Bind the contextvar to a job id; reset with :func:`reset_job_id`."""
    return JOB_ID_CONTEXT.set(job_id)


def reset_job_id(token: Token[str]) -> None:
    """Restore the previous contextvar binding from a ``set_job_id`` token."""
    JOB_ID_CONTEXT.reset(token)


@dataclass
class CostMetrics:
    """Cost metrics for one research task."""

    total_time_seconds: float = 0.0
    llm_calls: int = 0
    search_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    by_model: dict[str, dict[str, int]] = field(default_factory=dict)
    price_table: dict[str, dict[str, float]] = field(default_factory=dict, repr=False)

    @property
    def total_tokens(self) -> int:
        """Total token count."""
        return self.total_input_tokens + self.total_output_tokens

    @property
    def estimated_cost_usd(self) -> float:
        """Estimated USD cost from the injected per-model price table.

        The default price table reproduces the legacy flat approximation
        (1 USD per million tokens in either direction).
        """
        table = self.price_table or _DEFAULT_PRICE_TABLE
        default_price = table.get("default", _DEFAULT_PRICE_TABLE["default"])
        total = 0.0
        for model, usage in self.by_model.items():
            price = table.get(model) or default_price
            total += (
                usage["in"] * float(price["in_per_million"])
                + usage["out"] * float(price["out_per_million"])
            ) / 1_000_000
        return round(total, 4)

    def to_dict(self) -> dict:
        """Return a JSON-serializable dict."""
        return {
            "total_time_seconds": round(self.total_time_seconds, 2),
            "llm_calls": self.llm_calls,
            "search_calls": self.search_calls,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "by_model": self.by_model,
        }


def _prometheus_state() -> tuple[Any, dict[str, Any], dict[str, Any]] | None:
    """Return the lazily built Prometheus state, or None when unavailable."""
    global _REGISTRY, _COUNTERS, _GAUGES, _PROMETHEUS_UNAVAILABLE
    if _PROMETHEUS_UNAVAILABLE:
        return None
    if _COUNTERS is not None:
        return _REGISTRY, _COUNTERS, _GAUGES
    try:
        from prometheus_client import CollectorRegistry, Counter, Gauge
    except ImportError:
        _PROMETHEUS_UNAVAILABLE = True
        return None
    _REGISTRY = CollectorRegistry()
    _COUNTERS = {
        "llm_calls": Counter(
            "research_llm_calls_total",
            "Total LLM chat completions",
            registry=_REGISTRY,
        ),
        "search_calls": Counter(
            "research_search_calls_total",
            "Total search connector calls",
            registry=_REGISTRY,
        ),
        "tokens": Counter(
            "research_tokens_total",
            "Token usage by direction",
            ["kind"],
            registry=_REGISTRY,
        ),
        "estimated_cost_usd": Counter(
            "research_estimated_cost_usd_total",
            "Accumulated estimated LLM cost in USD",
            registry=_REGISTRY,
        ),
    }
    _GAUGES = {
        "estimated_cost_usd": Gauge(
            "research_estimated_cost_usd",
            "Estimated LLM cost in USD (latest tracker snapshot)",
            registry=_REGISTRY,
        ),
        "task_runtime_seconds": Gauge(
            "research_task_runtime_seconds",
            "Tracked runtime in seconds (latest tracker snapshot)",
            registry=_REGISTRY,
        ),
    }
    return _REGISTRY, _COUNTERS, _GAUGES


def prometheus_registry() -> Any | None:
    """Return the isolated Prometheus registry, or None when unavailable."""
    state = _prometheus_state()
    if state is None:
        return None
    return state[0]


def refresh_prometheus_gauges() -> None:
    """Push the global tracker snapshot into the Prometheus gauges (no-op offline)."""
    state = _prometheus_state()
    if state is None:
        return
    _registry, _counters, gauges = state
    snapshot = _tracker.snapshot() if _tracker is not None else CostMetrics()
    gauges["estimated_cost_usd"].set(snapshot.estimated_cost_usd)
    gauges["task_runtime_seconds"].set(snapshot.total_time_seconds)


def _record_prometheus_llm_call(
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
) -> None:
    state = _prometheus_state()
    if state is None:
        return
    _registry, counters, _gauges = state
    counters["llm_calls"].inc()
    counters["tokens"].labels(kind="input").inc(input_tokens)
    counters["tokens"].labels(kind="output").inc(output_tokens)
    counters["estimated_cost_usd"].inc(cost_usd)


def _record_prometheus_search_call() -> None:
    state = _prometheus_state()
    if state is None:
        return
    _registry, counters, _gauges = state
    counters["search_calls"].inc()


class CostTracker:
    """Global cost tracker with contextvar per-job attribution support.

    Mutations are guarded by a lock so concurrent jobs (e.g. gateway threads
    recording search calls) do not drop counters.
    """

    def __init__(
        self,
        price_table: Mapping[str, Mapping[str, float]] | None = None,
    ) -> None:
        self._price_table = dict(price_table) if price_table else {}
        self._metrics = CostMetrics(price_table=self._price_table)
        self._per_job: dict[str, CostMetrics] = {}
        self._start_time: float | None = None
        self._lock = threading.Lock()

    @property
    def metrics(self) -> CostMetrics:
        return self._metrics

    @property
    def is_running(self) -> bool:
        """Whether timing is active."""
        return self._start_time is not None

    def start(self) -> None:
        """Start timing and reset metrics."""
        with self._lock:
            self._start_time = time.time()
            self._metrics = CostMetrics(price_table=self._price_table)
            self._per_job.clear()

    def stop(self) -> CostMetrics:
        """Stop timing and return metrics."""
        with self._lock:
            if self._start_time is not None:
                self._metrics.total_time_seconds = time.time() - self._start_time
            self._start_time = None
            metrics = self._metrics
        logger.info(
            "Cost tracker: time={:.1f}s, llm_calls={}, search_calls={}, tokens={}",
            metrics.total_time_seconds,
            metrics.llm_calls,
            metrics.search_calls,
            metrics.total_tokens,
        )
        return metrics

    def snapshot(self) -> CostMetrics:
        """Return current metrics."""
        with self._lock:
            if self._start_time is not None:
                self._metrics.total_time_seconds = time.time() - self._start_time
            return self._metrics

    def snapshot_for(self, job_id: str) -> CostMetrics:
        """Return a copied snapshot for one job (empty when absent).

        返回拷贝而非活对象：调用方（bundle 编译线程）与 worker 线程的
        record_* 并发时，活对象上的 to_dict() 会在无锁迭代中看到变化。
        """
        with self._lock:
            current = self._per_job.setdefault(job_id, CostMetrics(price_table=self._price_table))
            return deepcopy(current)

    def reset_for(self, job_id: str) -> None:
        """Clear the metrics recorded for one job."""
        with self._lock:
            self._per_job[job_id] = CostMetrics(price_table=self._price_table)

    def _llm_call_cost_usd(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str | None,
    ) -> float:
        table = self._price_table or _DEFAULT_PRICE_TABLE
        default_price = table.get("default", _DEFAULT_PRICE_TABLE["default"])
        price = table.get(model or "default") or default_price
        return (
            input_tokens * float(price["in_per_million"])
            + output_tokens * float(price["out_per_million"])
        ) / 1_000_000

    @staticmethod
    def _record_llm(
        metrics: CostMetrics,
        input_tokens: int,
        output_tokens: int,
        model: str | None,
    ) -> None:
        metrics.llm_calls += 1
        metrics.total_input_tokens += input_tokens
        metrics.total_output_tokens += output_tokens
        usage = metrics.by_model.setdefault(model or "default", {"in": 0, "out": 0})
        usage["in"] += input_tokens
        usage["out"] += output_tokens

    def record_llm_call(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        *,
        model: str | None = None,
    ) -> None:
        """Record one LLM call attributed to the current job context."""
        with self._lock:
            self._record_llm(self._metrics, input_tokens, output_tokens, model)
            job = self._per_job.setdefault(
                current_job_id(), CostMetrics(price_table=self._price_table)
            )
            self._record_llm(job, input_tokens, output_tokens, model)
        _record_prometheus_llm_call(
            input_tokens,
            output_tokens,
            self._llm_call_cost_usd(input_tokens, output_tokens, model),
        )

    def record_search_call(self) -> None:
        """Record one search call attributed to the current job context."""
        with self._lock:
            self._metrics.search_calls += 1
            job = self._per_job.setdefault(
                current_job_id(), CostMetrics(price_table=self._price_table)
            )
            job.search_calls += 1
        _record_prometheus_search_call()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


_tracker: CostTracker | None = None


def get_tracker() -> CostTracker:
    """Return the global cost tracker."""
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
    return _tracker
