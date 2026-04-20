# Push 与 Cleanup Checklist

- 生成时间：`2026-04-20T16:12:53Z`
- Phase 7 基线：`main@cf8b0a8`
- 注意：不要直接 push，除非已经完成本清单中的本地检查。

## 1. Push 前检查项

执行：

```bash
git status --short
git log --oneline --decorate -n 25
git rev-list --count origin/main..HEAD
git rev-list --count HEAD..origin/main
git worktree list
```

确认：

- `main` 在最新本轮收官提交上。
- `HEAD..origin/main` 为 `0`。
- `origin/main..HEAD` 只包含本轮 Phase 0-7 相关提交。
- 主工作区的既有脏改动没有被暂存。
- 没有 accidental staged files。

## 2. 推荐 Push 命令

```bash
git push origin main
```

如果远端有新提交，先不要 force push。应先：

```bash
git fetch origin main
git log --oneline --decorate --left-right main...origin/main
```

确认差异后再决定 rebase 或 merge。

## 3. Phase Worktree 是否可删除

可以删除，但不是必须删除。

建议保留到以下条件满足后再删除：

- `main` 已成功 push。
- 远端 CI 或本地最终验收通过。
- 不再需要逐 phase 查看中间 diff。

当前 phase worktrees：

- `../dra-phase-01-runtime-state-persistence`
- `../dra-phase-02-orchestration-recovery-contract`
- `../dra-phase-03-connector-policy-security`
- `../dra-phase-04-claim-evidence-audit`
- `../dra-phase-05-observability-release-governance`
- `../dra-phase-06-api-readiness`
- `../dra-phase-07-finalize`

## 4. 推荐 Cleanup 命令

删除前先确认每个 worktree clean：

```bash
git -C ../dra-phase-01-runtime-state-persistence status --short
git -C ../dra-phase-02-orchestration-recovery-contract status --short
git -C ../dra-phase-03-connector-policy-security status --short
git -C ../dra-phase-04-claim-evidence-audit status --short
git -C ../dra-phase-05-observability-release-governance status --short
git -C ../dra-phase-06-api-readiness status --short
git -C ../dra-phase-07-finalize status --short
```

确认 clean 后再执行：

```bash
git worktree remove ../dra-phase-01-runtime-state-persistence
git worktree remove ../dra-phase-02-orchestration-recovery-contract
git worktree remove ../dra-phase-03-connector-policy-security
git worktree remove ../dra-phase-04-claim-evidence-audit
git worktree remove ../dra-phase-05-observability-release-governance
git worktree remove ../dra-phase-06-api-readiness
git worktree remove ../dra-phase-07-finalize
```

删除 worktree 后，如需删除本地 phase 分支：

```bash
git branch -d refactor/phase-01-runtime-state-persistence
git branch -d refactor/phase-02-orchestration-recovery-contract
git branch -d refactor/phase-03-connector-policy-security
git branch -d refactor/phase-04-claim-evidence-audit
git branch -d refactor/phase-05-observability-release-governance
git branch -d refactor/phase-06-api-readiness
git branch -d refactor/phase-07-finalize
```

## 5. 绝对不要删

不要删除或重置主工作区中的既有脏改动和未跟踪文件，包括但不限于：

- `.env.example`、README、configs、scripts、tests、workflows 等 mode-only 或本地改动。
- `docs/deep-research-agent-beginner-guide.md`
- `docs/interview_qa.md`
- `docs/plans/`
- `docs/resume_bullets.md`
- `docs/showcase.md`
- `docs/审查意见.md`
- `prompts/codex/`

不要执行：

```bash
git reset --hard
git clean -fd
git checkout -- .
```

## 6. 如何避免误伤主工作区

- 清理只用 `git worktree remove <phase-worktree>`，不要手动 `rm -rf` 主仓库目录。
- 提交前用 `git diff --cached --name-only` 确认只暂存预期文件。
- 如需保护主工作区 mode-only 改动，优先使用 path-scoped stash，例如：

```bash
git stash push -m pre-cleanup-mode -- README.md docs/architecture.md
git stash pop
```

- 不要把主工作区未跟踪文档加入本轮重构提交，除非用户明确要求。
