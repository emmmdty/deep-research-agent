# DRB Gate

DRB（Deep Research Bench）引用真实性门禁的基线 scorecard。

- `scorecard.json`: `uv run python scripts/run_drb_gate.py` 生成的确定性基线产物
  （门禁状态 = passed，`verified_rate = 0.9 >= min_verified_rate = 0.9`）。
- 阈值与 fixture bundle 列表来自 `evals/external/configs/drb_gate.yaml`（脚本真实读取）。
- fixture bundle: `evals/fixtures/drb/citation_fixture.json`
  （`audit_summary.citation_verification`，summary 计数对齐
  `auditor/citation_verifier.py` 的 CitationVerificationReport）。
- 语义映射: `passed=verified`；`failed=unsupported+fetch_failed`；
  `unresolved=unverifiable`；`verified_rate = passed/(passed+failed+unresolved)`。
- 分母为空时 `verified_rate=None`，门禁判定 blocked（reason `no_citation_evidence`）。
