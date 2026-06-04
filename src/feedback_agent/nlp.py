"""Deterministic classification and summarization helpers.

The project can optionally call a large model for narrative polishing, but the
core workflow remains deterministic so the assignment can be tested offline.
"""

from __future__ import annotations

import re
from collections import Counter

from .models import CATEGORIES


CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "课程内容与知识点": (
        "数字经济",
        "平台经济",
        "数据要素",
        "算法",
        "区块链",
        "人工智能",
        "模型",
        "知识点",
        "理论",
        "案例",
        "产业",
    ),
    "学习节奏与难度": (
        "听不懂",
        "太快",
        "太难",
        "节奏",
        "进度",
        "复习",
        "预习",
        "基础",
        "时间",
        "压力",
    ),
    "作业考试与评价": (
        "作业",
        "考试",
        "测验",
        "评分",
        "考核",
        "论文",
        "小组",
        "展示",
        "rubric",
        "截止",
    ),
    "平台工具与数据": (
        "飞书",
        "表格",
        "系统",
        "平台",
        "数据",
        "爬虫",
        "代码",
        "python",
        "api",
        "可视化",
        "报错",
    ),
    "资料资源与实践支持": (
        "资料",
        "课件",
        "阅读",
        "文献",
        "教材",
        "案例库",
        "数据集",
        "实训",
        "模板",
        "链接",
    ),
    "论文科研与就业": (
        "论文",
        "选题",
        "开题",
        "实习",
        "就业",
        "简历",
        "研究",
        "竞赛",
        "职业",
        "企业",
    ),
    "校园服务与协同": (
        "教务",
        "预约",
        "通知",
        "报名",
        "社团",
        "办公室",
        "流程",
        "审批",
        "协同",
        "消息",
    ),
}

POSITIVE_WORDS = (
    "清晰",
    "有用",
    "喜欢",
    "满意",
    "及时",
    "方便",
    "高效",
    "提升",
    "帮助",
    "不错",
    "好",
)

NEGATIVE_WORDS = (
    "不懂",
    "听不懂",
    "困难",
    "太难",
    "太快",
    "混乱",
    "缺少",
    "不足",
    "报错",
    "崩溃",
    "无法",
    "不能",
    "卡",
    "慢",
    "焦虑",
    "压力",
    "不清楚",
    "来不及",
)

HIGH_PRIORITY_WORDS = (
    "紧急",
    "无法",
    "不能",
    "影响",
    "严重",
    "崩溃",
    "截止",
    "考试",
    "挂科",
    "全班",
)

ACTION_TEMPLATES = {
    "课程内容与知识点": "补充数字经济概念图谱、真实企业案例和课堂小结，帮助学生建立知识框架。",
    "学习节奏与难度": "按章节设置预习清单和课后 10 分钟复盘题，对高频难点安排答疑。",
    "作业考试与评价": "公开评分标准、样例答案和截止提醒，降低学生对考核要求的不确定感。",
    "平台工具与数据": "整理工具安装说明、常见报错 FAQ 和数据处理脚本模板。",
    "资料资源与实践支持": "建立飞书资料库，按主题归档课件、文献、数据集和案例链接。",
    "论文科研与就业": "提供选题库、文献阅读模板、实习方向清单和研究方法建议。",
    "校园服务与协同": "把流程步骤、材料清单和责任人汇总到飞书文档，并通过机器人提醒。",
    "其他": "将反馈转交课程负责人人工复核，必要时补充访谈确认真实需求。",
}


def classify_category(text: str) -> tuple[str, str]:
    """Classify feedback by keyword overlap and return category plus reason."""
    normalized = text.lower()
    scores: Counter[str] = Counter()
    matched: dict[str, list[str]] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in normalized:
                scores[category] += 1
                matched.setdefault(category, []).append(keyword)

    if not scores:
        return "其他", "未命中明确关键词，归入其他并建议人工复核。"

    category, score = scores.most_common(1)[0]
    reason = "命中关键词：" + "、".join(matched.get(category, [])[:4])
    if score == 1:
        reason += "。置信度中等。"
    return category, reason


def classify_sentiment(text: str) -> str:
    positive = sum(1 for word in POSITIVE_WORDS if word in text)
    negative = sum(1 for word in NEGATIVE_WORDS if word in text)
    if negative > positive:
        return "负向"
    if positive > negative:
        return "正向"
    return "中性"


def classify_priority(text: str, sentiment: str) -> str:
    high_hits = sum(1 for word in HIGH_PRIORITY_WORDS if word in text)
    negative_hits = sum(1 for word in NEGATIVE_WORDS if word in text)
    if high_hits >= 1 or negative_hits >= 3:
        return "高"
    if sentiment == "负向" or negative_hits >= 1:
        return "中"
    return "低"


def extract_keywords(text: str, limit: int = 5) -> list[str]:
    """Extract explainable keywords without external NLP dependencies."""
    hits: list[str] = []
    for keywords in CATEGORY_KEYWORDS.values():
        for keyword in keywords:
            if keyword.lower() in text.lower() and keyword not in hits:
                hits.append(keyword)

    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_+-]{2,}|[\u4e00-\u9fff]{2,4}", text)
    stopwords = {"我们", "老师", "课程", "希望", "感觉", "一个", "可以", "需要", "同学"}
    for token, _count in Counter(tokens).most_common():
        if token not in stopwords and token not in hits:
            hits.append(token)
        if len(hits) >= limit:
            break
    return hits[:limit]


def action_for_category(category: str) -> str:
    return ACTION_TEMPLATES.get(category, ACTION_TEMPLATES["其他"])


def validate_category(category: str) -> str:
    return category if category in CATEGORIES else "其他"
