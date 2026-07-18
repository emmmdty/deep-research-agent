import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, BookOpen, Database, GitBranch } from "lucide-react";
import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { productApi } from "../../api/client";

export function TopicsIndex() {
  const [title, setTitle] = useState("");
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const createTopic = useMutation({
    mutationFn: () => productApi.createTopic(title),
    onSuccess: async (topic) => {
      await queryClient.invalidateQueries({ queryKey: ["topics"] });
      navigate(`/topics/${topic.topic_id}`);
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (title.trim()) createTopic.mutate();
  }

  return (
    <section className="welcome-canvas">
      <div className="welcome-copy">
        <span className="section-label">新研究</span>
        <h1>从问题开始，<br />沿证据推进。</h1>
        <p>建立一个持续更新的科研主题。Agent 集群会拆解任务、冻结语料快照并交叉审查关键论断。</p>
        <form className="topic-creator" onSubmit={submit}>
          <label htmlFor="topic-title">研究主题</label>
          <div className="creator-row">
            <input id="topic-title" onChange={(event) => setTitle(event.target.value)} placeholder="例如：事件图谱、Agent 与 LLM 如何相互促进？" value={title} />
            <button className="primary-button" disabled={!title.trim() || createTopic.isPending} type="submit">创建 <ArrowRight aria-hidden="true" size={17} /></button>
          </div>
          {createTopic.isError ? <p className="form-error" role="alert">{createTopic.error.message}</p> : null}
        </form>
      </div>
      <div className="method-strip" aria-label="研究方法">
        <span><BookOpen />稳定论文源</span><span><GitBranch />并行 Agent</span><span><Database />冻结证据快照</span>
      </div>
    </section>
  );
}
