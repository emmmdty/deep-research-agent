import { useQuery } from "@tanstack/react-query";
import { CircleCheck, CircleOff, KeyRound, ServerCog } from "lucide-react";
import { Link } from "react-router-dom";

import { productApi } from "../../api/client";
import { AsyncState } from "../../components/AsyncState";

export function AdminModelsPage() {
  const models = useQuery({ queryKey: ["admin", "models"], queryFn: () => productApi.listModels() });
  return (
    <section className="page-layout admin-page">
      <header className="page-header"><div><span className="section-label">管理控制台</span><h1>模型端点</h1><p>只展示可验证的运行配置；密钥值不会返回浏览器。</p></div><ServerCog size={34} /></header>
      <nav className="admin-tabs"><Link className="active" to="/admin/models">模型</Link><Link to="/admin/runtime">运行时</Link></nav>
      <AsyncState loading={models.isPending} error={models.error}>
        <div className="admin-table" role="table" aria-label="模型端点">
          <div className="admin-row admin-head" role="row"><span>端点</span><span>模型</span><span>地址</span><span>密钥</span><span>状态</span></div>
          {models.data?.models.map((model) => (
            <div className="admin-row" role="row" key={model.endpoint_id}>
              <strong>{model.endpoint_id}</strong><span>{model.model}</span><code>{model.base_url}</code><span className="redacted"><KeyRound size={13} />{model.api_key}</span><span>{model.enabled ? <><CircleCheck className="supported" />启用</> : <><CircleOff />停用</>}</span>
            </div>
          ))}
        </div>
      </AsyncState>
    </section>
  );
}
