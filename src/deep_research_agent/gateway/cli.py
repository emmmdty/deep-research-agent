"""Deep Research Agent 主入口。

phase2 起，公开 CLI 入口改为 job orchestrator：
    uv run python main.py submit --topic "可信深度研究 app"
    uv run python main.py watch --job-id <job_id>

legacy 直跑路径保留为内部 helper `run_cli()`，并通过 hidden subcommand 暂时兼容。
"""

from __future__ import annotations

import argparse
import inspect
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from dotenv import load_dotenv
from loguru import logger
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from configs.settings import get_settings
from deep_research_agent.common import CANONICAL_SOURCE_PROFILES
from deep_research_agent.evals import (
    BENCHMARK_NAMES,
    EVAL_SUITE_NAMES,
    EVAL_VARIANT_NAMES,
    run_eval_suite,
    run_external_benchmark,
)
from deep_research_agent.gateway.artifacts import (
    ARTIFACT_NAME_CHOICES,
    artifact_path_for_job,
    load_json_artifact,
)
from deep_research_agent.gateway.batch import load_batch_requests

if TYPE_CHECKING:
    from deep_research_agent.kernel.contracts import ResearchBrief
    from deep_research_agent.orchestration.dag import ResearchDAG
    from deep_research_agent.research_jobs.models import JobRuntimeRecord

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# 加载 .env 文件（优先 cwd，其次项目根目录）
for env_candidate in (Path.cwd() / ".env", PROJECT_ROOT / ".env"):
    if env_candidate.exists():
        load_dotenv(env_candidate)
        break

logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:^8}</level> | <cyan>{message}</cyan>",
    level="INFO",
)

console = Console()


def _load_run_research():
    """懒加载 legacy 研究工作流执行函数。"""
    from legacy.workflows.graph import run_research

    return run_research


def _build_job_service():
    """构建 phase2 job service。"""
    from deep_research_agent.research_jobs import ResearchJobService

    return ResearchJobService()


_DEFAULT_DOMAIN_PACK_ID = "event-graph-agents-llms"


def _plan_cli_dag(topic: str, settings) -> tuple[ResearchDAG, ResearchBrief]:
    """Plan a scheduler-v2 DAG for a CLI topic.

    Mirrors the product service composition: the LLM planner is used when
    explicitly enabled and credentials exist; otherwise the deterministic
    planner compiles the topic into typed research tasks. The returned brief
    is pre-frozen with a pending job id; ``submit_scheduler_v2`` rebinds it to
    the durable job id.
    """
    from deep_research_agent.domain_packs.registry import DomainPackRegistry
    from deep_research_agent.kernel.contracts import ResearchBrief

    domain_pack_id = getattr(settings, "domain_pack_id", None) or _DEFAULT_DOMAIN_PACK_ID
    try:
        domain_pack = DomainPackRegistry().load(domain_pack_id)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"无法加载 domain pack {domain_pack_id!r}（{exc}）") from exc
    brief = ResearchBrief(
        brief_id="cli-brief",
        job_id="pending",
        question=topic,
        domain_pack_id=domain_pack_id,
        objectives=[topic],
        constraints={"source": "cli"},
    )
    planner_enabled = bool(
        getattr(settings, "agent_planner_enabled", True) and getattr(settings, "llm_api_key", None)
    )
    if planner_enabled:
        from deep_research_agent.agents import LLMResearchPlanner

        dag = LLMResearchPlanner(settings=settings).plan(brief, domain_pack)
    else:
        from deep_research_agent.orchestration.dag import ResearchPlanner

        dag = ResearchPlanner(settings=settings).plan(brief, domain_pack)
    return dag, brief


def _submit_cli_v2(
    service,
    *,
    topic: str,
    max_loops: int,
    source_profile: str | None,
    allow_domains: list[str],
    deny_domains: list[str],
    connector_budget: dict | None,
    start_worker: bool,
    settings,
) -> JobRuntimeRecord:
    """Submit a scheduler-v2 job from a CLI topic."""
    dag, brief = _plan_cli_dag(topic, settings)
    config_snapshot = {
        "domain_pack_id": brief.domain_pack_id,
        "objectives": brief.objectives,
        "max_loops": max_loops,
        "source_profile": source_profile,
        "allow_domains": allow_domains,
        "deny_domains": deny_domains,
    }
    if connector_budget:
        config_snapshot["connector_budget"] = connector_budget
    return service.submit_scheduler_v2(
        brief=brief,
        dag=dag,
        config_snapshot=config_snapshot,
        start_worker=start_worker,
        source_profile=source_profile,
        max_loops=max_loops,
        allow_domains=allow_domains,
        deny_domains=deny_domains,
        connector_budget=connector_budget,
        runtime_metadata={"cli_submitted": True},
    )


_MAX_TOPIC_CHARS = 2000


def _validate_topic(topic: str) -> str:
    """Normalize and gate a research topic before it reaches the runtime.

    Blank, whitespace-only, and oversized topics are rejected up front so no
    research budget is spent on inputs that cannot produce a report.
    """

    if not isinstance(topic, str):
        raise ValueError("研究主题必须是文本")
    normalized = topic.strip()
    if not normalized:
        raise ValueError("研究主题不能为空")
    if len(normalized) > _MAX_TOPIC_CHARS:
        raise ValueError(f"研究主题过长（{len(normalized)} 字符，上限 {_MAX_TOPIC_CHARS}）")
    return normalized


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""
    settings = get_settings()
    default_max_loops = getattr(settings, "max_research_loops", 3)
    default_profile = getattr(settings, "research_profile", "default")
    default_source_profile = getattr(settings, "source_policy_mode", "company_broad")
    parser = argparse.ArgumentParser(
        description="Deep Research Agent — evidence-first research runtime",
    )
    subparsers = parser.add_subparsers(dest="command")

    submit_parser = subparsers.add_parser("submit", help="提交一个 research job")
    submit_parser.add_argument("--topic", required=True, type=str, help="研究主题")
    submit_parser.add_argument(
        "--max-loops",
        type=int,
        default=default_max_loops,
        help=f"最大迭代循环次数（默认 {default_max_loops}）",
    )
    submit_parser.add_argument(
        "--profile",
        type=str,
        default=default_profile,
        help=f"研究 profile（默认 {default_profile}）",
    )
    submit_parser.add_argument(
        "--source-profile",
        type=str,
        default=default_source_profile,
        choices=CANONICAL_SOURCE_PROFILES,
        help=f"来源策略 profile（默认 {default_source_profile}）",
    )
    submit_parser.add_argument(
        "--legacy",
        action="store_true",
        help="使用 legacy orchestrator-v1 管线（默认 scheduler-v2）",
    )
    submit_parser.add_argument(
        "--allow-domain", action="append", default=[], help="额外允许的域名，可重复"
    )
    submit_parser.add_argument(
        "--deny-domain", action="append", default=[], help="额外禁止的域名，可重复"
    )
    submit_parser.add_argument(
        "--max-candidates-per-connector",
        type=int,
        default=None,
        help="单个 connector 的最大候选数覆盖",
    )
    submit_parser.add_argument(
        "--max-fetches-per-task",
        type=int,
        default=None,
        help="单个任务的最大 fetch 数覆盖",
    )
    submit_parser.add_argument(
        "--max-total-fetches",
        type=int,
        default=None,
        help="单个 job 的最大 fetch 总数覆盖",
    )
    submit_parser.add_argument(
        "--no-worker",
        action="store_true",
        help="只创建 job，不启动后台 worker",
    )
    submit_parser.add_argument("--json", action="store_true", help="输出 JSON")

    status_parser = subparsers.add_parser("status", help="查询 job 状态")
    status_parser.add_argument("--job-id", required=True, type=str, help="job ID")
    status_parser.add_argument("--json", action="store_true", help="输出 JSON")

    watch_parser = subparsers.add_parser("watch", help="持续观察 job 直到结束")
    watch_parser.add_argument("--job-id", required=True, type=str, help="job ID")
    watch_parser.add_argument("--poll-interval", type=float, default=1.0, help="轮询间隔秒数")
    watch_parser.add_argument("--json", action="store_true", help="输出 JSON Lines")

    cancel_parser = subparsers.add_parser("cancel", help="请求取消 job")
    cancel_parser.add_argument("--job-id", required=True, type=str, help="job ID")
    cancel_parser.add_argument("--json", action="store_true", help="输出 JSON")

    retry_parser = subparsers.add_parser("retry", help="基于旧 job 创建 retry")
    retry_parser.add_argument("--job-id", required=True, type=str, help="原 job ID")
    retry_parser.add_argument(
        "--no-worker", action="store_true", help="只创建 retry job，不启动后台 worker"
    )
    retry_parser.add_argument("--json", action="store_true", help="输出 JSON")

    resume_parser = subparsers.add_parser("resume", help="从最新 checkpoint 恢复同一个 job")
    resume_parser.add_argument("--job-id", required=True, type=str, help="job ID")
    resume_parser.add_argument(
        "--no-worker", action="store_true", help="只恢复状态，不启动后台 worker"
    )
    resume_parser.add_argument("--json", action="store_true", help="输出 JSON")

    refine_parser = subparsers.add_parser("refine", help="记录 refinement 指令并从安全边界恢复")
    refine_parser.add_argument("--job-id", required=True, type=str, help="job ID")
    refine_parser.add_argument("--instruction", required=True, type=str, help="refinement 指令")
    refine_parser.add_argument(
        "--no-worker", action="store_true", help="只更新状态，不启动后台 worker"
    )
    refine_parser.add_argument("--json", action="store_true", help="输出 JSON")

    bundle_parser = subparsers.add_parser("bundle", help="读取 job bundle 或 sidecar artifacts")
    bundle_parser.add_argument("--job-id", required=True, type=str, help="job ID")
    bundle_parser.add_argument(
        "--artifact-name",
        type=str,
        default="report_bundle.json",
        choices=ARTIFACT_NAME_CHOICES,
        help="要读取的 artifact 名称（默认 report_bundle.json）",
    )
    bundle_parser.add_argument(
        "--json", action="store_true", help="将 JSON artifact 以结构化 JSON 输出"
    )

    batch_parser = subparsers.add_parser("batch", help="批量 research job 操作")
    batch_subparsers = batch_parser.add_subparsers(dest="batch_command")
    batch_run_parser = batch_subparsers.add_parser("run", help="从 JSON/JSONL 文件批量创建 job")
    batch_run_parser.add_argument(
        "--file", required=True, type=str, help="JSON 或 JSONL batch 文件路径"
    )
    batch_run_parser.add_argument("--json", action="store_true", help="输出结构化 JSON")

    eval_parser = subparsers.add_parser("eval", help="运行本地 deterministic eval suites")
    eval_subparsers = eval_parser.add_subparsers(dest="eval_command")
    eval_run_parser = eval_subparsers.add_parser("run", help="执行一个 local eval suite")
    eval_run_parser.add_argument(
        "--suite", required=True, choices=EVAL_SUITE_NAMES, help="suite 名称"
    )
    eval_run_parser.add_argument(
        "--variant",
        default="smoke_local",
        choices=EVAL_VARIANT_NAMES,
        help="suite variant，默认 smoke_local",
    )
    eval_run_parser.add_argument("--output-root", type=str, default=None, help="suite 输出目录")
    eval_run_parser.add_argument(
        "--capture-runtime-metrics",
        action="store_true",
        help="在 fresh rerun 中保存 pre-normalization runtime timing sidecar",
    )
    eval_run_parser.add_argument("--json", action="store_true", help="输出结构化 JSON")

    eval_human_parser = eval_subparsers.add_parser(
        "human-sample", help="人工抽检：采样评审单 / 导入评分生成 scorecard"
    )
    eval_human_parser.add_argument(
        "--bundle-dir", required=True, type=str, help="包含 report_bundle.json 的目录"
    )
    eval_human_parser.add_argument(
        "--sample-size", type=int, default=3, help="每个 bundle 抽检声明数（默认 3）"
    )
    eval_human_parser.add_argument("--seed", type=int, default=0, help="采样随机种子（默认 0）")
    eval_human_parser.add_argument(
        "--import",
        dest="import_file",
        type=str,
        default=None,
        help="导入已完成评分文件（YAML）并生成 scorecard",
    )

    benchmark_parser = subparsers.add_parser("benchmark", help="运行 external benchmark portfolio")
    benchmark_subparsers = benchmark_parser.add_subparsers(dest="benchmark_command")
    benchmark_run_parser = benchmark_subparsers.add_parser(
        "run", help="执行一个 external benchmark run"
    )
    benchmark_run_parser.add_argument(
        "--benchmark", required=True, choices=BENCHMARK_NAMES, help="benchmark 名称"
    )
    benchmark_run_parser.add_argument(
        "--split", type=str, default=None, help="benchmark split，例如 open"
    )
    benchmark_run_parser.add_argument(
        "--subset", type=str, default="smoke", help="subset 名称，例如 smoke"
    )
    benchmark_run_parser.add_argument(
        "--bucket", type=str, default=None, help="可选 context bucket"
    )
    benchmark_run_parser.add_argument(
        "--config", type=str, default=None, help="可选 benchmark 配置路径"
    )
    benchmark_run_parser.add_argument(
        "--output-root", type=str, default=None, help="benchmark 输出目录"
    )
    benchmark_run_parser.add_argument("--json", action="store_true", help="输出结构化 JSON")

    return parser


def _build_legacy_parser() -> argparse.ArgumentParser:
    """构建 hidden legacy-run 解析器。"""
    settings = get_settings()
    default_max_loops = getattr(settings, "max_research_loops", 3)
    default_profile = getattr(settings, "research_profile", "default")
    parser = argparse.ArgumentParser(prog="main.py legacy-run")
    parser.add_argument("--topic", required=True, type=str, help="研究主题")
    parser.add_argument(
        "--max-loops",
        type=int,
        default=default_max_loops,
        help=f"最大迭代循环次数（默认 {default_max_loops}）",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=default_profile,
        help=f"研究 profile（默认 {default_profile}）",
    )
    return parser


def run_cli(
    topic: str,
    max_loops: int | None = None,
    profile: str | None = None,
    emit_bundle: bool | None = None,
    run_research_fn=None,
) -> Path:
    """legacy helper：命令行模式直跑深度研究并输出报告。"""
    settings = get_settings()
    resolved_max_loops = (
        max_loops if max_loops is not None else getattr(settings, "max_research_loops", 3)
    )
    resolved_profile = profile or getattr(settings, "research_profile", "default")
    resolved_emit_bundle = (
        emit_bundle
        if emit_bundle is not None
        else getattr(settings, "bundle_emission_enabled", True)
    )
    research_runner = run_research_fn or _load_run_research()

    console.print(
        Panel(
            f"[bold cyan]研究主题:[/bold cyan] {topic}\n"
            f"[bold cyan]最大迭代:[/bold cyan] {resolved_max_loops} 次\n"
            f"[bold cyan]运行 Profile:[/bold cyan] {resolved_profile}",
            title="🔬 Deep Research Agent",
            border_style="blue",
        )
    )
    console.print()

    signature = inspect.signature(research_runner)
    if "research_profile" in signature.parameters:
        result = research_runner(
            topic,
            max_loops=resolved_max_loops,
            research_profile=resolved_profile,
        )
    else:
        result = research_runner(
            topic,
            max_loops=resolved_max_loops,
        )

    report = result.get("final_report", "报告生成失败")
    console.print()
    console.print(Panel("[bold green]✅ 研究完成[/bold green]", border_style="green"))
    console.print()
    console.print(Markdown(report))

    output_dir = Path(getattr(settings, "workspace_dir", "workspace"))
    output_dir.mkdir(parents=True, exist_ok=True)
    # 白名单净化：路径分隔符/控制字符一律替换，中文保留（仓库双语），
    # 再校验净化结果不能是相对路径段（防 ../ 逃逸 workspace_dir）。
    safe_topic = re.sub(r"[^A-Za-z0-9_.\-\u4e00-\u9fff]", "_", topic[:20])
    if not safe_topic or safe_topic in {".", ".."} or Path(safe_topic).name != safe_topic:
        safe_topic = "research"
    output_file = output_dir / f"report_{safe_topic}.md"
    output_file.write_text(report, encoding="utf-8")
    console.print(f"\n📄 报告已保存到: [cyan]{output_file}[/cyan]")

    if resolved_emit_bundle:
        from deep_research_agent.reporting.bundle import emit_report_artifacts

        artifact_paths = emit_report_artifacts(
            result,
            topic=topic,
            max_loops=resolved_max_loops,
            research_profile=resolved_profile,
            workspace_dir=output_dir,
            bundle_output_dirname=getattr(settings, "bundle_output_dirname", "bundles"),
            source_profile=getattr(settings, "source_policy_mode", "legacy-default"),
            report_path=output_file,
        )
        if artifact_paths is not None:
            console.print(f"🧾 Bundle 已保存到: [cyan]{artifact_paths['bundle_path']}[/cyan]")
            console.print(f"🪵 Trace 已保存到: [cyan]{artifact_paths['trace_path']}[/cyan]")
    return output_file


def _print_json(payload) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _jsonable_model(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "__dict__"):
        return dict(value.__dict__)
    return value


def _connector_budget_from_args(args) -> dict | None:
    payload: dict[str, int] = {}
    if getattr(args, "max_candidates_per_connector", None) is not None:
        payload["max_candidates_per_connector"] = int(args.max_candidates_per_connector)
    if getattr(args, "max_fetches_per_task", None) is not None:
        payload["max_fetches_per_task"] = int(args.max_fetches_per_task)
    if getattr(args, "max_total_fetches", None) is not None:
        payload["max_total_fetches"] = int(args.max_total_fetches)
    return payload or None


def _artifact_payload(job, artifact_name: str):
    path = artifact_path_for_job(job, artifact_name)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix == ".json":
        return load_json_artifact(path)
    return path.read_text(encoding="utf-8")


_HUMAN_REVIEW_OUTPUT_DIR = Path("evals") / "reports" / "human_review"
_HUMAN_REVIEW_RUBRIC_REL = Path("evals") / "rubrics" / "citation_authenticity.yaml"


def _resolve_bundle_candidate(bundle_dir: Path, candidate: Path) -> Path:
    """解析 bundle 路径并拒绝逃逸 bundle-dir 的符号链接/路径。"""
    base = bundle_dir.resolve()
    resolved = candidate.resolve()
    if base not in resolved.parents:
        raise ValueError(f"bundle 路径逃逸 bundle-dir: {candidate}")
    return resolved


def _iter_report_bundles(bundle_dir: str | Path) -> list[Path]:
    """确定性列出 bundle-dir 内的 report_bundle.json（排序，拒绝路径逃逸）。"""
    base = Path(bundle_dir)
    if not base.is_dir():
        raise ValueError(f"bundle-dir 不存在: {base}")
    candidates = [base / "report_bundle.json", *sorted(base.glob("*/report_bundle.json"))]
    bundles: list[Path] = []
    for candidate in candidates:
        if not candidate.exists():
            continue
        bundles.append(_resolve_bundle_candidate(base, candidate))
    return sorted(bundles, key=str)


def _load_bundle_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"bundle 必须是 JSON 对象: {path}")
    return payload


def _bundle_job_name(bundle: dict, fallback: str) -> str:
    run_manifest = bundle.get("run_manifest") or {}
    job_id = run_manifest.get("job_id")
    if isinstance(job_id, str) and job_id:
        return job_id
    job = bundle.get("job") or {}
    job_id = job.get("job_id")
    if isinstance(job_id, str) and job_id:
        return job_id
    return fallback


def _safe_review_filename(job: str) -> str:
    """把 bundle/评分文件中的 job 名转成安全文件名（防目录逃逸）。

    job 名来自不可信的 bundle/评分内容；直接拼进输出路径可写出 output_root
    之外的文件（../../README 之类的目录穿越），故先做白名单替换并再次校验。
    """
    sanitized = re.sub(r"[^A-Za-z0-9_.-]", "_", job)
    if sanitized in {"", ".", ".."} or Path(sanitized).name != sanitized:
        raise ValueError(f"job 名无法安全用作文件名: {job!r}")
    return sanitized


def _bundle_claims(bundle: dict) -> list[dict]:
    """把 v2（accepted/qualified_claims）或 v1（claims）bundle 归一化为抽检行。"""
    source_by_document: dict[str, str] = {}
    source_by_id: dict[str, str] = {}
    for source in bundle.get("sources") or []:
        if not isinstance(source, dict):
            continue
        uri = source.get("uri") or source.get("canonical_uri")
        if not isinstance(uri, str):
            continue
        metadata = source.get("metadata") or {}
        document_id = metadata.get("document_version_id")
        if isinstance(document_id, str):
            source_by_document.setdefault(document_id, uri)
        source_id = source.get("source_id")
        if isinstance(source_id, str):
            source_by_id.setdefault(source_id, uri)
    if "accepted_claims" in bundle or "qualified_claims" in bundle:
        claims: list[dict] = []
        for claim in [
            *(bundle.get("accepted_claims") or []),
            *(bundle.get("qualified_claims") or []),
        ]:
            if not isinstance(claim, dict):
                continue
            spans = claim.get("evidence_spans") or []
            source_url = quote = None
            if spans and isinstance(spans[0], dict):
                quote = spans[0].get("quote")
                source_url = source_by_document.get(spans[0].get("document_version_id"))
            claims.append(
                {
                    "claim_id": claim.get("claim_id", ""),
                    "claim": claim.get("claim", ""),
                    "critical": bool(claim.get("critical", False)),
                    "source_url": source_url,
                    "quote": quote,
                }
            )
        return claims
    fragments: dict[str, dict] = {}
    for fragment in bundle.get("evidence_fragments") or []:
        if isinstance(fragment, dict):
            fragments[fragment.get("evidence_id")] = fragment
    claims = []
    for claim in bundle.get("claims") or []:
        if not isinstance(claim, dict):
            continue
        source_url = quote = None
        for evidence_id in claim.get("evidence_ids") or []:
            fragment = fragments.get(evidence_id)
            if not fragment:
                continue
            quote = fragment.get("excerpt")
            source_url = source_by_id.get(fragment.get("source_id"))
            if quote or source_url:
                break
        claims.append(
            {
                "claim_id": claim.get("claim_id", ""),
                "claim": claim.get("text", ""),
                "critical": str(claim.get("criticality", "")).lower() in {"high", "critical"},
                "source_url": source_url,
                "quote": quote,
            }
        )
    return claims


def _verified_rate_from_bundle(bundle: dict) -> tuple[float | None, dict | None, str]:
    """按 run_drb_gate 语义聚合 citation_verification.summary。"""
    audit_summary = bundle.get("audit_summary") or {}
    verification = audit_summary.get("citation_verification") or {}
    summary = verification.get("summary")
    if not isinstance(summary, dict):
        return None, None, "bundle audit_summary 缺少 citation_verification.summary"
    passed = int(summary.get("verified", 0))
    failed = int(summary.get("unsupported", 0)) + int(summary.get("fetch_failed", 0))
    unresolved = int(summary.get("unverifiable", 0))
    counts = {
        "total": int(summary.get("total", 0)),
        "passed": passed,
        "failed": failed,
        "unresolved": unresolved,
    }
    denominator = passed + failed + unresolved
    if denominator == 0:
        return None, counts, "citation_verification 分母为空（no_citation_evidence）"
    return round(passed / denominator, 6), counts, None


def _load_human_review_rubric() -> dict:
    path = PROJECT_ROOT / _HUMAN_REVIEW_RUBRIC_REL
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict) or not payload.get("dimensions"):
        raise ValueError(f"rubric 无效: {path}")
    return payload


def _md_cell(value) -> str:
    if value is None:
        return ""
    text = str(value).replace("|", "\\|").replace("\n", " ").strip()
    if len(text) > 200:
        text = text[:200] + "…"
    return text


def _anchor_text(anchor) -> str:
    if isinstance(anchor, dict):
        return _md_cell(anchor.get("example", ""))
    return _md_cell(anchor)


def _repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _render_human_review_md(
    *,
    job: str,
    bundle: dict,
    rubric: dict,
    sampled: list[dict],
    seed: int,
    sample_size: int,
    bundle_path: Path,
) -> str:
    dimensions = rubric["dimensions"]
    lines = [
        f"# 人工抽检评审 — {job}",
        "",
        "> 量规：`evals/rubrics/citation_authenticity.yaml`（DRB-II 风格，1–5 级锚点，2/4 为相邻锚点之间）",
        f"> 采样：seed={seed}，sample_size={sample_size}，bundle={_repo_relative(bundle_path)}",
        "",
        "## 评分区（按量规 4 个维度打分，整数 1–5）",
        "",
        "| 维度 | 说明 | 评分 |",
        "|---|---|---|",
    ]
    for dimension in dimensions:
        lines.append(
            f"| `{dimension['name']}`（{dimension.get('label', '')}） | "
            f"{dimension.get('description', '')} | ____ |"
        )
    lines += [
        "",
        "## 抽检声明",
        "",
        "| # | claim_id | critical | 声明 | 来源 URL | 原文摘录 |",
        "|---|---|---|---|---|---|",
    ]
    for index, claim in enumerate(sampled, start=1):
        lines.append(
            f"| {index} | {_md_cell(claim['claim_id'])} | "
            f"{'是' if claim['critical'] else '否'} | {_md_cell(claim['claim'])} | "
            f"{_md_cell(claim['source_url']) or '（无证据引用）'} | "
            f"{_md_cell(claim['quote']) or '（无原文摘录）'} |"
        )
    audit_summary = bundle.get("audit_summary") or {}
    lines += ["", "## Bundle 审计摘要", ""]
    lines.append(f"- status: `{audit_summary.get('status', '?')}`")
    lines.append(f"- gate_status: `{audit_summary.get('gate_status', '?')}`")
    verification = (audit_summary.get("citation_verification") or {}).get("summary")
    if isinstance(verification, dict):
        lines.append(
            f"- citation_verification.summary: {json.dumps(verification, ensure_ascii=False, sort_keys=True)}"
        )
    else:
        lines.append("- citation_verification.summary: （缺失）")
    lines += [
        "- 语义映射：passed=verified；failed=unsupported+fetch_failed；unresolved=unverifiable",
        "",
        "## 量规锚点（评审参考）",
        "",
    ]
    for dimension in dimensions:
        lines.append(f"### {dimension['name']}（{dimension.get('label', '')}）")
        anchors = dimension.get("anchors") or {}
        for level in (1, 3, 5):
            anchor = anchors.get(level, anchors.get(str(level), ""))
            lines.append(f"- {level} 分：{_anchor_text(anchor)}")
        lines.append("")
    return "\n".join(lines)


def _sample_human_review(
    *,
    bundle_dir: str | Path,
    sample_size: int,
    seed: int,
    output_dir: str | Path | None = None,
) -> dict:
    """按种子确定性采样 bundle 声明并生成 <job>.md 评审单。"""
    bundles = _iter_report_bundles(bundle_dir)
    if not bundles:
        raise ValueError(f"bundle-dir 中没有 report_bundle.json: {bundle_dir}")
    rubric = _load_human_review_rubric()
    output_root = Path(output_dir) if output_dir else PROJECT_ROOT / _HUMAN_REVIEW_OUTPUT_DIR
    output_root.mkdir(parents=True, exist_ok=True)
    reports: dict[str, str] = {}
    for bundle_path in bundles:
        bundle = _load_bundle_json(bundle_path)
        job = _bundle_job_name(bundle, bundle_path.parent.name)
        claims = _bundle_claims(bundle)
        sampled = sorted(
            random.Random(seed).sample(claims, min(sample_size, len(claims))),
            key=lambda claim: str(claim["claim_id"]),
        )
        markdown = _render_human_review_md(
            job=job,
            bundle=bundle,
            rubric=rubric,
            sampled=sampled,
            seed=seed,
            sample_size=sample_size,
            bundle_path=bundle_path,
        )
        report_path = output_root / f"{_safe_review_filename(job)}.md"
        report_path.write_text(markdown, encoding="utf-8")
        reports[_safe_review_filename(job)] = str(report_path)
    return {
        "command": "human-sample",
        "status": "completed",
        "output_root": str(output_root.resolve()),
        "seed": seed,
        "sample_size": sample_size,
        "sampled_jobs": sorted(reports),
        "reports": reports,
    }


def _import_human_review_scores(
    *,
    bundle_dir: str | Path,
    score_file: str | Path,
    output_dir: str | Path | None = None,
) -> dict:
    """导入评分文件（YAML），聚合生成 <job>.scorecard.json。"""
    score_path = Path(score_file)
    if not score_path.is_file():
        raise ValueError(f"评分文件不存在: {score_path}")
    payload = yaml.safe_load(score_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("评分文件必须是 YAML 映射")
    rubric = _load_human_review_rubric()
    rubric_dimensions = [dimension["name"] for dimension in rubric["dimensions"]]
    job = payload.get("job")
    job = job.strip() if isinstance(job, str) and job.strip() else score_path.stem
    dimensions = payload.get("dimensions")
    if not isinstance(dimensions, dict):
        raise ValueError("评分文件缺少 dimensions 映射")
    unknown = [name for name in dimensions if name not in rubric_dimensions]
    if unknown:
        raise ValueError(f"评分文件包含未知维度: {', '.join(sorted(unknown))}")
    missing = [name for name in rubric_dimensions if name not in dimensions]
    if missing:
        raise ValueError(f"评分文件缺少维度: {', '.join(sorted(missing))}")
    scores: dict[str, int] = {}
    for name, value in dimensions.items():
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise ValueError(f"维度 {name} 的评分必须是 1–5 的整数，得到: {value!r}")
        scores[name] = value

    bundle_path = None
    for candidate in _iter_report_bundles(bundle_dir):
        candidate_bundle = _load_bundle_json(candidate)
        if _bundle_job_name(candidate_bundle, candidate.parent.name) == job:
            bundle_path = candidate
            break
    if bundle_path is None:
        raise ValueError(f"bundle-dir 中未找到 job {job!r} 对应的 report_bundle.json")
    bundle = _load_bundle_json(bundle_path)
    verified_rate, _counts, note = _verified_rate_from_bundle(bundle)

    output_root = Path(output_dir) if output_dir else PROJECT_ROOT / _HUMAN_REVIEW_OUTPUT_DIR
    output_root.mkdir(parents=True, exist_ok=True)
    scorecard_path = output_root / f"{_safe_review_filename(job)}.scorecard.json"
    existing: dict = {}
    if scorecard_path.exists():
        existing = json.loads(scorecard_path.read_text(encoding="utf-8"))
    reviews = dict(existing.get("reviews") or {})
    reviews[score_path.name] = scores
    dimension_stats: dict[str, dict] = {}
    for name in rubric_dimensions:
        values = [review[name] for review in reviews.values()]
        dimension_stats[name] = {
            "mean": round(sum(values) / len(values), 4),
            "min": min(values),
            "max": max(values),
            "count": len(values),
        }
    overall_values = [score for review in reviews.values() for score in review.values()]
    scorecard = {
        "job": job,
        "rubric_name": rubric["rubric_name"],
        "score_files": sorted(reviews),
        "reviews": {name: reviews[name] for name in sorted(reviews)},
        "dimensions": dimension_stats,
        "overall": {
            "mean": round(sum(overall_values) / len(overall_values), 4),
            "min": min(overall_values),
            "max": max(overall_values),
            "count": len(overall_values),
        },
        "verified_rate": verified_rate,
        "verified_rate_note": note,
        "semantic_mapping": rubric.get("semantic_mapping") or {},
    }
    scorecard_path.write_text(
        json.dumps(scorecard, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return {
        "command": "human-sample-import",
        "status": "completed",
        "job": job,
        "score_file": str(score_path),
        "scorecard_path": str(scorecard_path),
        "dimensions": dimension_stats,
        "verified_rate": verified_rate,
        "verified_rate_note": note,
    }


def run_command(argv: list[str] | None = None) -> int:
    """执行一条 CLI 命令。"""
    settings = get_settings()
    argv = list(argv or [])
    if argv and argv[0] == "legacy-run":
        if not getattr(settings, "legacy_cli_enabled", True):
            console.print("[red]当前环境未启用 legacy-run[/red]")
            return 2
        legacy_args = _build_legacy_parser().parse_args(argv[1:])
        try:
            topic = _validate_topic(legacy_args.topic)
        except ValueError as exc:
            console.print(f"[red]输入校验失败: {exc}[/red]")
            return 2
        run_cli(topic, max_loops=legacy_args.max_loops, profile=legacy_args.profile)
        return 0

    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        console.print("\n[yellow]示例:[/yellow]")
        console.print('  uv run python main.py submit --topic "可信深度研究 app"')
        console.print("  uv run python main.py watch --job-id <job_id>")
        console.print("  uv run python main.py eval run --suite company12")
        return 0

    if args.command == "eval":
        if args.eval_command == "run":
            result = run_eval_suite(
                suite_name=args.suite,
                variant=args.variant,
                output_root=args.output_root,
                capture_runtime_metrics=args.capture_runtime_metrics,
            )
            if args.json:
                _print_json(result)
            else:
                console.print(f"✅ eval suite 完成: [cyan]{args.suite}[/cyan]")
                console.print(f"status: [bold]{result['status']}[/bold]")
                console.print(f"summary: [cyan]{result['summary_path']}[/cyan]")
            return 0
        if args.eval_command == "human-sample":
            try:
                if args.import_file:
                    result = _import_human_review_scores(
                        bundle_dir=args.bundle_dir,
                        score_file=args.import_file,
                    )
                else:
                    result = _sample_human_review(
                        bundle_dir=args.bundle_dir,
                        sample_size=args.sample_size,
                        seed=args.seed,
                    )
            except ValueError as exc:
                console.print(f"[red]人工抽检失败: {exc}[/red]")
                return 2
            console.print(f"✅ 人工抽检完成: [cyan]{result['status']}[/cyan]")
            if "reports" in result:
                for job in result["sampled_jobs"]:
                    console.print(f"- [cyan]{result['reports'][job]}[/cyan]")
            else:
                console.print(f"scorecard: [cyan]{result['scorecard_path']}[/cyan]")
            return 0
        parser.error("eval 目前只支持 `run` 和 `human-sample` 子命令")
        return 2

    if args.command == "benchmark":
        if args.benchmark_command != "run":
            parser.error("benchmark 目前只支持 `run` 子命令")
            return 2
        benchmark_output_root = args.output_root or str(
            Path("evals") / "external" / "reports" / f"{args.benchmark}_{args.subset}"
        )
        result = run_external_benchmark(
            benchmark_name=args.benchmark,
            split=args.split,
            subset=args.subset,
            bucket=args.bucket,
            output_root=benchmark_output_root,
            config_path=args.config,
        )
        if args.json:
            _print_json(result)
        else:
            console.print(f"✅ external benchmark 完成: [cyan]{args.benchmark}[/cyan]")
            console.print(f"status: [bold]{result['status']}[/bold]")
            console.print(f"output_root: [cyan]{result['output_root']}[/cyan]")
        return 0

    service = _build_job_service()
    service.recover_stale_jobs()

    if args.command == "submit":
        try:
            topic = _validate_topic(args.topic)
        except ValueError as exc:
            console.print(f"[red]输入校验失败: {exc}[/red]")
            return 2
        connector_budget = _connector_budget_from_args(args)
        offline = bool(getattr(service, "_scheduler_offline", lambda: False)())
        if args.legacy or offline:
            # v1 orchestrator: kept for legacy compatibility, and it is the
            # only runtime that can produce a deterministic report without
            # LLM credentials (scheduler-v2 offline yields an honest empty
            # bundle by design).
            job = service.submit(
                topic=topic,
                max_loops=args.max_loops,
                research_profile=args.profile,
                start_worker=not args.no_worker,
                source_profile=args.source_profile,
                allow_domains=args.allow_domain,
                deny_domains=args.deny_domain,
                connector_budget=connector_budget,
            )
        else:
            job = _submit_cli_v2(
                service,
                topic=topic,
                max_loops=args.max_loops,
                source_profile=args.source_profile,
                allow_domains=args.allow_domain,
                deny_domains=args.deny_domain,
                connector_budget=connector_budget,
                start_worker=not args.no_worker,
                settings=settings,
            )
        payload = _jsonable_model(job)
        if args.json:
            _print_json(payload)
        else:
            console.print(f"✅ 已提交 job: [cyan]{job.job_id}[/cyan]")
            console.print(
                f"当前状态: [bold]{job.status}[/bold] -> next: [bold]{job.current_stage}[/bold]"
            )
            console.print(f"source_profile: [bold]{job.source_profile}[/bold]")
            console.print(f"runtime_path: [bold]{job.runtime_path}[/bold]")
        return 0

    if args.command == "status":
        job = service.get(args.job_id)
        if job is None:
            console.print(f"[red]未找到 job: {args.job_id}[/red]")
            return 1
        payload = _jsonable_model(job)
        if args.json:
            _print_json(payload)
        else:
            console.print(f"job_id: [cyan]{job.job_id}[/cyan]")
            console.print(f"status: [bold]{job.status}[/bold]")
            console.print(f"current_stage: [bold]{job.current_stage}[/bold]")
            console.print(f"audit_gate_status: [bold]{job.audit_gate_status}[/bold]")
            if job.blocked_critical_claim_count:
                console.print(
                    f"blocked_critical_claim_count: [yellow]{job.blocked_critical_claim_count}[/yellow]"
                )
            if job.error:
                console.print(f"error: [red]{job.error}[/red]")
        return 0

    if args.command == "cancel":
        job = service.cancel(args.job_id)
        payload = _jsonable_model(job)
        if args.json:
            _print_json(payload)
        else:
            console.print(f"🛑 已请求取消 job: [cyan]{job.job_id}[/cyan]")
        return 0

    if args.command == "retry":
        job = service.retry(args.job_id, start_worker=not args.no_worker)
        payload = _jsonable_model(job)
        if args.json:
            _print_json(payload)
        else:
            console.print(
                f"🔁 已创建 retry job: [cyan]{job.job_id}[/cyan] (retry_of={job.retry_of})"
            )
        return 0

    if args.command == "resume":
        job = service.resume(args.job_id, start_worker=not args.no_worker)
        payload = _jsonable_model(job)
        if args.json:
            _print_json(payload)
        else:
            console.print(f"▶️ 已恢复 job: [cyan]{job.job_id}[/cyan]")
            console.print(f"当前阶段: [bold]{job.current_stage}[/bold]")
        return 0

    if args.command == "refine":
        job = service.refine(args.job_id, args.instruction, start_worker=not args.no_worker)
        payload = _jsonable_model(job)
        if args.json:
            _print_json(payload)
        else:
            console.print(f"🧭 已记录 refinement 并恢复 job: [cyan]{job.job_id}[/cyan]")
            console.print(f"当前阶段: [bold]{job.current_stage}[/bold]")
        return 0

    if args.command == "bundle":
        job = service.get(args.job_id)
        if job is None:
            console.print(f"[red]未找到 job: {args.job_id}[/red]")
            return 1
        try:
            payload = _artifact_payload(job, args.artifact_name)
        except FileNotFoundError:
            console.print(f"[red]缺少 artifact: {args.artifact_name}[/red]")
            return 1
        if args.json and isinstance(payload, (dict, list)):
            _print_json(payload)
        elif isinstance(payload, (dict, list)):
            console.print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            console.print(payload)
        return 0

    if args.command == "batch":
        if args.batch_command != "run":
            parser.error("batch 目前只支持 `run` 子命令")
            return 2
        requests = load_batch_requests(args.file)
        jobs = [
            service.submit(
                topic=item.topic,
                max_loops=item.max_loops,
                research_profile=item.research_profile,
                start_worker=item.start_worker,
                source_profile=item.source_profile,
                allow_domains=item.allow_domains,
                deny_domains=item.deny_domains,
                connector_budget=item.connector_budget,
            )
            for item in requests
        ]
        payload = {
            "accepted_count": len(jobs),
            "jobs": [_jsonable_model(job) for job in jobs],
        }
        if args.json:
            _print_json(payload)
        else:
            console.print(f"✅ 已接收 batch jobs: [cyan]{len(jobs)}[/cyan]")
            for job in jobs:
                console.print(f"- {job.job_id} :: {job.topic}")
        return 0

    if args.command == "watch":
        last_sequence = 0
        while True:
            service.recover_stale_jobs()
            events = service.list_events(args.job_id, after_sequence=last_sequence)
            for event in events:
                last_sequence = event.sequence
                if args.json:
                    console.print(json.dumps(event.model_dump(mode="json"), ensure_ascii=False))
                else:
                    console.print(
                        f"[{event.sequence:04d}] {event.stage} {event.event_type} - {event.message}"
                    )
            job = service.get(args.job_id)
            if job is None:
                console.print(f"[red]未找到 job: {args.job_id}[/red]")
                return 1
            if job.status in {"completed", "failed", "cancelled"}:
                if not args.json:
                    console.print(f"终态: [bold]{job.status}[/bold]")
                    if getattr(job, "audit_gate_status", "unchecked") != "unchecked":
                        console.print(f"audit_gate_status: [bold]{job.audit_gate_status}[/bold]")
                return 0
            time.sleep(args.poll_interval)

    parser.error(f"未知命令: {args.command}")
    return 2


def main() -> None:
    """主入口函数。"""
    raise SystemExit(run_command(sys.argv[1:]))


if __name__ == "__main__":
    main()
