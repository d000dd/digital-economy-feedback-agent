"""Shared data models for the feedback agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


CATEGORIES: tuple[str, ...] = (
    "课程内容与知识点",
    "学习节奏与难度",
    "作业考试与评价",
    "平台工具与数据",
    "资料资源与实践支持",
    "论文科研与就业",
    "校园服务与协同",
    "其他",
)

SENTIMENTS: tuple[str, ...] = ("正向", "中性", "负向")
PRIORITIES: tuple[str, ...] = ("低", "中", "高")


@dataclass(slots=True)
class FeedbackItem:
    """A single raw feedback record."""

    id: str
    text: str
    source: str = "manual"
    group: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ClassifiedFeedback:
    """Feedback plus agent-generated labels."""

    item: FeedbackItem
    category: str
    sentiment: str
    priority: str
    keywords: list[str] = field(default_factory=list)
    reason: str = ""
    action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AnalysisResult:
    """End-to-end analysis result for reports, UI, and Feishu push."""

    generated_at: str
    total: int
    category_counts: dict[str, int]
    sentiment_counts: dict[str, int]
    priority_counts: dict[str, int]
    top_keywords: list[tuple[str, int]]
    summary: str
    recommendations: list[str]
    items: list[ClassifiedFeedback]
    report_markdown: str
    feishu_message: str
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def empty(cls, warnings: list[str] | None = None) -> "AnalysisResult":
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return cls(
            generated_at=generated_at,
            total=0,
            category_counts={},
            sentiment_counts={},
            priority_counts={},
            top_keywords=[],
            summary="没有可分析的有效反馈。",
            recommendations=["补充课程反馈文本或上传包含反馈内容的 CSV 文件。"],
            items=[],
            report_markdown="# 课程反馈分析报告\n\n没有可分析的有效反馈。\n",
            feishu_message="课程反馈分析未生成结果：没有可分析的有效反馈。",
            warnings=warnings or [],
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["top_keywords"] = [
            {"keyword": keyword, "count": count} for keyword, count in self.top_keywords
        ]
        return data

