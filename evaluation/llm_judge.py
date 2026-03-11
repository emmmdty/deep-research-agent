"""LLM-as-Judge 评分器——使用 LLM 对研究报告进行多维度评分。"""

from __future__ import annotations

import json

from loguru import logger


# LLM 评分提示词模板
JUDGE_SYSTEM_PROMPT = """\
你是一名研究报告质量评审专家。你需要对给定的研究报告进行严格、客观的多维度质量评分。
评分必须基于报告的实际内容，不可因主题偏好而带有倾向性。
"""

JUDGE_USER_PROMPT = """\
请对以下研究报告进行评分（每项 1-10 分）。

评分维度：
1. **内容深度 (depth)**：分析是否深入，有无具体案例和数据支撑
2. **事实准确度 (accuracy)**：信息是否可信，有无明显错误或幻觉
3. **逻辑连贯性 (coherence)**：段落之间是否有逻辑关系，论述是否流畅
4. **引用质量 (citation_quality)**：引用来源是否丰富、可靠且标注规范
5. **结构完整性 (structure)**：是否包含概述、多维度分析、总结和参考来源

---

研究主题：{topic}

报告内容：
{report}

---

请以 JSON 格式输出评分结果，只输出 JSON，不要包含其他文本：
{{
  "depth": 分数,
  "accuracy": 分数,
  "coherence": 分数,
  "citation_quality": 分数,
  "structure": 分数,
  "overall": 综合分数（5个维度的加权平均，depth和accuracy权重各25%，其余各约17%）,
  "comments": "用1-2句话说明评价理由"
}}
"""

PAIRWISE_USER_PROMPT = """\
请对以下两份研究报告做盲评。不要因为报告标签顺序产生偏见。

评分维度：
1. depth
2. accuracy
3. coherence
4. citation_quality
5. structure

研究主题：{topic}

报告 X：
{report_x}

---

报告 Y：
{report_y}

请以 JSON 输出，只输出 JSON：
{{
  "report_x": {{
    "depth": 分数,
    "accuracy": 分数,
    "coherence": 分数,
    "citation_quality": 分数,
    "structure": 分数,
    "overall": 综合分数,
    "comments": "1 句评价"
  }},
  "report_y": {{
    "depth": 分数,
    "accuracy": 分数,
    "coherence": 分数,
    "citation_quality": 分数,
    "structure": 分数,
    "overall": 综合分数,
    "comments": "1 句评价"
  }},
  "winner": "X / Y / tie",
  "reason": "1-2 句总结胜负原因"
}}
"""


class LLMJudge:
    """使用 LLM 对研究报告进行质量评分。"""

    def __init__(self, llm=None) -> None:
        self._llm = llm

    @property
    def llm(self):
        """懒加载 LLM 实例。"""
        if self._llm is None:
            from llm.provider import get_llm
            self._llm = get_llm()
        return self._llm

    def score_report(self, report: str, topic: str = "") -> dict:
        """对研究报告进行多维度评分。

        Args:
            report: 研究报告 Markdown 文本。
            topic: 研究主题（可选，用于上下文参考）。

        Returns:
            评分结果字典，包含各维度分数和综合评语。
        """
        if not report or len(report.strip()) < 100:
            return self._empty_scores("报告内容过短，无法评分")

        user_prompt = JUDGE_USER_PROMPT.format(
            topic=topic or "未指定",
            report=report[:8000],  # 限制长度，避免超过上下文窗口
        )

        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=JUDGE_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
            response = self.llm.invoke(messages)
            raw_text = response.content
            scores = self._parse_scores(raw_text)

            logger.info(
                "📊 LLM Judge 评分完成: overall={}, depth={}, accuracy={}",
                scores.get("overall", 0),
                scores.get("depth", 0),
                scores.get("accuracy", 0),
            )
            return scores

        except Exception as e:
            logger.error("LLM Judge 评分失败: {}", e)
            return self._empty_scores(f"评分过程出错: {e}")

    def compare_reports(
        self, report_a: str, report_b: str, topic: str = ""
    ) -> dict:
        """对比评估两份报告（A/B 盲评）。

        Args:
            report_a: 报告 A 的 Markdown 文本。
            report_b: 报告 B 的 Markdown 文本。
            topic: 研究主题。

        Returns:
            包含两份报告评分和对比结果的字典。
        """
        if not report_a or not report_b:
            scores_a = self.score_report(report_a, topic)
            scores_b = self.score_report(report_b, topic)
            winner = "A" if scores_a.get("overall", 0) > scores_b.get("overall", 0) else "B"
            if scores_a.get("overall", 0) == scores_b.get("overall", 0):
                winner = "平局"
            return {
                "topic": topic,
                "report_a": scores_a,
                "report_b": scores_b,
                "winner": winner,
                "score_diff": round(scores_a.get("overall", 0) - scores_b.get("overall", 0), 2),
            }

        # 使用中性标签 X / Y，避免把 A/B 标签直接暴露给评审模型。
        x_is_a = len(report_a) <= len(report_b)
        report_x = report_a if x_is_a else report_b
        report_y = report_b if x_is_a else report_a
        try:
            from langchain_core.messages import HumanMessage, SystemMessage

            messages = [
                SystemMessage(content=JUDGE_SYSTEM_PROMPT),
                HumanMessage(
                    content=PAIRWISE_USER_PROMPT.format(
                        topic=topic or "未指定",
                        report_x=report_x[:7000],
                        report_y=report_y[:7000],
                    )
                ),
            ]
            response = self.llm.invoke(messages)
            payload = self._parse_pairwise_scores(response.content)
            scores_x = payload.get("report_x", self._empty_scores("pairwise 评分缺失"))
            scores_y = payload.get("report_y", self._empty_scores("pairwise 评分缺失"))
            winner = payload.get("winner", "tie")
            mapped_winner = {
                "X": "A" if x_is_a else "B",
                "Y": "B" if x_is_a else "A",
                "tie": "平局",
            }.get(str(winner).strip(), "平局")

            scores_a = scores_x if x_is_a else scores_y
            scores_b = scores_y if x_is_a else scores_x
            return {
                "topic": topic,
                "report_a": scores_a,
                "report_b": scores_b,
                "winner": mapped_winner,
                "score_diff": round(scores_a.get("overall", 0) - scores_b.get("overall", 0), 2),
                "reason": payload.get("reason", ""),
            }
        except Exception as e:
            logger.error("LLM Judge 盲评失败，退回单独评分: {}", e)
            scores_a = self.score_report(report_a, topic)
            scores_b = self.score_report(report_b, topic)
            winner = "A" if scores_a.get("overall", 0) > scores_b.get("overall", 0) else "B"
            if scores_a.get("overall", 0) == scores_b.get("overall", 0):
                winner = "平局"
            return {
                "topic": topic,
                "report_a": scores_a,
                "report_b": scores_b,
                "winner": winner,
                "score_diff": round(scores_a.get("overall", 0) - scores_b.get("overall", 0), 2),
            }

    def _parse_scores(self, raw_text: str) -> dict:
        """从 LLM 响应中解析评分 JSON。"""
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start != -1 and end > start:
                try:
                    return json.loads(raw_text[start : end + 1])
                except json.JSONDecodeError:
                    pass
        return self._empty_scores("评分结果解析失败")

    def _parse_pairwise_scores(self, raw_text: str) -> dict:
        """解析 pairwise 评分结果。"""
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start != -1 and end > start:
                try:
                    return json.loads(raw_text[start : end + 1])
                except json.JSONDecodeError:
                    pass
        return {
            "report_x": self._empty_scores("pairwise 评分结果解析失败"),
            "report_y": self._empty_scores("pairwise 评分结果解析失败"),
            "winner": "tie",
            "reason": "pairwise 评分结果解析失败",
        }

    @staticmethod
    def _empty_scores(reason: str) -> dict:
        """返回空评分结果。"""
        return {
            "depth": 0,
            "accuracy": 0,
            "coherence": 0,
            "citation_quality": 0,
            "structure": 0,
            "overall": 0,
            "comments": reason,
        }
