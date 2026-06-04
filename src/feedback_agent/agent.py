"""Main intelligent-agent workflow."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from .llm import OptionalLLM
from .models import AnalysisResult, ClassifiedFeedback, FeedbackItem
from .nlp import (
    action_for_category,
    classify_category,
    classify_priority,
    classify_sentiment,
    extract_keywords,
    validate_category,
)


class FeedbackAgent:
    """Analyze course/campus feedback and generate action-oriented reports."""

    def __init__(self, llm: OptionalLLM | None = None) -> None:
        self.llm = llm or OptionalLLM()

    def analyze(self, items: list[FeedbackItem]) -> AnalysisResult:
        valid_items = [item for item in items if item.text.strip()]
        warnings: list[str] = []
        if len(valid_items) != len(items):
            warnings.append("已忽略空白反馈。")
        if not valid_items:
            return AnalysisResult.empty(warnings)

        classified = [self._classify_item(item) for item in valid_items]
        category_counts = Counter(row.category for row in classified)
        sentiment_counts = Counter(row.sentiment for row in classified)
        priority_counts = Counter(row.priority for row in classified)
        keyword_counts = Counter(keyword for row in classified for keyword in row.keywords)

        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        recommendations = self._build_recommendations(classified, category_counts)
        summary = self._build_summary(
            total=len(classified),
            category_counts=category_counts,
            sentiment_counts=sentiment_counts,
            priority_counts=priority_counts,
            top_keywords=keyword_counts.most_common(5),
        )
        polished = self._polish_with_llm(summary, recommendations)
        if polished:
            summary = polished
        elif self.llm.enabled and self.llm.last_error:
            warnings.append("真实 AI 调用失败，已自动回退到离线规则摘要。")

        result = AnalysisResult(
            generated_at=generated_at,
            total=len(classified),
            category_counts=dict(category_counts),
            sentiment_counts=dict(sentiment_counts),
            priority_counts=dict(priority_counts),
            top_keywords=keyword_counts.most_common(8),
            summary=summary,
            recommendations=recommendations,
            items=classified,
            report_markdown="",
            feishu_message="",
            warnings=warnings,
        )
        result.report_markdown = self._build_markdown_report(result)
        result.feishu_message = self._build_feishu_message(result)
        return result

    def _classify_item(self, item: FeedbackItem) -> ClassifiedFeedback:
        category, reason = classify_category(item.text)
        category = validate_category(category)
        sentiment = classify_sentiment(item.text)
        priority = classify_priority(item.text, sentiment)
        keywords = extract_keywords(item.text)
        return ClassifiedFeedback(
            item=item,
            category=category,
            sentiment=sentiment,
            priority=priority,
            keywords=keywords,
            reason=reason,
            action=action_for_category(category),
        )

    def _build_summary(
        self,
        total: int,
        category_counts: Counter[str],
        sentiment_counts: Counter[str],
        priority_counts: Counter[str],
        top_keywords: list[tuple[str, int]],
    ) -> str:
        top_category, top_category_count = category_counts.most_common(1)[0]
        negative = sentiment_counts.get("负向", 0)
        high = priority_counts.get("高", 0)
        keyword_text = "、".join(keyword for keyword, _ in top_keywords[:5]) or "暂无"
        return (
            f"本次共分析 {total} 条反馈，最集中的主题是“{top_category}”"
            f"（{top_category_count} 条）。负向反馈 {negative} 条，高优先级事项 {high} 条。"
            f"高频关键词包括：{keyword_text}。建议优先处理高优先级负向反馈，并把处理进度同步到飞书。"
        )

    def _build_recommendations(
        self, items: list[ClassifiedFeedback], category_counts: Counter[str]
    ) -> list[str]:
        recommendations: list[str] = []
        for category, _count in category_counts.most_common():
            related = [row for row in items if row.category == category]
            high_or_negative = [
                row for row in related if row.priority == "高" or row.sentiment == "负向"
            ]
            if not high_or_negative and len(recommendations) >= 3:
                continue
            recommendations.append(action_for_category(category))
            if len(recommendations) >= 5:
                break
        return recommendations or ["继续收集反馈，形成每周固定复盘机制。"]

    def _polish_with_llm(self, summary: str, recommendations: list[str]) -> str | None:
        system = "你是高校数字经济课程助教。只输出一段正式、简洁、可执行的中文摘要。"
        user = (
            f"规则引擎摘要：{summary}\n"
            f"候选行动建议：{recommendations}\n"
            "要求：不超过180字；保留关键数量；不要编造输入中没有的信息。"
        )
        return self.llm.complete(system, user)

    def _build_markdown_report(self, result: AnalysisResult) -> str:
        lines = [
            "# 数字经济课程反馈分析报告",
            "",
            f"- 生成时间：{result.generated_at}",
            f"- 反馈总数：{result.total}",
            f"- 负向反馈：{result.sentiment_counts.get('负向', 0)}",
            f"- 高优先级事项：{result.priority_counts.get('高', 0)}",
            "",
            "## 一、总体结论",
            "",
            result.summary,
            "",
            "## 二、主题分布",
            "",
            "| 主题 | 数量 |",
            "| --- | ---: |",
        ]
        for category, count in sorted(
            result.category_counts.items(), key=lambda pair: pair[1], reverse=True
        ):
            lines.append(f"| {category} | {count} |")

        lines.extend(
            [
                "",
                "## 三、改进建议",
                "",
            ]
        )
        for index, recommendation in enumerate(result.recommendations, start=1):
            lines.append(f"{index}. {recommendation}")

        lines.extend(
            [
                "",
                "## 四、明细表",
                "",
                "| ID | 反馈内容 | 分类 | 情绪 | 优先级 | 关键词 | 建议动作 |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in result.items:
            text = row.item.text.replace("|", "/").replace("\n", " ")
            lines.append(
                "| {id} | {text} | {category} | {sentiment} | {priority} | {keywords} | {action} |".format(
                    id=row.item.id,
                    text=text[:120],
                    category=row.category,
                    sentiment=row.sentiment,
                    priority=row.priority,
                    keywords="、".join(row.keywords),
                    action=row.action,
                )
            )

        if result.warnings:
            lines.extend(["", "## 五、异常情况", ""])
            lines.extend(f"- {warning}" for warning in result.warnings)

        return "\n".join(lines) + "\n"

    def _build_feishu_message(self, result: AnalysisResult) -> str:
        top_categories = "、".join(
            f"{category}{count}条"
            for category, count in sorted(
                result.category_counts.items(), key=lambda pair: pair[1], reverse=True
            )[:3]
        )
        actions = "\n".join(f"{idx}. {item}" for idx, item in enumerate(result.recommendations[:3], 1))
        return (
            f"数字经济课程反馈分析完成\n"
            f"反馈总数：{result.total}\n"
            f"主要主题：{top_categories or '暂无'}\n"
            f"负向反馈：{result.sentiment_counts.get('负向', 0)}，"
            f"高优先级：{result.priority_counts.get('高', 0)}\n\n"
            f"飞书同步建议：把以下动作分配给课程团队并跟踪状态。\n{actions}"
        )
