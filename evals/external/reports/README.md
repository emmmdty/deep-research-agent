# External Benchmark Reports

This directory holds generated outputs from the external benchmark portfolio.

Current committed reviewer artifact:

- `portfolio_summary/portfolio_summary.json`
- `portfolio_summary/README.md`

Typical generation flow:

```bash
uv run python main.py benchmark run --benchmark facts_grounding --split open --subset smoke --output-root evals/external/reports/facts_grounding_open_smoke --json
uv run python scripts/build_benchmark_portfolio_summary.py --output-root evals/external/reports/portfolio_summary --json
```

The authoritative release gate still lives under `evals/reports/phase5_local_smoke/`.
