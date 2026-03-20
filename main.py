"""Deep Research Agent 主入口。

使用方式：
    # 命令行运行
    uv run python main.py --topic "2024年大语言模型Agent架构的最新进展"
"""

from __future__ import annotations

import argparse
import inspect
import sys
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

# 配置日志
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:^8}</level> | <cyan>{message}</cyan>",
    level="INFO",
)

console = Console()


def _load_run_research():
    """懒加载研究工作流执行函数。"""
    from workflows.graph import run_research

    return run_research


def build_parser() -> argparse.ArgumentParser:
    """构建 CLI 参数解析器。"""
    settings = get_settings()
    default_max_loops = getattr(settings, "max_research_loops", 3)
    default_profile = getattr(settings, "research_profile", "default")
    parser = argparse.ArgumentParser(
        description="Deep Research Agent — 多智能体深度研究系统",
    )
    parser.add_argument(
        "--topic",
        type=str,
        help="研究主题",
    )
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
    run_research_fn=None,
) -> Path:
    """命令行模式：运行深度研究并输出报告。"""
    settings = get_settings()
    resolved_max_loops = (
        max_loops if max_loops is not None else getattr(settings, "max_research_loops", 3)
    )
    resolved_profile = profile or getattr(settings, "research_profile", "default")
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

    # 执行研究
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

    # 输出报告
    report = result.get("final_report", "报告生成失败")
    console.print()
    console.print(Panel("[bold green]✅ 研究完成[/bold green]", border_style="green"))
    console.print()
    console.print(Markdown(report))

    # 保存报告到文件
    output_dir = Path(getattr(settings, "workspace_dir", "workspace"))
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"report_{topic[:20].replace(' ', '_')}.md"
    output_file.write_text(report, encoding="utf-8")
    console.print(f"\n📄 报告已保存到: [cyan]{output_file}[/cyan]")
    return output_file


def main() -> None:
    """主入口函数。"""
    parser = build_parser()
    args = parser.parse_args()

    if args.topic:
        run_cli(args.topic, max_loops=args.max_loops, profile=args.profile)
    else:
        parser.print_help()
        console.print("\n[yellow]示例:[/yellow]")
        console.print('  uv run python main.py --topic "2024年大语言模型Agent架构的最新进展"')
        console.print("  uv run python scripts/run_benchmark.py --comparators ours,gptr,odr,alibaba")


if __name__ == "__main__":
    main()
