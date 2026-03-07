"""Deep Research Agent 主入口。

使用方式：
    # 命令行运行
    uv run python main.py --topic "2024年大语言模型Agent架构的最新进展"

    # 启动 API 服务
    uv run python main.py --serve
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

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


def run_cli(topic: str, max_loops: int = 3) -> None:
    """命令行模式：运行深度研究并输出报告。"""
    from workflows.graph import run_research

    console.print(
        Panel(
            f"[bold cyan]研究主题:[/bold cyan] {topic}\n"
            f"[bold cyan]最大迭代:[/bold cyan] {max_loops} 次",
            title="🔬 Deep Research Agent",
            border_style="blue",
        )
    )
    console.print()

    # 执行研究
    result = run_research(topic, max_loops=max_loops)

    # 输出报告
    report = result.get("final_report", "报告生成失败")
    console.print()
    console.print(Panel("[bold green]✅ 研究完成[/bold green]", border_style="green"))
    console.print()
    console.print(Markdown(report))

    # 保存报告到文件
    output_dir = Path("workspace")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"report_{topic[:20].replace(' ', '_')}.md"
    output_file.write_text(report, encoding="utf-8")
    console.print(f"\n📄 报告已保存到: [cyan]{output_file}[/cyan]")


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """启动 FastAPI 服务器。"""
    import uvicorn

    console.print(
        Panel(
            f"[bold cyan]地址:[/bold cyan] http://{host}:{port}\n"
            f"[bold cyan]文档:[/bold cyan] http://{host}:{port}/docs",
            title="🌐 Deep Research Agent API",
            border_style="blue",
        )
    )

    # 延迟导入以避免循环依赖
    from api import create_app

    app = create_app()
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    """主入口函数。"""
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
        default=3,
        help="最大迭代循环次数（默认 3）",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="启动 API 服务器模式",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="API 服务绑定地址（默认 0.0.0.0）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API 服务端口（默认 8000）",
    )

    args = parser.parse_args()

    if args.serve:
        run_server(host=args.host, port=args.port)
    elif args.topic:
        run_cli(args.topic, max_loops=args.max_loops)
    else:
        parser.print_help()
        console.print("\n[yellow]示例:[/yellow]")
        console.print('  uv run python main.py --topic "2024年大语言模型Agent架构的最新进展"')
        console.print("  uv run python main.py --serve")


if __name__ == "__main__":
    main()
