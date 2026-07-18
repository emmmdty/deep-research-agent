import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BrainCircuit, Clock3, ShieldCheck, Trash2 } from "lucide-react";

import { productApi } from "../../api/client";
import { AsyncState } from "../../components/AsyncState";

const scopeLabels: Record<string, string> = {
  user_preference: "用户偏好",
  long_term: "长期记忆",
  project: "项目记忆",
  temporary: "临时记忆",
  session: "会话记忆",
};

export function MemoryPage() {
  const queryClient = useQueryClient();
  const memories = useQuery({ queryKey: ["memory"], queryFn: () => productApi.listMemory() });
  const remove = useMutation({
    mutationFn: (memoryId: string) => productApi.deleteMemory(memoryId),
    onMutate: async (memoryId) => {
      await queryClient.cancelQueries({ queryKey: ["memory"] });
      queryClient.setQueryData<{ memories: import("../../types").MemoryRecord[] }>(["memory"], (current) => ({ memories: current?.memories.filter((item) => item.memory_id !== memoryId) ?? [] }));
    },
    onError: () => queryClient.invalidateQueries({ queryKey: ["memory"] }),
  });

  function deleteMemory(memoryId: string) {
    if (window.confirm("删除这条记忆？该操作不会影响已经冻结的研究快照。")) remove.mutate(memoryId);
  }

  return (
    <section className="page-layout">
      <header className="page-header"><div><span className="section-label">个人研究上下文</span><h1>记忆治理</h1><p>查看系统保留的偏好与长期上下文，并主动清理失效信息。</p></div><BrainCircuit size={34} /></header>
      <AsyncState loading={memories.isPending} error={memories.error}>
        <div className="memory-list">
          {memories.data?.memories.length ? memories.data.memories.map((memory) => (
            <article className="memory-row" key={memory.memory_id}>
              <div className="memory-scope"><ShieldCheck size={16} /><span>{scopeLabels[memory.scope] ?? memory.scope}</span></div>
              <div className="memory-content"><p>{memory.content}</p><small><Clock3 size={12} />更新于 {new Date(memory.updated_at).toLocaleString("zh-CN")} · 置信度 {Math.round(memory.confidence * 100)}%</small></div>
              <button className="icon-button danger" aria-label="删除记忆" onClick={() => deleteMemory(memory.memory_id)} type="button"><Trash2 size={17} /></button>
            </article>
          )) : <div className="view-empty">当前没有可用记忆。偏好只有在确认后才会进入长期存储。</div>}
        </div>
      </AsyncState>
    </section>
  );
}
