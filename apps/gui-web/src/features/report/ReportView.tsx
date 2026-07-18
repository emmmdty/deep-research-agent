import { Check, FileText, Link2 } from "lucide-react";
import ReactMarkdown from "react-markdown";

import type { Claim, ReportBundle } from "../../types";

export function ReportView({ bundle, onSelectClaim }: { bundle: ReportBundle; onSelectClaim: (claim: Claim) => void }) {
  const claims = [...bundle.accepted_claims, ...(bundle.qualified_claims ?? [])];
  return (
    <div className="report-reading-layout">
      <aside className="evidence-spine" aria-label="报告论断证据">
        <span className="spine-line" />
        {claims.map((claim, index) => (
          <button
            aria-label={`查看论断 ${claim.claim_id} 的证据`}
            className="spine-claim"
            key={claim.claim_id}
            onClick={() => onSelectClaim(claim)}
            style={{ top: `${8 + index * 13}rem` }}
            title={claim.claim ?? claim.claim_text}
            type="button"
          >
            <span>{index + 1}</span><Link2 size={13} />
          </button>
        ))}
      </aside>
      <article className="report-document">
        <div className="report-provenance"><span><Check size={13} />审计通过</span><span><FileText size={13} />Bundle {bundle.schema_version}</span><span>{claims.length} 个可追溯论断</span></div>
        <ReactMarkdown>{bundle.report_markdown}</ReactMarkdown>
      </article>
    </div>
  );
}
