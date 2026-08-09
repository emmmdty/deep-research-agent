import { useState } from "react";
import { Sparkles, BookOpen, Info } from "lucide-react";
import { HomePage } from "./components/HomePage";
import { ResearchPage } from "./components/ResearchPage";
import { ReportBrowser } from "./components/ReportBrowser";
import { AboutPage } from "./components/AboutPage";

export type Tab = "home" | "research" | "reports" | "about";

const TABS: Array<{ id: Tab; label: string; icon: React.ReactNode }> = [
  { id: "home", label: "首页", icon: <Sparkles size={15} /> },
  { id: "research", label: "发起研究", icon: <Sparkles size={15} /> },
  { id: "reports", label: "示例报告", icon: <BookOpen size={15} /> },
  { id: "about", label: "关于本项目", icon: <Info size={15} /> },
];

export function App() {
  const parseHash = () => {
    const raw = window.location.hash.replace(/^#\/?/, "");
    const [path, query = ""] = raw.split("?");
    const params = new URLSearchParams(query);
    return { path, q: params.get("q") ?? "" };
  };
  const initial = parseHash();
  const initialTab = (): Tab => {
    return (["home", "research", "reports", "about"] as Tab[]).includes(initial.path as Tab)
      ? (initial.path as Tab)
      : "home";
  };
  const [tab, setTab] = useState<Tab>(initialTab);
  const [question, setQuestion] = useState<string>(initial.q);

  const navigate = (next: Tab) => {
    setTab(next);
    window.location.hash = `#/${next}`;
    window.scrollTo({ top: 0 });
  };

  const startResearch = (questionText: string) => {
    setQuestion(questionText);
    setTab("research");
    window.location.hash = `#/research?q=${encodeURIComponent(questionText)}`;
    window.scrollTo({ top: 0 });
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-title">
          <span className="logo">DRA</span>
          <div>
            <div className="app-name">Deep Research Agent</div>
            <div className="app-sub">深度研究助手 · 在线体验</div>
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
        {tab === "home" && <HomePage startResearch={startResearch} navigate={navigate} />}
        {tab === "research" && <ResearchPage question={question} />}
        {tab === "reports" && <ReportBrowser />}
        {tab === "about" && <AboutPage />}
      </main>

      <footer className="app-footer">
        <span>
          开源（MIT）· 本地可一键运行 ·{" "}
          <a href="https://github.com/emmmdty/deep-research-agent" target="_blank" rel="noreferrer">
            源码仓库
          </a>
        </span>
      </footer>
    </div>
  );
}
