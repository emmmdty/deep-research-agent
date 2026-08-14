"""Real GAIA 2023 validation runner for the canonical scheduler-v2 agent.

Runs the model-driven evidence-first agent (live LLM + governed web/GitHub/arXiv
search) on a frozen sample of the GAIA 2023 validation set (text-only questions,
no attachments), extracts an answer from the synthesized report, and grades it
against the ground truth with both exact-match and an LLM judge.

This is the live agent lane for the external benchmark portfolio: unlike the
guarded smoke adapters (``evals/external/benchmarks/gaia.py``), every question
here executes the real runtime against real providers and reports honest scores,
including per-question artifacts and error samples.

Usage (requires LLM_API_KEY / LLM_BASE_URL / TAVILY_API_KEY in .env):

    SCHEDULER_RUNTIME_MODE=production \\
        uv run python scripts/run_gaia_real.py --max-questions 20

Chunked/resumable: pass ``--start-index`` / ``--max-questions``; questions whose
output directory already exists are skipped.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from configs.settings import get_settings  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from loguru import logger  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from deep_research_agent.agents.factory import MultiRoleWorker, build_gateway
from deep_research_agent.agents.critic import LLMCriticWorker
from deep_research_agent.agents.llm import LLMChat
from deep_research_agent.agents.planner import LLMResearchPlanner
from deep_research_agent.agents.researcher import LLMResearcherWorker
from deep_research_agent.domain_packs.registry import DomainPackRegistry
from deep_research_agent.kernel.contracts import CorpusManifest, ResearchBrief, ResearchGraph
from deep_research_agent.observability.cost_tracker import get_tracker
from deep_research_agent.orchestration.dag import ResearchPlanner
from deep_research_agent.orchestration.scheduler import ResearchScheduler, SchedulerJob
from deep_research_agent.reporting.bundle_v2 import ReportBundleCompilerV2

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    PROJECT_ROOT
    / "evals"
    / "external"
    / "dataset_manifests"
    / "gaia_2023_val_text_sample20.json"
)
DEFAULT_OUT_DIR = PROJECT_ROOT / "evals" / "reports" / "live_benchmarks" / "gaia_real"

_ANSWER_EXTRACT_SYSTEM = (
    "You are an answer extractor for a question-answering benchmark. "
    "Given a research report and the original question, extract the concise final "
    'answer the report supports. Respond with JSON only: {"answer": "..."}. '
    "Keep the answer short (at most 100 words). If the report does not answer the "
    'question, respond with {"answer": ""}.'
)

_JUDGE_SYSTEM = (
    "You are a strict, fair judge for the GAIA benchmark. Given the original "
    "question, the ground truth answer, and a candidate answer produced by a "
    "research agent, decide whether the candidate answer is CORRECT. "
    "GAIA answers can be numbers, names, codes, lists, or short phrases. "
    "Ignore minor formatting differences (case, punctuation, spacing, trailing "
    "periods, article words). If the candidate is a paraphrase of the ground "
    "truth or answers the question with equivalent content, mark it correct. "
    'Respond with JSON only: {"correct": true or false, "rationale": "..."}'
)


def _job_id() -> str:
    return f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"


def _normalize(text: str) -> str:
    """Normalize for exact-match grading."""
    text = text.strip().casefold()
    text = re.sub(r"\s+", " ", text)
    return text.rstrip(".").strip()


async def _run_one_question(question: dict, out_dir: Path) -> dict:
    """Run the full agent pipeline on one GAIA question and grade the result."""
    settings = get_settings()
    if not settings.llm_api_key or not settings.tavily_api_key:
        raise SystemExit("LLM and TAVILY credentials are required for the live lane")

    job_id = _job_id()
    task_id = question["task_id"]
    brief = ResearchBrief(
        brief_id=f"brief-{job_id}",
        job_id=job_id,
        question=question["question"],
        objectives=[question["question"]],
        constraints={"answer_in_chinese": False, "focus": "answer the question precisely"},
        domain_pack_id="event-graph-agents-llms",
    )
    domain_pack = DomainPackRegistry().load(brief.domain_pack_id)
    dag = ResearchPlanner().plan(brief, domain_pack)
    dag = LLMResearchPlanner._ensure_tool_budget(dag)

    gateway = build_gateway()
    worker = MultiRoleWorker(researcher=LLMResearcherWorker(), critic=LLMCriticWorker())
    scheduler = ResearchScheduler(worker=worker, tool_gateway=gateway, max_workers=1, max_attempts=2)

    started = time.monotonic()
    logger.info("[{}] running agent on GAIA question: {}...", task_id, question["question"][:90])
    result = await scheduler.run(
        SchedulerJob(job_id=job_id, tenant_id="benchmark"),
        dag,
        {"model": "scheduler-v2-live", "benchmark": "gaia-2023-validation", "question_id": task_id},
    )
    wall_seconds = round(time.monotonic() - started, 2)

    sources: list = []
    claims: list = []
    packets: list = []
    for task_result in result.task_results.values():
        for packet in task_result.evidence_packets:
            packets.append(packet)
            claims.extend(packet.claims)
            sources.extend(packet.artifacts)

    critic_output = result.task_outputs.get("critic", {})
    report_markdown = str(critic_output.get("report_markdown") or "")
    graph_payload = critic_output.get("research_graph") or {"nodes": [], "edges": []}
    if isinstance(graph_payload, dict):
        research_graph = ResearchGraph.model_validate(graph_payload)
    else:
        research_graph = graph_payload
    corpus_manifest = CorpusManifest(
        manifest_id=f"corpus:{job_id}",
        document_version_ids=tuple(
            sorted(
                {
                    artifact.metadata.get("document_version_id")
                    for artifact in sources
                    if artifact.metadata.get("document_version_id")
                }
            )
        ),
        content_hashes={
            artifact.metadata.get("document_version_id"): artifact.content_sha256
            for artifact in sources
            if artifact.metadata.get("document_version_id")
        },
        critical_claims_allowed={
            artifact.metadata.get("document_version_id"): True
            for artifact in sources
            if artifact.metadata.get("document_version_id")
        },
    )
    bundle = ReportBundleCompilerV2().compile(
        report_markdown=report_markdown,
        claims=claims,
        evidence_packets=packets,
        critic_decisions=result.critic_decisions,
        research_graph=research_graph,
        sources=sources,
        corpus_manifest=corpus_manifest,
        run_manifest={"job_id": job_id, "status": result.status},
    )

    tracker = get_tracker().metrics
    cost = tracker.to_dict()
    cost["wall_seconds"] = wall_seconds

    answer = await _extract_answer(report_markdown, question["question"])
    grade = await _grade(question, answer)

    record = {
        "task_id": task_id,
        "question": question["question"],
        "level": question["level"],
        "ground_truth": question["ground_truth"],
        "extracted_answer": answer,
        "grade": grade,
        "exact_match": _normalize(answer) == _normalize(question["ground_truth"]),
        "job_id": job_id,
        "status": result.status,
        "claim_count": len(claims),
        "source_count": len(sources),
        "cost": cost,
        "model": settings.llm_model_name,
    }
    qdir = out_dir / task_id
    qdir.mkdir(parents=True, exist_ok=True)
    (qdir / "record.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    (qdir / "report.md").write_text(report_markdown, encoding="utf-8")
    (qdir / "report_bundle.json").write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    (qdir / "scheduler_checkpoints.json").write_text(
        json.dumps([c.model_dump(mode="json") for c in result.checkpoints], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(
        "[{}] done: correct={} exact={} claims={} sources={} wall={}s",
        task_id,
        grade.get("correct"),
        record["exact_match"],
        len(claims),
        len(sources),
        wall_seconds,
    )
    return record


async def _extract_answer(report_markdown: str, question: str) -> str:
    try:
        chat = LLMChat()
        payload = await chat.chat_json(
            system=_ANSWER_EXTRACT_SYSTEM,
            user=f"Question:\n{question}\n\nResearch report:\n{report_markdown[:24000]}",
            max_tokens=512,
            temperature=0.0,
        )
        return str(payload.get("answer") or "").strip()
    except Exception as exc:
        logger.warning("answer extraction failed: {}", exc)
        return ""


async def _grade(question: dict, answer: str) -> dict:
    try:
        chat = LLMChat()
        payload = await chat.chat_json(
            system=_JUDGE_SYSTEM,
            user=(
                f"Question: {question['question']}\n\n"
                f"Ground truth: {question['ground_truth']}\n\n"
                f"Candidate answer: {answer or '(empty)'}"
            ),
            max_tokens=256,
            temperature=0.0,
        )
        return {
            "correct": bool(payload.get("correct")),
            "rationale": str(payload.get("rationale") or ""),
            "judge_model": chat.model_name,
        }
    except Exception as exc:
        logger.warning("grading failed: {}", exc)
        return {"correct": False, "rationale": f"judge error: {exc}", "judge_model": None}


def _write_summary(records: list[dict], out_dir: Path) -> dict:
    correct = sum(1 for r in records if r.get("grade", {}).get("correct"))
    exact = sum(1 for r in records if r.get("exact_match"))
    by_level = Counter()
    correct_by_level = Counter()
    for r in records:
        by_level[r["level"]] += 1
        if r.get("grade", {}).get("correct"):
            correct_by_level[r["level"]] += 1

    total_cost_usd = sum(r.get("cost", {}).get("estimated_cost_usd", 0.0) for r in records)
    total_tokens = sum(r.get("cost", {}).get("total_tokens", 0) for r in records)
    total_wall = sum(r.get("cost", {}).get("wall_seconds", 0.0) for r in records)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark": "GAIA 2023 validation (text-only sample)",
        "questions": len(records),
        "judge_correct": correct,
        "judge_accuracy": round(correct / len(records), 4) if records else 0.0,
        "exact_match": exact,
        "exact_match_rate": round(exact / len(records), 4) if records else 0.0,
        "accuracy_by_level": {lv: round(correct_by_level[lv] / by_level[lv], 4) if by_level[lv] else 0.0 for lv in sorted(by_level)},
        "total_llm_tokens": total_tokens,
        "total_estimated_cost_usd": round(total_cost_usd, 4),
        "total_wall_seconds": round(total_wall, 2),
        "per_question": [{"task_id": r["task_id"], "level": r["level"], "correct": r.get("grade", {}).get("correct"), "exact": r.get("exact_match")} for r in records],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _write_report(records: list[dict], summary: dict, out_dir: Path) -> None:
    lines = [
        "# GAIA 2023 Validation — Live Agent Run",
        "",
        "Real runs of the canonical scheduler-v2 model-driven agent (live LLM + governed "
        "web/GitHub/arXiv search + full-page reads) on a frozen text-only sample of the "
        "GAIA 2023 validation set.",
        "",
        f"- Questions: {summary['questions']} (stratified: {summary['accuracy_by_level']})",
        f"- Judge accuracy: **{summary['judge_accuracy']:.2%}** ({summary['judge_correct']}/{summary['questions']})",
        f"- Exact match: {summary['exact_match_rate']:.2%}",
        f"- LLM tokens: {summary['total_llm_tokens']} | est. cost: ~${summary['total_estimated_cost_usd']:.2f}",
        f"- Wall time: {summary['total_wall_seconds']:.0f}s",
        "",
        "> Honesty notes: the judge uses the same model family as the agent "
        "(an LLM judge is the standard GAIA validation practice); answers are "
        "extracted from the synthesized report. Per-question bundles, checkpoints, "
        "and grading rationales are committed alongside this summary.",
        "",
        "## Per-Question Results",
        "",
        "| Task | Level | Judge | Exact | Answer (excerpt) |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for r in records:
        ans = (r.get("extracted_answer") or "(empty)").replace("|", "/")
        lines.append(
            f"| `{r['task_id'][:8]}` | {r['level']} | {'✅' if r.get('grade', {}).get('correct') else '❌'} | "
            f"{'✅' if r.get('exact_match') else '❌'} | {ans[:80]} |"
        )
    lines.extend(["", "## Error Samples (rationales)", ""])
    for r in records:
        if not r.get("grade", {}).get("correct"):
            lines.append(f"### {r['task_id'][:8]} (L{r['level']})")
            lines.append(f"- Question: {r['question']}")
            lines.append(f"- Ground truth: {r['ground_truth']}")
            lines.append(f"- Model answer: {r.get('extracted_answer') or '(empty)'}")
            lines.append(f"- Judge rationale: {r.get('grade', {}).get('rationale', '')}")
            lines.append("")
    (out_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run real GAIA 2023 validation questions")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--max-questions", type=int, default=20)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level:^8}</level> | {message}", level="INFO")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    questions = manifest["questions"][args.start_index : args.start_index + args.max_questions]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    for q in questions:
        if (args.out_dir / q["task_id"] / "record.json").exists():
            records.append(json.loads((args.out_dir / q["task_id"] / "record.json").read_text(encoding="utf-8")))
            logger.info("[{}] already done, skipping", q["task_id"][:8])
            continue
        try:
            records.append(asyncio.run(_run_one_question(q, args.out_dir)))
        except Exception as exc:
            logger.error("[{}] failed: {}", q["task_id"][:8], exc)
            records.append(
                {
                    "task_id": q["task_id"],
                    "question": q["question"],
                    "level": q["level"],
                    "ground_truth": q["ground_truth"],
                    "extracted_answer": "",
                    "grade": {"correct": False, "rationale": f"run error: {exc}"},
                    "exact_match": False,
                    "status": "failed",
                    "cost": {},
                }
            )
            (args.out_dir / q["task_id"]).mkdir(parents=True, exist_ok=True)
            (args.out_dir / q["task_id"] / "record.json").write_text(
                json.dumps(records[-1], ensure_ascii=False, indent=2), encoding="utf-8"
            )

    summary = _write_summary(records, args.out_dir)
    _write_report(records, summary, args.out_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
