"""Registry for supported external benchmarks."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module


@dataclass(frozen=True)
class BenchmarkDescriptor:
    """Static registration info for one benchmark."""

    benchmark: str
    title: str
    adapter_mode: str
    role: str
    module_path: str
    config_path: str | None = None
    integrity_guards: tuple[str, ...] = ()


_DESCRIPTORS = {
    "facts_grounding": BenchmarkDescriptor(
        benchmark="facts_grounding",
        title="FACTS Grounding",
        adapter_mode="facts_doc_grounded_longform",
        role="secondary_regression",
        module_path="deep_research_agent.evals.external.benchmarks.facts_grounding",
        config_path="evals/external/configs/facts_grounding_open_smoke.yaml",
        integrity_guards=("public_private_split_separation",),
    ),
    "longfact_safe": BenchmarkDescriptor(
        benchmark="longfact_safe",
        title="LongFact / SAFE",
        adapter_mode="longfact_safe_open_domain_longform",
        role="external_regression",
        module_path="deep_research_agent.evals.external.benchmarks.longfact_safe",
        config_path="evals/external/configs/longfact_safe_smoke.yaml",
        integrity_guards=("search_trace_cache", "judge_backend_logging"),
    ),
    "longbench_v2": BenchmarkDescriptor(
        benchmark="longbench_v2",
        title="LongBench v2",
        adapter_mode="longbench_mcq_longcontext",
        role="external_regression",
        module_path="deep_research_agent.evals.external.benchmarks.longbench_v2",
        config_path="evals/external/configs/longbench_v2_short_smoke.yaml",
        integrity_guards=("bucket_assignment_logging", "truncation_detection"),
    ),
    "browsecomp": BenchmarkDescriptor(
        benchmark="browsecomp",
        title="BrowseComp",
        adapter_mode="browsecomp_short_answer",
        role="challenge_track",
        module_path="deep_research_agent.evals.external.benchmarks.browsecomp",
        config_path="evals/external/configs/browsecomp_guarded_smoke.yaml",
        integrity_guards=(
            "benchmark_material_denylist",
            "canary_string_detection",
            "query_redaction",
            "integrity_findings_manifest",
        ),
    ),
    "gaia": BenchmarkDescriptor(
        benchmark="gaia",
        title="GAIA",
        adapter_mode="gaia_capability_gated",
        role="challenge_track",
        module_path="deep_research_agent.evals.external.benchmarks.gaia",
        config_path="evals/external/configs/gaia_supported_smoke.yaml",
        integrity_guards=("capability_filter", "attachment_path_sanitization"),
    ),
}


def get_benchmark_descriptor(benchmark_name: str) -> BenchmarkDescriptor:
    """Return the static descriptor for one benchmark id."""

    try:
        return _DESCRIPTORS[benchmark_name]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"unsupported benchmark: {benchmark_name}") from exc


def load_benchmark_runner(benchmark_name: str):
    """Load the module-level run function for one benchmark."""

    descriptor = get_benchmark_descriptor(benchmark_name)
    module = import_module(descriptor.module_path)
    return descriptor, module.run_benchmark
