# 8. 目录级重构方案

## 8.1 新的顶层目录树

```text
.
├── src/
│   └── deep_research_agent/
│       ├── gateway/                     # [N] API / CLI / batch / review endpoints
│       │   ├── api/
│       │   ├── cli/
│       │   └── schemas/
│       ├── research_jobs/              # [M] <= services/research_jobs/
│       │   ├── contracts/
│       │   ├── orchestration/
│       │   ├── stages/
│       │   ├── repositories/
│       │   └── worker/
│       ├── connectors/                 # [M] <= connectors/ + tools/
│       │   ├── web/
│       │   ├── github/
│       │   ├── arxiv/
│       │   ├── files/
│       │   ├── mcp_bridge/
│       │   ├── legacy_adapter/
│       │   └── registry.py
│       ├── policy/                     # [M] <= policies/ + research_policy.py
│       │   ├── profiles/
│       │   ├── trust_taxonomy.py
│       │   ├── source_policy.py
│       │   └── budget.py
│       ├── evidence_store/             # [N/M] <= memory/evidence_store.py + snapshot logic
│       │   ├── documents/
│       │   ├── snapshots/
│       │   ├── chunks/
│       │   ├── evidence/
│       │   ├── claims/
│       │   └── repositories/
│       ├── auditor/                    # [M] <= auditor/
│       │   ├── pipeline.py
│       │   ├── gates.py
│       │   ├── review.py
│       │   └── store.py
│       ├── reporting/                  # [N/M] <= artifacts/ + new report delivery
│       │   ├── bundle/
│       │   ├── compiler/
│       │   ├── templates/
│       │   └── viewer_contract/
│       ├── providers/                  # [N/M] <= llm/provider.py + configs/settings.py
│       │   ├── openai.py
│       │   ├── anthropic.py
│       │   ├── openai_compat.py
│       │   ├── anthropic_compat.py
│       │   ├── router.py
│       │   └── capabilities.py
│       ├── retrieval/                  # [N]
│       │   ├── query_planning.py
│       │   ├── embeddings.py
│       │   ├── rerank.py
│       │   └── dedupe.py
│       ├── storage/                    # [N]
│       │   ├── db/
│       │   ├── object_store/
│       │   └── migrations/
│       ├── observability/              # [N]
│       │   ├── logging.py
│       │   ├── tracing.py
│       │   └── metrics.py
│       └── common/                     # [N]
│           ├── enums.py
│           ├── errors.py
│           └── utils.py
├── evals/                              # [N/M] <= evaluation/ + scripts/
│   ├── datasets/
│   ├── rubrics/
│   ├── suites/
│   ├── runners/
│   ├── graders/
│   ├── legacy_diagnostics/
│   └── reports/
├── tests/                              # [M]
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── reliability/
│   ├── adversarial/
│   └── fixtures/
├── configs/                            # [M]
│   ├── providers/
│   ├── source_profiles/
│   ├── runtime_profiles/
│   └── release_gates/
├── docs/                               # [K/M]
│   ├── adr/
│   ├── architecture/
│   ├── methodology/
│   ├── api/
│   └── demo/
├── scripts/                            # [M] thin wrappers only
├── legacy/                             # [A]
│   ├── agents/
│   ├── workflows/
│   ├── comparator/
│   ├── old_metrics/
│   └── migration_fixtures/
├── main.py                             # [M] thin wrapper to src CLI
└── pyproject.toml                      # [M]
```

## 8.2 各目录职责与迁移来源

* **保留目录**：`docs/adr`、`configs/`、`tests/` 的文化与大部分内容保留，但重排结构。
* **搬迁目录**：

  * `services/research_jobs/ -> src/.../research_jobs/`
  * `connectors/ -> src/.../connectors/`
  * `policies/ -> src/.../policy/`
  * `auditor/ -> src/.../auditor/`
  * `artifacts/ -> src/.../reporting/bundle/`
  * `llm/provider.py -> src/.../providers/`
* **新增目录**：

  * `gateway/`
  * `evidence_store/`
  * `retrieval/`
  * `storage/`
  * `observability/`
  * `evals/`
* **归档目录**：

  * `agents/`
  * `workflows/`
  * `legacy/` 原有内容
  * `evaluation/comparator*`
  * `memory/store.py`
* **删除目录/文件**：

  * 不直接删除 `main.py`，先变 wrapper
  * 删除未来主路径中对 `legacy-run`、旧 metrics 的依赖