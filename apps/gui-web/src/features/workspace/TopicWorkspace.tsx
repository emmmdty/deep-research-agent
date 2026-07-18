import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUp, Clock3, FileText, RefreshCw, Sparkles } from "lucide-react";
import { FormEvent, useState } from "react";
import { Link, Outlet, useParams } from "react-router-dom";

import { productApi } from "../../api/client";
import { AsyncState } from "../../components/AsyncState";
import type { MessageDecision } from "../../types";

export function TopicWorkspace() {
  const { topicId = "" } = useParams();
  const queryClient = useQueryClient();
  const [prompt, setPrompt] = useState("");
  const [refresh, setRefresh] = useState(false);
  const [decision, setDecision] = useState<MessageDecision | null>(null);
  const [briefQuestion, setBriefQuestion] = useState("");
  const topic = useQuery({ queryKey: ["topic", topicId], queryFn: () => productApi.getTopic(topicId), enabled: Boolean(topicId) });
  const runs = useQuery({ queryKey: ["runs", topicId], queryFn: () => productApi.listRuns(topicId), enabled: Boolean(topicId) });

  const send = useMutation({
    mutationFn: async () => {
      if (!topic.data?.conversation_id) throw new Error("当前主题没有可用对话");
      return productApi.sendMessage(topic.data.conversation_id, prompt.trim(), refresh);
    },
    onSuccess: (next) => {
      setDecision(next);
      setBriefQuestion(next.brief.question);
      if (next.run_id) void queryClient.invalidateQueries({ queryKey: ["runs", topicId] });
    },
  });
  const startFromBrief = useMutation({
    mutationFn: () => productApi.createRun(topicId, briefQuestion, topic.data?.conversation_id),
    onSuccess: async () => {
      setDecision((current) => current ? { ...current, response_type: "research_job_started" } : current);
      await queryClient.invalidateQueries({ queryKey: ["runs", topicId] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (prompt.trim()) send.mutate();
  }

  return (
    <AsyncState loading={topic.isPending} error={topic.error}>
      <div className="workspace-shell">
        <aside className="activity-column" aria-label="对话与活动">
          <header className="activity-header">
            <span className="section-label">当前主题</span>
            <h1>{topic.data?.title}</h1>
            <p>{runs.data?.runs.length ?? 0} 次研究运行</p>
          </header>

          <div className="activity-feed">
            {runs.data?.runs.length ? runs.data.runs.map((item) => (
              <Link className="activity-item" key={item.run_id} to={`/topics/${topicId}/runs/${item.run_id}`}>
                <span className={`run-dot ${item.status}`} />
                <span><strong>{item.question}</strong><small><Clock3 size={12} /> {item.status} · {new Date(item.updated_at).toLocaleString("zh-CN")}</small></span>
              </Link>
            )) : <div className="empty-activity"><Sparkles /><strong>还没有研究运行</strong><p>输入问题后，系统会先判断是否需要补充范围。</p></div>}

            {decision?.response_type === "clarification_required" ? (
              <section className="clarification-panel">
                <span className="section-label">需要确认</span>
                <h2>完善研究简报</h2>
                <ul>{decision.clarification_questions.map((question) => <li key={question}>{question}</li>)}</ul>
                <label htmlFor="brief-question">研究问题简报</label>
                <textarea id="brief-question" onChange={(event) => setBriefQuestion(event.target.value)} value={briefQuestion} />
                <button className="primary-button" disabled={!briefQuestion.trim() || startFromBrief.isPending} onClick={() => startFromBrief.mutate()} type="button">开始研究 <ArrowUp size={16} /></button>
              </section>
            ) : null}
            {decision?.response_type === "direct_answer" ? <div className="assistant-answer">{decision.answer}</div> : null}
            {decision?.response_type === "research_job_started" ? <div className="started-notice"><FileText size={17} />研究任务已启动</div> : null}
          </div>

          <form className="composer" onSubmit={submit}>
            <label htmlFor="research-question">研究问题</label>
            <textarea id="research-question" onChange={(event) => setPrompt(event.target.value)} placeholder="询问进展、比较方法或发起新研究..." value={prompt} />
            <div className="composer-actions">
              <label className="refresh-toggle"><input checked={refresh} onChange={(event) => setRefresh(event.target.checked)} type="checkbox" /> <RefreshCw size={14} />刷新资料快照</label>
              <button className="send-button" disabled={!prompt.trim() || send.isPending} type="submit" aria-label="发送"><ArrowUp size={18} /></button>
            </div>
            {send.isError ? <p className="form-error" role="alert">{send.error.message}</p> : null}
          </form>
        </aside>
        <section className="workspace-content"><Outlet context={{ topic: topic.data }} /></section>
      </div>
    </AsyncState>
  );
}

export function TopicOverview() {
  return <div className="topic-overview"><FileText size={24} /><h2>选择一次研究运行</h2><p>报告、来源、论断审计与关系图会在这里保持同步。</p></div>;
}
