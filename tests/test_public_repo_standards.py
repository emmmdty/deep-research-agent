"""公共 GitHub 仓库标准回归测试。"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent
REMOVED_SHOWCASE_MATERIALS = [
    f"docs/{name}.md"
    for name in ("showcase", "resume_bullets", "interview_qa")
]


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
    assert "BUNDLE_EMISSION_ENABLED=" in content
    assert "BUNDLE_OUTPUT_DIRNAME=" in content
    assert "JOB_RUNTIME_DIRNAME=" in content
    assert "JOB_HEARTBEAT_INTERVAL_SECONDS=" in content
    assert "JOB_STALE_TIMEOUT_SECONDS=" in content
    assert "LEGACY_CLI_ENABLED=" in content
    assert "RESEARCH_CONCURRENCY=" in content
    assert "ENABLED_SOURCES=" in content
    assert "ENABLED_COMPARATORS=" in content
    assert "OPEN_DEEP_RESEARCH_COMMAND=" in content


def test_pyproject_has_public_metadata_and_supported_api_dependencies():
    """包元数据应适合公开仓库，并声明当前支持的 HTTP API 依赖。"""
    content = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "fastapi" in content
    assert "uvicorn" in content
    assert "license" in content
    assert "keywords" in content
    assert "classifiers" in content
    assert "[project.urls]" in content
    assert "[project.scripts]" in content


def test_gitignore_covers_local_risks_and_tracks_lockfile():
    """忽略规则应覆盖本地风险资产，但保留 lockfile 进入版本控制。"""
    content = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    required_patterns = [
        ".env",
        ".env.*",
        "!.env.example",
        ".codex",
        ".codex/",
        ".venv/",
        "venv_gptr/",
        ".ruff_cache/",
        ".pytest_cache/",
        ".mypy_cache/",
        ".pyright/",
        ".coverage.*",
        "htmlcov/",
        ".ipynb_checkpoints/",
        "workspace/",
        "my-docs/",
        "docs/reports/",
        "*.db",
        "*.sqlite",
        "*.sqlite3",
        "*:Zone.Identifier",
        "scripts/test_gptr*.py",
    ]

    for pattern in required_patterns:
        assert pattern in content

    assert "uv.lock" not in content


def test_public_readmes_do_not_link_removed_showcase_materials():
    """公开 README 不应链接不再发布的面试/简历材料。"""
    readme_paths = ["README.md", "README.zh-CN.md"]

    for readme_path in readme_paths:
        content = (PROJECT_ROOT / readme_path).read_text(encoding="utf-8")
        for removed_path in REMOVED_SHOWCASE_MATERIALS:
            assert removed_path not in content


def test_non_public_files_are_not_tracked_when_inside_git_repo():
    """公开仓库不应跟踪本地资料、运行产物和已下线展示文档。"""
    repo_check = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if repo_check.returncode != 0 or repo_check.stdout.strip() != "true":
        pytest.skip("当前环境不是 Git 仓库，跳过 tracked files 发布面检查")

    result = subprocess.run(
        ["git", "ls-files"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked_files = set(result.stdout.splitlines())

    forbidden_exact_paths = {
        ".codex",
        ".env",
        "docs/deep-research-agent-beginner-guide.md",
        "docs/审查意见.md",
        "docs/plans/2026-03-08-deep-research-comparators.md",
    } | set(REMOVED_SHOWCASE_MATERIALS)
    forbidden_prefixes = (
        ".env.",
        "workspace/",
        "my-docs/",
        "docs/reports/",
    )
    forbidden_suffixes = (".db", ".sqlite", ".sqlite3")

    leaked = [
        path
        for path in tracked_files
        if path != ".env.example"
        and (
            path in forbidden_exact_paths
            or path.startswith(forbidden_prefixes)
            or path.endswith(forbidden_suffixes)
        )
    ]

    assert not leaked, f"公开仓库跟踪了非发布文件: {sorted(leaked)}"


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


def test_tracked_files_do_not_contain_plaintext_secrets():
    """版本控制中的文件不应包含典型明文密钥。"""
    repo_check = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if repo_check.returncode != 0 or repo_check.stdout.strip() != "true":
        pytest.skip("当前环境不是 Git 仓库，跳过 tracked files 密钥扫描")

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
