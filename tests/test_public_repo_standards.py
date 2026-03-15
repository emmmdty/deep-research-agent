"""公共 GitHub 仓库标准回归测试。"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent


def test_main_help_exposes_only_supported_cli_surface():
    """主 CLI 不应再暴露冻结的服务参数。"""
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--serve" not in result.stdout
    assert "--host" not in result.stdout
    assert "--port" not in result.stdout


def test_compare_agents_help_is_offline_only():
    """compare_agents 应只保留离线文件比较入口。"""
    result = subprocess.run(
        [sys.executable, "scripts/compare_agents.py", "--help"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--topic" not in result.stdout
    assert "--file-a" in result.stdout
    assert "--file-b" in result.stdout


def test_env_example_matches_supported_public_configuration():
    """示例环境变量应只保留公开支持的配置面。"""
    content = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "HOST=" not in content
    assert "PORT=" not in content
    assert "RESEARCH_CONCURRENCY=" in content
    assert "ENABLED_SOURCES=" in content
    assert "ENABLED_COMPARATORS=" in content
    assert "WORKSPACE_DIR=" in content
    assert "LOG_LEVEL=" in content
    assert "OPEN_DEEP_RESEARCH_COMMAND=" in content


def test_default_yaml_does_not_advertise_removed_server_surface():
    """默认 YAML 不应再暗示已支持 HTTP 服务配置。"""
    content = (PROJECT_ROOT / "configs/default.yaml").read_text(encoding="utf-8")

    assert "server:" not in content
    assert "workspace_dir:" in content


def test_pyproject_has_public_metadata_and_no_dead_server_dependencies():
    """包元数据应适合公开仓库，且不再保留未使用的服务依赖。"""
    content = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "fastapi" not in content
    assert "uvicorn" not in content
    assert "license" in content
    assert "keywords" in content
    assert "classifiers" in content
    assert "[project.urls]" in content
    assert "[project.scripts]" in content


def test_gitignore_covers_local_risks_and_tracks_lockfile():
    """忽略规则应覆盖本地风险资产，但保留 lockfile 进入版本控制。"""
    content = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "venv_gptr/" in content
    assert "scripts/test_gptr*.py" in content
    assert "uv.lock" not in content


def test_required_community_and_github_files_exist():
    """公共仓库应包含社区健康文件与 GitHub 自动化配置。"""
    required_paths = [
        "LICENSE",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "SECURITY.md",
        ".github/workflows/ci.yml",
        ".github/pull_request_template.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        "README.zh-CN.md",
    ]

    missing = [path for path in required_paths if not (PROJECT_ROOT / path).exists()]
    assert not missing, f"缺少标准 GitHub 文件: {missing}"


def test_docs_mark_optional_modules_and_comparator_status_clearly():
    """公开文档应明确边缘目录状态，并提供 comparator 成熟度说明。"""
    readme_zh = (PROJECT_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs/architecture.md").read_text(encoding="utf-8")

    assert "Comparator 状态矩阵" in readme_zh
    assert "`ours`" in readme_zh
    assert "`gemini`" in readme_zh
    assert "memory/" in readme_zh
    assert "skills/" in readme_zh
    assert "mcp_servers/" in readme_zh

    assert "未纳入 `main.py -> workflows/graph.py` 主流程" in architecture
    assert "预留扩展目录" in architecture
    assert "默认允许 `skipped`" in architecture


def test_development_guide_contains_execution_and_governance_entrypoints():
    """开发指南应给出 90 天执行路线与最小项目纪律。"""
    development = (PROJECT_ROOT / "docs/development.md").read_text(encoding="utf-8")
    roadmap = (
        PROJECT_ROOT / "docs/plans/90-day-execution-roadmap.md"
    ).read_text(encoding="utf-8")

    assert "90 天执行路线" in development
    assert "文档同步清单" in development
    assert "Release Note 模板" in development
    assert "Benchmark 发布最小格式" in development

    assert "第 0-30 天" in roadmap
    assert "第 31-60 天" in roadmap
    assert "第 61-90 天" in roadmap
    assert "plan artifact" in roadmap
    assert "manifest" in roadmap
    assert "cited claim alignment" in roadmap
    assert "JSONL" in roadmap


def test_tracked_files_do_not_contain_plaintext_secrets():
    """版本控制中的文件不应包含典型明文密钥。"""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked_files = [
        PROJECT_ROOT / line
        for line in result.stdout.splitlines()
        if line and (PROJECT_ROOT / line).is_file()
    ]
    secret_pattern = re.compile(r"(sk-[A-Za-z0-9_-]{16,}|tvly-[A-Za-z0-9_-]{16,})")

    leaked = []
    for path in tracked_files:
        content = path.read_text(encoding="utf-8", errors="ignore")
        if secret_pattern.search(content):
            leaked.append(path.relative_to(PROJECT_ROOT).as_posix())

    assert not leaked, f"跟踪文件中发现疑似明文密钥: {leaked}"
