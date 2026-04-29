"""Deep Research Agent product CLI."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from deep_research_agent.config.settings import get_settings
from deep_research_agent.common import CANONICAL_SOURCE_PROFILES
from deep_research_agent.gateway.artifacts import ARTIFACT_NAME_CHOICES, artifact_path_for_job, load_json_artifact
from deep_research_agent.gateway.batch import load_batch_requests
from dotenv import load_dotenv
from loguru import logger
from rich.console import Console

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


def _build_job_service():
    """构建 job service。"""
    from deep_research_agent.research_jobs import ResearchJobService

    return ResearchJobService()


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
    submit_parser.add_argument("--allow-domain", action="append", default=[], help="额外允许的域名，可重复")
    submit_parser.add_argument("--deny-domain", action="append", default=[], help="额外禁止的域名，可重复")
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
    retry_parser.add_argument("--no-worker", action="store_true", help="只创建 retry job，不启动后台 worker")
    retry_parser.add_argument("--json", action="store_true", help="输出 JSON")

    resume_parser = subparsers.add_parser("resume", help="从最新 checkpoint 恢复同一个 job")
    resume_parser.add_argument("--job-id", required=True, type=str, help="job ID")
    resume_parser.add_argument("--no-worker", action="store_true", help="只恢复状态，不启动后台 worker")
    resume_parser.add_argument("--json", action="store_true", help="输出 JSON")

    refine_parser = subparsers.add_parser("refine", help="记录 refinement 指令并从安全边界恢复")
    refine_parser.add_argument("--job-id", required=True, type=str, help="job ID")
    refine_parser.add_argument("--instruction", required=True, type=str, help="refinement 指令")
    refine_parser.add_argument("--no-worker", action="store_true", help="只更新状态，不启动后台 worker")
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
    bundle_parser.add_argument("--json", action="store_true", help="将 JSON artifact 以结构化 JSON 输出")

    batch_parser = subparsers.add_parser("batch", help="批量 research job 操作")
    batch_subparsers = batch_parser.add_subparsers(dest="batch_command")
    batch_run_parser = batch_subparsers.add_parser("run", help="从 JSON/JSONL 文件批量创建 job")
    batch_run_parser.add_argument("--file", required=True, type=str, help="JSON 或 JSONL batch 文件路径")
    batch_run_parser.add_argument("--json", action="store_true", help="输出结构化 JSON")

    return parser


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


def run_command(argv: list[str] | None = None) -> int:
    """执行一条 CLI 命令。"""
    parser = build_parser()
    args = parser.parse_args(list(argv or []))
    if not args.command:
        parser.print_help()
        console.print("\n[yellow]示例:[/yellow]")
        console.print('  uv run python main.py submit --topic "可信深度研究 app"')
        console.print("  uv run python main.py watch --job-id <job_id>")
        return 0

    service = _build_job_service()
    service.recover_stale_jobs()

    if args.command == "submit":
        job = service.submit(
            topic=args.topic,
            max_loops=args.max_loops,
            research_profile=args.profile,
            start_worker=not args.no_worker,
            source_profile=args.source_profile,
            allow_domains=args.allow_domain,
            deny_domains=args.deny_domain,
            connector_budget=_connector_budget_from_args(args),
        )
        payload = _jsonable_model(job)
        if args.json:
            _print_json(payload)
        else:
            console.print(f"✅ 已提交 job: [cyan]{job.job_id}[/cyan]")
            console.print(f"当前状态: [bold]{job.status}[/bold] -> next: [bold]{job.current_stage}[/bold]")
            console.print(f"source_profile: [bold]{job.source_profile}[/bold]")
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
                console.print(f"blocked_critical_claim_count: [yellow]{job.blocked_critical_claim_count}[/yellow]")
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
            console.print(f"🔁 已创建 retry job: [cyan]{job.job_id}[/cyan] (retry_of={job.retry_of})")
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
