"""Credential-safe OpenTelemetry setup and research span helpers."""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

ATTRIBUTE_NAMES = {
    "job_id": "research.job_id",
    "task_id": "research.task_id",
    "role": "research.role",
    "endpoint_id": "research.endpoint_id",
    "model": "research.model",
    "tool": "research.tool",
    "latency_ms": "research.latency_ms",
    "input_tokens": "research.input_tokens",
    "output_tokens": "research.output_tokens",
    "cost_usd": "research.cost_usd",
    "retry_count": "research.retry_count",
    "artifact_ids": "research.artifact_ids",
}


def sanitize_trace_attributes(attributes: Mapping[str, Any]) -> dict[str, Any]:
    """Return only identifiers and aggregate telemetry approved for export."""

    sanitized: dict[str, Any] = {}
    for source_name, target_name in ATTRIBUTE_NAMES.items():
        value = attributes.get(source_name)
        if value is None:
            continue
        if source_name == "artifact_ids":
            if not isinstance(value, (list, tuple)):
                continue
            value = tuple(str(item) for item in value if str(item).strip())
        elif not isinstance(value, (str, bool, int, float)):
            continue
        sanitized[target_name] = value
    return sanitized


def configure_tracing(*, service_name: str = "deep-research-agent"):
    """Configure OTLP export when an endpoint is explicit, otherwise stay no-op.

    幂等：重复调用（worker/网关/测试多次启动）不得替换 TracerProvider——
    新 provider 会让上一个 BatchSpanProcessor 的缓冲 span 全部丢失。
    """

    from opentelemetry import trace

    current = trace.get_tracer_provider()
    if getattr(current, "_dra_configured_service", None) == service_name:
        return trace.get_tracer(service_name)

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    disabled = os.environ.get("OTEL_SDK_DISABLED", "").strip().casefold() in {"1", "true", "yes"}
    if not endpoint or disabled:
        return trace.get_tracer(service_name)

    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:  # pragma: no cover - dependency packaging guard
        raise RuntimeError(
            "OTLP endpoint configured but OpenTelemetry SDK/exporter is unavailable"
        ) from exc

    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    marker = trace.get_tracer_provider()
    with contextlib.suppress(Exception):
        marker._dra_configured_service = service_name  # type: ignore[attr-defined]
    return trace.get_tracer(service_name)


@contextmanager
def research_span(
    name: str,
    attributes: Mapping[str, Any],
    *,
    tracer=None,
) -> Iterator[Any]:
    """Start a span with the strict research telemetry attribute allowlist."""

    from opentelemetry import trace

    selected_tracer = tracer or trace.get_tracer("deep-research-agent")
    with selected_tracer.start_as_current_span(
        name,
        attributes=sanitize_trace_attributes(attributes),
    ) as span:
        yield span


__all__ = [
    "ATTRIBUTE_NAMES",
    "configure_tracing",
    "research_span",
    "sanitize_trace_attributes",
]
