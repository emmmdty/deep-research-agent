import { ExternalLink, FileSearch, X } from "lucide-react";

import type { EvidenceSpan } from "../../types";

function locator(span: EvidenceSpan): string {
  const location = span.locator ?? span;
  const parts: string[] = [];
  if (location.page) parts.push(`page ${location.page}`);
  if (location.section) parts.push(`section ${location.section}`);
  if (location.start_offset != null && location.end_offset != null) parts.push(`chars ${location.start_offset}-${location.end_offset}`);
  return parts.join(" · ") || "document locator";
}

export function EvidenceDrawer({ spans, onClose }: { spans: EvidenceSpan[]; onClose: () => void }) {
  return (
    <aside className="evidence-drawer" aria-label="证据详情">
      <header className="drawer-heading">
        <div><span className="section-label">来源定位</span><h2>证据详情</h2></div>
        <button className="icon-button" aria-label="关闭证据" onClick={onClose} type="button"><X /></button>
      </header>
      {spans.length === 0 ? <div className="drawer-empty"><FileSearch /><p>这个关系没有绑定可读取的证据片段。</p></div> : null}
      <div className="evidence-stack">
        {spans.map((span) => (
          <article className="evidence-record" key={span.span_id}>
            <div className="evidence-record-head">
              <span className="trust-mark">可追溯</span>
              <code>{locator(span)}</code>
            </div>
            <h3>{span.title ?? span.document_version_id ?? span.document_id ?? "来源文档"}</h3>
            <blockquote>{span.quote ?? span.text}</blockquote>
            <footer>
              <code>{span.span_id}</code>
              {span.source_url ? <a href={span.source_url} rel="noreferrer" target="_blank">查看原文 <ExternalLink size={13} /></a> : null}
            </footer>
          </article>
        ))}
      </div>
    </aside>
  );
}
