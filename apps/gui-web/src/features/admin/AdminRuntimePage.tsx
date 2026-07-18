import { useQuery } from "@tanstack/react-query";
import { Activity, CheckCircle2 } from "lucide-react";
import { Link } from "react-router-dom";

import { productApi } from "../../api/client";
import { AsyncState } from "../../components/AsyncState";

export function AdminRuntimePage() {
  const configs = useQuery({ queryKey: ["admin", "runtime"], queryFn: () => productApi.listRuntimeConfigs() });
  return (
    <section className="page-layout admin-page">
      <header className="page-header"><div><span className="section-label">管理控制台</span><h1>运行时配置</h1><p>版本化配置在研究启动时冻结，之后的变更不会污染已运行任务。</p></div><Activity size={34} /></header>
      <nav className="admin-tabs"><Link to="/admin/models">模型</Link><Link className="active" to="/admin/runtime">运行时</Link></nav>
      <AsyncState loading={configs.isPending} error={configs.error}>
        <div className="config-list">{configs.data?.configs.map((config) => <article key={config.version_id}><div><code>{config.version_id}</code>{config.active ? <span className="active-config"><CheckCircle2 size={13} />当前生效</span> : null}</div><dl>{Object.entries(config.config).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{typeof value === "object" ? JSON.stringify(value) : String(value)}</dd></div>)}</dl></article>)}</div>
      </AsyncState>
    </section>
  );
}
