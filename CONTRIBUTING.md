# Contributing

Thanks for your interest in this project.

## Development Setup

```bash
uv sync --group dev
cp .env.example .env
```

Fill in the required API keys in `.env` before running research or benchmark commands.

## Supported Entry Points

- `uv run python main.py submit --topic "your topic"`
- `uv run python main.py watch --job-id <job_id>`
- `uv run python scripts/run_benchmark.py --comparators ours,gptr,odr,alibaba`
- `uv run python scripts/full_comparison.py --comparators ours,gptr,odr,alibaba`
- `uv run python scripts/compare_agents.py --file-a report_a.md --file-b report_b.md`

## Before Opening a Pull Request

Run the full local verification:

```bash
uv run ruff check .
uv run pytest -q
```

If your change affects CLI behavior, comparator behavior, or public docs, update the relevant documentation in the same pull request.

## Repository Rules

- Do not commit secrets, `.env`, local virtual environments, or scratch scripts.
- Keep docs aligned with the actual supported surface.
- Prefer small, reviewable pull requests with clear commit messages.
- New public-facing behavior should include tests or an explicit explanation for why tests are not practical.
