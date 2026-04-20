"""CLI 运行时配置与公开 surface 回归测试。"""

from __future__ import annotations

from types import SimpleNamespace


def test_main_parser_uses_settings_default_max_loops_for_submit(monkeypatch):
    """submit 子命令默认迭代次数应跟随 Settings。"""
    import main

    settings = SimpleNamespace(
        max_research_loops=7,
        workspace_dir="workspace",
        legacy_cli_enabled=True,
        source_policy_mode="open-web",
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)

    parser = main.build_parser()
    args = parser.parse_args(["submit", "--topic", "可信研究"])

    assert args.command == "submit"
    assert args.max_loops == 7
    assert args.source_profile == "open-web"


def test_run_cli_uses_settings_workspace_dir(tmp_path, monkeypatch):
    """legacy helper 输出目录应跟随 Settings.workspace_dir。"""
    import main

    output_root = tmp_path / "custom-workspace"
    settings = SimpleNamespace(
        max_research_loops=5,
        workspace_dir=str(output_root),
        legacy_cli_enabled=True,
        bundle_emission_enabled=False,
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)

    output_path = main.run_cli(
        topic="边界收敛测试",
        run_research_fn=lambda topic, max_loops: {"final_report": "# 报告\n\n内容"},
    )

    assert output_path == output_root / "report_边界收敛测试.md"
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").startswith("# 报告")


def test_submit_cli_dispatches_to_job_service(monkeypatch):
    """submit 子命令应调用 job service 创建任务。"""
    import main

    captured: dict[str, object] = {}

    class FakeService:
        def recover_stale_jobs(self):
            captured["recovered"] = True

        def submit(
            self,
            *,
            topic,
            max_loops,
            research_profile,
            start_worker=True,
            source_profile=None,
            allow_domains=None,
            deny_domains=None,
            connector_budget=None,
            file_inputs=None,
        ):
            captured["submit"] = {
                "topic": topic,
                "max_loops": max_loops,
                "research_profile": research_profile,
                "start_worker": start_worker,
                "source_profile": source_profile,
                "allow_domains": allow_domains,
                "deny_domains": deny_domains,
                "connector_budget": connector_budget,
                "file_inputs": file_inputs,
            }
            return SimpleNamespace(job_id="job-001", status="created")

    monkeypatch.setattr(main, "_build_job_service", lambda: FakeService())

    exit_code = main.run_command(
        [
            "submit",
            "--topic",
            "可信研究",
            "--max-loops",
            "4",
            "--profile",
            "benchmark",
            "--source-profile",
            "trusted-web",
            "--allow-domain",
            "docs.langchain.com",
            "--deny-domain",
            "reddit.com",
            "--max-candidates-per-connector",
            "4",
            "--max-fetches-per-task",
            "3",
            "--max-total-fetches",
            "8",
            "--json",
        ]
    )

    assert exit_code == 0
    assert captured["recovered"] is True
    assert captured["submit"] == {
        "topic": "可信研究",
        "max_loops": 4,
        "research_profile": "benchmark",
        "start_worker": True,
        "source_profile": "trusted-web",
        "allow_domains": ["docs.langchain.com"],
        "deny_domains": ["reddit.com"],
        "connector_budget": {
            "max_candidates_per_connector": 4,
            "max_fetches_per_task": 3,
            "max_total_fetches": 8,
        },
        "file_inputs": None,
    }
