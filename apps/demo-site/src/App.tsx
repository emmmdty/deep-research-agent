import { useState } from "react";
import { BookOpen, GitBranch, PlayCircle, Scale, Boxes } from "lucide-react";
import { HomePage } from "./components/HomePage";
import { ReportBrowser } from "./components/ReportBrowser";
import { ClaimGraphView } from "./components/ClaimGraphView";
import { TraceReplay } from "./components/TraceReplay";
import { BenchmarkPage } from "./components/BenchmarkPage";
import { ArchitecturePage } from "./components/ArchitecturePage";

export type Tab = "home" | "reports" | "graph" | "trace" | "benchmark" | "architecture";

const TABS: Array<{ id: Tab; label: string; icon: React.ReactNode }> = [
  { id: "home", label: "Overview", icon: <Boxes size={15} /> },
  { id: "reports", label: "Report Bundles", icon: <BookOpen size={15} /> },
  { id: "graph", label: "Claim Graph", icon: <GitBranch size={15} /> },
  { id: "trace", label: "Agent Trace", icon: <PlayCircle size={15} /> },
  { id: "benchmark", label: "Benchmark", icon: <Scale size={15} /> },
  { id: "architecture", label: "Architecture", icon: <Boxes size={15} /> },
];

export function App() {
  const [tab, setTab] = useState<Tab>("home");
  const [selectedRun, setSelectedRun] = useState("dsv4-20260425");

  const navigate = (next: Tab, runId?: string) => {
    if (runId) setSelectedRun(runId);
    setTab(next);
    window.scrollTo({ top: 0 });
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-title">
          <span className="logo">DRA</span>
          <div>
            <div className="app-name">Deep Research Agent</div>
            <div className="app-sub">evidence-first multi-agent research · live demo</div>
          </div>
        </div>
        <nav className="app-nav">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`nav-btn${tab === t.id ? " active" : ""}`}
              onClick={() => navigate(t.id)}
            >
              {t.icon}
              <span>{t.label}</span>
            </button>
          ))}
        </nav>
        <a
          className="gh-link"
          href="https://github.com/emmmdty/deep-research-agent"
          target="_blank"
          rel="noreferrer"
        >
          GitHub ↗
        </a>
      </header>

      <main className="app-main">
        {tab === "home" && <HomePage navigate={navigate} />}
        {tab === "reports" && (
          <ReportBrowser selectedRun={selectedRun} onSelectRun={setSelectedRun} />
        )}
        {tab === "graph" && <ClaimGraphView selectedRun={selectedRun} onSelectRun={setSelectedRun} />}
        {tab === "trace" && <TraceReplay selectedRun={selectedRun} onSelectRun={setSelectedRun} />}
        {tab === "benchmark" && <BenchmarkPage />}
        {tab === "architecture" && <ArchitecturePage />}
      </main>

      <footer className="app-footer">
        <span>
          Open-source (MIT) · deterministic evaluation runs locally without API keys ·{" "}
          <a href="https://github.com/emmmdty/deep-research-agent" target="_blank" rel="noreferrer">
            repository
          </a>
        </span>
      </footer>
    </div>
  );
}
