import { CheckCircle2, CircleAlert } from "lucide-react";

import type { Claim } from "../../types";

export function EvidenceList({ claims, onSelect }: { claims: Claim[]; onSelect: (claim: Claim) => void }) {
  if (!claims.length) return <div className="view-empty">这份报告还没有通过审计的论断。</div>;
  return (
    <div className="claim-ledger">
      {claims.map((claim) => {
        const supported = (claim.support_status ?? claim.status) !== "contradicted";
        return (
          <button className="claim-ledger-row" key={claim.claim_id} onClick={() => onSelect(claim)} type="button">
            {supported ? <CheckCircle2 className="supported" /> : <CircleAlert className="contradicted" />}
            <span><strong>{claim.claim ?? claim.claim_text}</strong><small>{claim.evidence_spans.length} 个证据片段 · {claim.confidence == null ? "已审计" : `${Math.round(claim.confidence * 100)}% 置信度`}</small></span>
            <code>{claim.claim_id}</code>
          </button>
        );
      })}
    </div>
  );
}
