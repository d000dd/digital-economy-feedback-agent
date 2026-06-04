from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from feedback_agent.agent import FeedbackAgent
from feedback_agent.data_loader import parse_csv_text, parse_text


class FeedbackAgentTest(unittest.TestCase):
    def test_analyze_groups_feedback_and_builds_report(self) -> None:
        items = parse_text(
            "\n".join(
                [
                    "Python 作业报错，平台工具说明不够清楚。",
                    "考试范围希望提前公布，复习压力比较大。",
                    "数字经济案例很有用。",
                ]
            )
        )

        result = FeedbackAgent().analyze(items)

        self.assertEqual(result.total, 3)
        self.assertGreaterEqual(result.sentiment_counts.get("负向", 0), 1)
        self.assertIn("数字经济课程反馈分析报告", result.report_markdown)
        self.assertTrue(result.recommendations)
        self.assertIn("飞书", result.feishu_message)

    def test_empty_input_returns_warning_result(self) -> None:
        result = FeedbackAgent().analyze(parse_text("   \n"))

        self.assertEqual(result.total, 0)
        self.assertIn("没有可分析", result.summary)

    def test_parse_csv_uses_chinese_feedback_field(self) -> None:
        rows = parse_csv_text("编号,反馈,班级\n1,飞书表格很好用,二班\n")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].text, "飞书表格很好用")
        self.assertEqual(rows[0].group, "二班")

    def test_live_ai_failure_falls_back_to_rules(self) -> None:
        llm = MagicMock()
        llm.enabled = True
        llm.last_error = "timeout"
        llm.complete.return_value = None

        result = FeedbackAgent(llm=llm).analyze(parse_text("Python 作业报错。"))

        self.assertIn("规则", result.warnings[0])
        self.assertIn("本次共分析", result.summary)


if __name__ == "__main__":
    unittest.main()
