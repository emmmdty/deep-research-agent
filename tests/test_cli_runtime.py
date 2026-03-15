"""CLI 运行时配置回归测试。"""

from __future__ import annotations

from types import SimpleNamespace


def test_main_parser_uses_settings_default_max_loops(monkeypatch):
    """主 CLI 默认迭代次数应跟随 Settings。"""
    import main

    settings = SimpleNamespace(max_research_loops=7, workspace_dir="workspace")
    monkeypatch.setattr(main, "get_settings", lambda: settings)

    parser = main.build_parser()
    args = parser.parse_args([])

    assert args.max_loops == 7


def test_run_cli_uses_settings_workspace_dir(tmp_path, monkeypatch):
    """CLI 输出目录应跟随 Settings.workspace_dir。"""
    import main

    output_root = tmp_path / "custom-workspace"
    settings = SimpleNamespace(
        max_research_loops=5,
        workspace_dir=str(output_root),
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)

    output_path = main.run_cli(
        topic="边界收敛测试",
        run_research_fn=lambda topic, max_loops: {"final_report": "# 报告\n\n内容"},
    )

    assert output_path == output_root / "report_边界收敛测试.md"
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").startswith("# 报告")
