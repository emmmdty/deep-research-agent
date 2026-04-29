# User Guide

## 1. Configure Credentials

Copy `.env.example` to `.env` and set at least one provider key. The default provider is `openai_compatible`.

For web search, set `TAVILY_API_KEY`. If it is not set, the runtime can fall back to DuckDuckGo for public web search.

## 2. Submit Jobs

```bash
uv run python main.py submit \
  --topic "Anthropic company profile" \
  --source-profile company_trusted \
  --json
```

Use `--no-worker` when you only want to create a job record and inspect the runtime contract.

## 3. Monitor Jobs

```bash
uv run python main.py status --job-id <job_id>
uv run python main.py watch --job-id <job_id>
```

`watch` streams job events until the job reaches `completed`, `failed`, or `cancelled`.

## 4. Recover or Refine

```bash
uv run python main.py cancel --job-id <job_id>
uv run python main.py retry --job-id <job_id>
uv run python main.py resume --job-id <job_id>
uv run python main.py refine --job-id <job_id> --instruction "Add more source detail"
```

Retry creates a new job from a failed or cancelled job. Resume continues the same job from the latest checkpoint. Refine records a user instruction and resumes from the safe refinement boundary.

## 5. Open Artifacts

```bash
uv run python main.py bundle --job-id <job_id> --json
```

The Web UI provides the same artifact links through the local API.
