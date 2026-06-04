from __future__ import annotations

import base64
import hashlib
import hmac
import unittest

from feedback_agent.agent import FeedbackAgent
from feedback_agent.data_loader import parse_text
from feedback_agent.feishu import FeishuWebhookClient


class FeishuWebhookClientTest(unittest.TestCase):
    def test_sign_matches_feishu_custom_bot_algorithm(self) -> None:
        client = FeishuWebhookClient("https://example.invalid", "secret")
        expected = base64.b64encode(
            hmac.new("1700000000\nsecret".encode("utf-8"), b"", hashlib.sha256).digest()
        ).decode("utf-8")

        self.assertEqual(client._sign("1700000000"), expected)

    def test_build_card_payload_contains_core_fields(self) -> None:
        result = FeedbackAgent().analyze(parse_text("考试范围不清楚，复习压力大。"))
        payload = FeishuWebhookClient("https://example.invalid")._build_card_payload(result)

        self.assertEqual(payload["msg_type"], "interactive")
        self.assertEqual(payload["card"]["header"]["title"]["content"], "数字经济课程反馈分析")
        self.assertIn("elements", payload["card"])

    def test_missing_webhook_returns_clean_error(self) -> None:
        result = FeedbackAgent().analyze(parse_text("课程案例有用。"))
        send_result = FeishuWebhookClient(webhook_url="").send_result(result)

        self.assertFalse(send_result.ok)
        self.assertIn("FEISHU_WEBHOOK_URL", send_result.message)


if __name__ == "__main__":
    unittest.main()

