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
import sys
import time
from pathlib import Path

from configs.settings import get_settings
from dotenv import load_dotenv
from loguru import logger
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

# 加载 .env 文件（同时检查上级目录的 .env）
env_path = Path(__file__).parent / ".env"
parent_env = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
elif parent_env.exists():
    load_dotenv(parent_env)

logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:^8}</level> | <cyan>{message}</cyan>",
    level="INFO",
)

console = Console()


def _load_run_research():
    """懒加载 legacy 研究工作流执行函数。"""
    from workflows.graph import run_research

    return run_research


def _build_job_service():
    """构建 phase2 job service。"""
    from services.research_jobs.service import ResearchJobService

    return ResearchJobService()


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""
    settings = get_settings()
    default_max_loops = getattr(settings, "max_research_loops", 3)
    default_profile = getattr(settings, "research_profile", "default")
    default_source_profile = getattr(settings, "source_policy_mode", "open-web")
    parser = argparse.ArgumentParser(
        description="Deep Research Agent — 多智能体深度研究系统",
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
    retry_parser.add_argument("--json", action="store_true", help="输出 JSON")

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
    output_file = output_dir / f"report_{topic[:20].replace(' ', '_')}.md"
    output_file.write_text(report, encoding="utf-8")
    console.print(f"\n📄 报告已保存到: [cyan]{output_file}[/cyan]")

    if resolved_emit_bundle:
        from artifacts.bundle import emit_report_artifacts

        artifact_paths = emit_report_artifacts(
            result,
            topic=topic,
            max_loops=resolved_max_loops,
            research_profile=resolved_profile,
            workspace_dir=output_dir,
            bundle_output_dirname=getattr(settings, "bundle_output_dirname", "bundles"),
            source_profile=getattr(settings, "source_policy_mode", "legacy-default"),
        )
        if artifact_paths is not None:
            console.print(f"🧾 Bundle 已保存到: [cyan]{artifact_paths['bundle_path']}[/cyan]")
            console.print(f"🪵 Trace 已保存到: [cyan]{artifact_paths['trace_path']}[/cyan]")
    return output_file


def _print_json(payload) -> None:
    console.print(json.dumps(payload, ensure_ascii=False, indent=2))


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


def run_command(argv: list[str] | None = None) -> int:
    """执行一条 CLI 命令。"""
    settings = get_settings()
    argv = list(argv or [])
    if argv and argv[0] == "legacy-run":
        if not getattr(settings, "legacy_cli_enabled", True):
            console.print("[red]当前环境未启用 legacy-run[/red]")
            return 2
        legacy_args = _build_legacy_parser().parse_args(argv[1:])
        run_cli(legacy_args.topic, max_loops=legacy_args.max_loops, profile=legacy_args.profile)
        return 0

    parser = build_parser()
    args = parser.parse_args(argv)
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
            start_worker=True,
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
        job = service.retry(args.job_id, start_worker=True)
        payload = _jsonable_model(job)
        if args.json:
            _print_json(payload)
        else:
            console.print(f"🔁 已创建 retry job: [cyan]{job.job_id}[/cyan] (retry_of={job.retry_of})")
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
            if job.status in {"completed", "failed", "cancelled", "needs_review"}:
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
