from __future__ import annotations

import unittest

from feedback_agent.nlp import classify_category, classify_priority, classify_sentiment


class NlpRulesTest(unittest.TestCase):
    def test_platform_tool_feedback_is_classified(self) -> None:
        category, reason = classify_category("Python 代码报错，飞书表格模板也需要补充。")

        self.assertEqual(category, "平台工具与数据")
        self.assertIn("命中关键词", reason)

    def test_negative_and_high_priority(self) -> None:
        text = "考试截止前系统崩溃，导致作业无法提交。"

        self.assertEqual(classify_sentiment(text), "负向")
        self.assertEqual(classify_priority(text, "负向"), "高")


if __name__ == "__main__":
    unittest.main()

