"""Feishu custom bot webhook integration.

The implementation is inspired by nanobot's Feishu channel design: keep message
formatting separate from transport, sign requests when a secret is configured,
and retry transient delivery failures.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .models import AnalysisResult


@dataclass(slots=True)
class FeishuSendResult:
    ok: bool
    status: int | None
    message: str
    response: dict[str, Any] | None = None


class FeishuWebhookClient:
    """Send result summaries to a Feishu custom bot webhook."""

    def __init__(
        self,
        webhook_url: str | None = None,
        secret: str | None = None,
        timeout: float = 10.0,
        max_retries: int = 3,
    ) -> None:
        self.webhook_url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL", "")
        self.secret = secret if secret is not None else os.getenv("FEISHU_WEBHOOK_SECRET", "")
        self.timeout = timeout
        self.max_retries = max(1, max_retries)

    def send_result(self, result: AnalysisResult) -> FeishuSendResult:
        if not self.webhook_url:
            return FeishuSendResult(False, None, "缺少 FEISHU_WEBHOOK_URL。")
        return self._post(self._build_card_payload(result))

    def send_text(self, text: str) -> FeishuSendResult:
        if not self.webhook_url:
            return FeishuSendResult(False, None, "缺少 FEISHU_WEBHOOK_URL。")
        payload = {"msg_type": "text", "content": {"text": text}}
        self._attach_signature(payload)
        return self._post(payload)

    def _build_card_payload(self, result: AnalysisResult) -> dict[str, Any]:
        top_keywords = "、".join(keyword for keyword, _count in result.top_keywords[:6]) or "暂无"
        top_categories = sorted(
            result.category_counts.items(), key=lambda pair: pair[1], reverse=True
        )[:4]
        category_text = "\n".join(f"- {category}: {count} 条" for category, count in top_categories)
        actions = "\n".join(
            f"{index}. {action}" for index, action in enumerate(result.recommendations[:4], start=1)
        )
        payload: dict[str, Any] = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": "blue",
                    "title": {"tag": "plain_text", "content": "数字经济课程反馈分析"},
                },
                "elements": [
                    {
                        "tag": "div",
                        "fields": [
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**反馈总数**\n{result.total}",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**高优先级**\n{result.priority_counts.get('高', 0)}",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**负向反馈**\n{result.sentiment_counts.get('负向', 0)}",
                                },
                            },
                            {
                                "is_short": True,
                                "text": {
                                    "tag": "lark_md",
                                    "content": f"**生成时间**\n{result.generated_at}",
                                },
                            },
                        ],
                    },
                    {"tag": "hr"},
                    {
                        "tag": "markdown",
                        "content": f"**总体结论**\n{_truncate(result.summary, 700)}",
                    },
                    {"tag": "markdown", "content": f"**主题分布**\n{category_text or '暂无'}"},
                    {"tag": "markdown", "content": f"**高频关键词**\n{top_keywords}"},
                    {"tag": "markdown", "content": f"**建议动作**\n{actions}"},
                ],
            },
        }
        self._attach_signature(payload)
        return payload

    def _attach_signature(self, payload: dict[str, Any]) -> None:
        if not self.secret:
            return
        timestamp = str(int(time.time()))
        payload["timestamp"] = timestamp
        payload["sign"] = self._sign(timestamp)

    def _sign(self, timestamp: str) -> str:
        string_to_sign = f"{timestamp}\n{self.secret}"
        digest = hmac.new(string_to_sign.encode("utf-8"), b"", digestmod=hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")

    def _post(self, payload: dict[str, Any]) -> FeishuSendResult:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        last_error = ""
        for attempt in range(1, self.max_retries + 1):
            request = urllib.request.Request(
                self.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read().decode("utf-8")
                    parsed = json.loads(raw) if raw else {}
                    if response.status < 300 and parsed.get("code", 0) == 0:
                        return FeishuSendResult(True, response.status, "飞书推送成功。", parsed)
                    last_error = parsed.get("msg") or raw
                    status = response.status
            except urllib.error.HTTPError as exc:
                status = exc.code
                last_error = exc.read().decode("utf-8", errors="replace")
            except (urllib.error.URLError, TimeoutError) as exc:
                status = None
                last_error = str(exc)

            if attempt < self.max_retries:
                time.sleep(min(2 ** (attempt - 1), 4))

        return FeishuSendResult(False, status, f"飞书推送失败：{last_error}")


def _truncate(text: str, limit: int) -> str:
    clean = text.strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."

