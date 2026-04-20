"""Phase 05 release gate 回归测试。"""

from __future__ import annotations


def test_release_gate_blocks_benchmark_only_evidence():
    """benchmark diagnostics 不能单独让 release gate 通过。"""
    from scripts.release_gate import evaluate_release_gate, load_release_gate_config

    config = load_release_gate_config()
    result = evaluate_release_gate(
        {
            "benchmark-diagnostics": {
                "status": "passed",
                "summary": "portfolio12 benchmark completed",
            }
        },
        config=config,
    )

    assert result["status"] == "blocked"
    assert result["categories"]["benchmark_diagnostics"]["status"] == "passed"
    assert result["categories"]["runtime_reliability"]["status"] == "missing"
    assert result["categories"]["audit_grounding"]["status"] == "missing"
    assert any("runtime-job-recovery" in reason for reason in result["block_reasons"])


def test_release_gate_passes_when_all_required_domains_have_evidence():
    """runtime/security/audit/docs/benchmark 分组都有证据时 gate 才能通过。"""
    from scripts.release_gate import evaluate_release_gate, load_release_gate_config

    config = load_release_gate_config()
    evidence = {check["id"]: {"status": "passed"} for check in config["checks"]}

    result = evaluate_release_gate(evidence, config=config)

    assert result["status"] == "passed"
    assert result["required_check_count"] == result["passed_required_check_count"]
