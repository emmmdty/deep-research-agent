"""Re-render committed report evidence with deterministic inline citations.

Every committed V2 bundle whose report body predates the citation injector is
re-processed: claim markers (``[[claim:<id>]]``) are replaced with numbered
references, verbatim claim sentences receive citations, and a numbered
``References`` section is appended. Bundle JSON and adjacent ``report.md`` are
kept in sync. Scores and ground-truth grades are untouched — this is a pure
rendering change.

Usage:
    uv run python scripts/rerender_reports.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from deep_research_agent.kernel.contracts import ArtifactRef, ClaimRecord
from deep_research_agent.reporting.bundle_v2 import ReportBundleCompilerV2
from deep_research_agent.reporting.citations import CitationInjector

ROOT = Path(__file__).resolve().parent.parent

BUNDLE_PATTERNS = (
    "evals/reports/live_benchmarks/gaia_real/*/report_bundle.json",
    "evals/reports/live_benchmarks/model_comparison*/**/report_bundle.json",
    "evals/reports/live_agent/*run_bundle.json",
    "evals/reports/live_agent/*bundle.json",
    "evals/reports/live_route_demo/*bundle.json",
)


def _bundle_files() -> list[Path]:
    found: list[Path] = []
    for pattern in BUNDLE_PATTERNS:
        for path in sorted(ROOT.glob(pattern)):
            if path not in found:
                found.append(path)
    return found


def _artifact_from_payload(item: dict) -> ArtifactRef:
    return ArtifactRef.model_validate(item)


def _claim_from_payload(item: dict) -> ClaimRecord:
    return ClaimRecord.model_validate(item)


_INLINE_CITATION_RE = re.compile(r"[ \t]*\[\d+(?:,\d+)*\]")
_REFERENCES_HEADING_RE = re.compile(r"^## References[ \t]*$", re.MULTILINE)
_REGISTER_HEADING_RE = re.compile(r"^## Claim Register[ \t]*$", re.MULTILINE)


def _restore_pristine_markdown(markdown: str) -> str:
    """Strip previously injected inline markers and appended sections.

    Makes the re-render idempotent: re-injecting over already-cited text must
    reproduce the pristine-render output exactly. Removes the ``[n]`` markers,
    the ``References`` section, and the ``Claim Register`` section.
    """
    markdown = _INLINE_CITATION_RE.sub("", markdown)
    for heading in (_REFERENCES_HEADING_RE, _REGISTER_HEADING_RE):
        match = heading.search(markdown)
        if match is not None:
            markdown = markdown[: match.start()].rstrip() + "\n"
    return markdown


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    injector = CitationInjector()
    report_dir = ROOT / "evals" / "reports" / "citation_rendering"
    report_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict] = []
    total_bundles = 0
    total_cited = 0
    total_uncited = 0
    total_register = 0

    for bundle_path in _bundle_files():
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "2.0":
            continue
        total_bundles += 1
        claims = [
            _claim_from_payload(item)
            for key in ("accepted_claims", "qualified_claims")
            for item in payload.get(key, [])
        ]
        spans = [span for claim in claims for span in claim.evidence_spans]
        sources = [_artifact_from_payload(item) for item in payload.get("sources", [])]
        pristine = _restore_pristine_markdown(payload.get("report_markdown", ""))
        # Mirror the compiler's executive-summary rebuild (top-5 critical-first
        # bullets) so the re-render matches what the runtime emits today.
        top_summary = ReportBundleCompilerV2._top_executive_summary_claims(claims)
        pristine = ReportBundleCompilerV2._rebuild_executive_summary(pristine, top_summary)
        result = injector.inject(pristine, claims, spans, sources)
        payload["report_markdown"] = result.markdown
        payload["audit_summary"]["report_citation_coverage"] = dict(result.coverage)
        _write_json(bundle_path, payload)

        report_md = bundle_path.parent / "report.md"
        if not report_md.exists():
            report_md = bundle_path.parent / "live_agent_report.md"
        if report_md.exists():
            report_md.write_text(result.markdown, encoding="utf-8")

        summaries.append(
            {
                "bundle": str(bundle_path.relative_to(ROOT)),
                "supported_claims": result.coverage["supported_claim_count"],
                "cited_in_prose": result.coverage["cited_in_prose"],
                "uncited_in_prose": result.coverage["uncited_claim_count"],
                "register_entries": result.coverage["register_entries"],
                "marker_cited": len(result.marker_cited_claim_ids),
                "verbatim_cited": len(result.verbatim_cited_claim_ids),
                "dropped_markers": result.dropped_markers,
            }
        )
        total_cited += result.coverage["cited_in_prose"]
        total_uncited += result.coverage["uncited_claim_count"]
        total_register += result.coverage["register_entries"]
        print(
            f"re-rendered {bundle_path.relative_to(ROOT)} "
            f"({result.coverage['cited_in_prose']}/{result.coverage['supported_claim_count']} "
            f"claims cited in prose; register: {result.coverage['register_entries']})"
        )

    report_dir.joinpath("rerender_summary.json").write_text(
        json.dumps(
            {
                "bundles_rerendered": total_bundles,
                "claims_cited_in_prose_total": total_cited,
                "claims_uncited_in_prose_total": total_uncited,
                "claims_register_total": total_register,
                "per_bundle": summaries,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    report_dir.joinpath("README.md").write_text(
        "\n".join(
            [
                "# Citation Rendering Evidence",
                "",
                "Deterministic re-render of all committed live-lane report bundles through the",
                "inline-citation injector (`deep_research_agent.reporting.citations`). Pure",
                "rendering change: benchmark scores, grades, and claim audits are untouched.",
                "",
                "- Bundles re-rendered: " + str(total_bundles),
                f"- Claims cited in prose: {total_cited}",
                f"- Claims uncited in prose (paraphrased, covered by the register): {total_uncited}",
                f"- Claim Register entries (every supported claim, cited): {total_register}",
                "",
                "Every supported claim is traceable: prose carries inline `[n]` references where",
                "the synthesizer marked or verbatim-matched it, and the appended `## Claim",
                "Register` lists all accepted/qualified claims with their source numbers.",
                "The executive summary is capped at the top-5 critical-first findings.",
                "",
                "See `rerender_summary.json` for per-bundle coverage.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\ndone: {total_bundles} bundles re-rendered, {total_cited} claims cited in prose")


if __name__ == "__main__":
    main()
