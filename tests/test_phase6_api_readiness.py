"""Phase 06 API readiness 边界回归测试。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
ADR_PATH = PROJECT_ROOT / "docs" / "adr" / "adr-0007-api-readiness-boundary.md"
SPEC_PATH = PROJECT_ROOT / "specs" / "api-readiness-contract.md"
NO_SERVER_PHRASE = "当前没有受支持的 HTTP/API server surface"
CONTRACT_ONLY_PHRASE = "目标契约，不是当前实现"


def test_api_readiness_docs_exist_and_are_contract_only():
    """API readiness 文档必须明确是 contract-only，不是当前能力。"""
    assert ADR_PATH.exists()
    assert SPEC_PATH.exists()

    adr = ADR_PATH.read_text(encoding="utf-8")
    spec = SPEC_PATH.read_text(encoding="utf-8")

    for content in (adr, spec):
        assert NO_SERVER_PHRASE in content
        assert CONTRACT_ONLY_PHRASE in content
        assert "FastAPI" not in content
        assert "uvicorn" not in content


def test_phase6_does_not_add_server_entrypoint_or_dependencies():
    """Phase 06 只做 readiness，不应新增 server entrypoint 或服务依赖。"""
    forbidden_paths = [
        PROJECT_ROOT / "api",
        PROJECT_ROOT / "server.py",
        PROJECT_ROOT / "app.py",
        PROJECT_ROOT / "services" / "api_server.py",
    ]
    for path in forbidden_paths:
        assert not path.exists()

    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "fastapi" not in pyproject.lower()
    assert "uvicorn" not in pyproject.lower()


def test_public_cli_surface_remains_job_only():
    """公开 CLI surface 仍只能是 job-oriented commands。"""
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "{submit,status,watch,cancel,retry}" in result.stdout
    assert "--serve" not in result.stdout
    assert "--host" not in result.stdout
    assert "--port" not in result.stdout
