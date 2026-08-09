import { useState } from "react";
import { Home as HomeIcon, PlayCircle, BookOpen, Scale, Boxes } from "lucide-react";
import { HomePage } from "./components/HomePage";
import { DemoPage } from "./components/DemoPage";
import { ReportBrowser } from "./components/ReportBrowser";
import { BenchmarkPage } from "./components/BenchmarkPage";
import { ArchitecturePage } from "./components/ArchitecturePage";

export type Tab = "home" | "demo" | "reports" | "benchmark" | "architecture";

const TABS: Array<{ id: Tab; label: string; hint: string; icon: React.ReactNode }> = [
  { id: "home", label: "首页", hint: "这是什么", icon: <HomeIcon size={15} /> },
  { id: "demo", label: "端到端演示", hint: "一个研究任务如何完成", icon: <PlayCircle size={15} /> },
  { id: "reports", label: "报告与证据", hint: "案例库", icon: <BookOpen size={15} /> },
  { id: "benchmark", label: "评测证据", hint: "它可信吗", icon: <Scale size={15} /> },
  { id: "architecture", label: "技术实现", hint: "怎么做到的", icon: <Boxes size={15} /> },
];

export function App() {
  const initialTab = (): Tab => {
    const hash = window.location.hash.replace(/^#\/?/, "");
    return (["home", "demo", "reports", "benchmark", "architecture"] as Tab[]).includes(
      hash as Tab
    )
      ? (hash as Tab)
      : "home";
  };
  const [tab, setTab] = useState<Tab>(initialTab);

  const navigate = (next: Tab) => {
    setTab(next);
    window.location.hash = `#/${next}`;
    window.scrollTo({ top: 0 });
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-title">
          <span className="logo">DRA</span>
          <div>
            <div className="app-name">Deep Research Agent</div>
            <div className="app-sub">多 agent 深度研究系统 · 在线演示</div>
          </div>
        </div>
        <nav className="app-nav">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`nav-btn${tab === t.id ? " active" : ""}`}
              onClick={() => navigate(t.id)}
              title={t.hint}
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
        {tab === "demo" && <DemoPage />}
        {tab === "reports" && <ReportBrowser />}
        {tab === "benchmark" && <BenchmarkPage />}
        {tab === "architecture" && <ArchitecturePage />}
      </main>

      <footer className="app-footer">
        <span>
          开源（MIT）· 确定性评测本地可复现，无需 API key ·{" "}
          <a href="https://github.com/emmmdty/deep-research-agent" target="_blank" rel="noreferrer">
            源码仓库
          </a>
        </span>
      </footer>
    </div>
  );
}
