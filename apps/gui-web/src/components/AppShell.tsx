import { useQuery } from "@tanstack/react-query";
import { BrainCircuit, Menu, Network, Settings2, X } from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { productApi } from "../api/client";

const primaryLinks = [
  { to: "/topics", label: "研究", icon: Network },
  { to: "/memory", label: "记忆", icon: BrainCircuit },
  { to: "/admin/models", label: "管理", icon: Settings2 },
];

function PrimaryLinks({ onNavigate }: { onNavigate?: () => void }) {
  return primaryLinks.map(({ to, label, icon: Icon }) => (
    <NavLink className={({ isActive }) => isActive ? "global-link active" : "global-link"} key={to} onClick={onNavigate} to={to}>
      <Icon aria-hidden="true" size={17} />
      <span>{label}</span>
    </NavLink>
  ));
}

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const topics = useQuery({ queryKey: ["topics"], queryFn: () => productApi.listTopics() });

  return (
    <div className="product-shell">
      <header className="topbar">
        <a className="wordmark" href="/topics" aria-label="Evidence Research 首页">
          <span className="wordmark-mark">ER</span>
          <span>Evidence Research</span>
        </a>
        <nav className="global-nav" aria-label="主导航"><PrimaryLinks /></nav>
        <div className="topbar-actions">
          <span className="system-state"><i />系统可用</span>
          <button className="icon-button mobile-only" aria-label="打开导航" onClick={() => setMobileOpen(true)} type="button"><Menu /></button>
        </div>
      </header>

      {mobileOpen ? (
        <div className="mobile-nav-layer">
          <button className="mobile-nav-scrim" aria-label="关闭导航遮罩" onClick={() => setMobileOpen(false)} type="button" />
          <nav className="mobile-nav" aria-label="移动导航">
            <div className="drawer-heading"><strong>导航</strong><button className="icon-button" aria-label="关闭导航" onClick={() => setMobileOpen(false)} type="button"><X /></button></div>
            <PrimaryLinks onNavigate={() => setMobileOpen(false)} />
          </nav>
        </div>
      ) : null}

      <aside className="topic-rail" aria-label="研究主题">
        <div className="rail-heading">
          <span>研究主题</span>
          <NavLink className="new-topic" to="/topics" aria-label="新建主题">+</NavLink>
        </div>
        {topics.isPending ? <p className="rail-empty">读取中...</p> : null}
        {topics.isError ? <p className="rail-empty">无法读取主题</p> : null}
        {topics.data?.topics.length === 0 ? <p className="rail-empty">从一个研究问题开始</p> : null}
        <nav className="topic-list">
          {topics.data?.topics.map((topic) => (
            <NavLink className={({ isActive }) => isActive ? "topic-link active" : "topic-link"} key={topic.topic_id} to={`/topics/${topic.topic_id}`}>
              <span>{topic.title}</span>
              <small>{new Date(topic.updated_at).toLocaleDateString("zh-CN", { month: "short", day: "numeric" })}</small>
            </NavLink>
          ))}
        </nav>
        <div className="rail-footer"><span className="monospace">V2.0</span><span>可信研究运行时</span></div>
      </aside>

      <main className="route-canvas"><Outlet /></main>
    </div>
  );
}
