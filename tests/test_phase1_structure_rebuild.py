"""Phase 1 structure rebuild acceptance tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent


def test_canonical_src_package_is_importable():
    """The new src-layout package should be the canonical import path."""
    package_root = PROJECT_ROOT / "src" / "deep_research_agent"

    assert package_root.exists()

    result = subprocess.run(
        [sys.executable, "-c", "import deep_research_agent; print(deep_research_agent.__file__)"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "src/deep_research_agent" in result.stdout.strip()


def test_legacy_graph_code_is_archived_under_legacy():
    """Legacy graph runtime should no longer live at the repo top level."""
    assert (PROJECT_ROOT / "legacy" / "agents").exists()
    assert (PROJECT_ROOT / "legacy" / "workflows").exists()
    assert not (PROJECT_ROOT / "agents").exists()
    assert not (PROJECT_ROOT / "workflows").exists()


def test_main_is_a_thin_wrapper_to_package_cli():
    """Top-level main.py should delegate to the package CLI entrypoint."""
    content = (PROJECT_ROOT / "main.py").read_text(encoding="utf-8")

    assert "deep_research_agent.gateway.cli" in content
