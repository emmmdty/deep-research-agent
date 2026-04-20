# ADR-0004: 连接器统一采用 Search / Fetch / File-Ingest 合同

- Status: Accepted
- Date: 2026-04-09

## Context

当前仓库的来源能力主要以单独工具函数形式存在，适合原型研究，但不适合产品化的来源治理、snapshotting、policy enforcement 和 provenance tracking。

## Decision

建立统一 connector 合同：

- `SearchConnector`
- `FetchConnector`
- `FileIngestor`
- `CorpusConnector`

所有 connector 至少统一产出：

- `source_id`
- `canonical_uri`
- `fetched_at`
- `content_hash`
- `mime_type`
- `auth_scope`
- `freshness_metadata`
- `snapshot_ref`

Phase 01-03 的核心入口限定为：

- open web
- uploaded files
- GitHub
- arXiv

## Consequences

- 不再接受 ad hoc 工具绕开 snapshot 与 policy
- public/private staged research 可以建立在统一 source profile 之上
- connector 健康度、freshness、provenance completeness 可以成为一等运营指标

## Rejected Alternatives

### 每种来源单独走工具调用逻辑

拒绝原因：

- 会导致 provenance、permissions、crawling restrictions 和 freshness 口径不统一

### 先扩来源，再统一合同

拒绝原因：

- 会放大历史债务，后续很难统一迁移
