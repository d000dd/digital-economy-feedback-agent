"""Optional OpenAI-compatible LLM helper.

This module is intentionally small and uses only the standard library. It is
enabled automatically when OPENAI_API_KEY is present. Set FEEDBACK_AGENT_USE_LLM=0
to force the deterministic offline rules.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


class OptionalLLM:
    """A minimal OpenAI-compatible chat completions client."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip(
            "/"
        )
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.timeout = float(os.getenv("OPENAI_TIMEOUT", str(timeout)))
        mode = os.getenv("FEEDBACK_AGENT_USE_LLM", "auto").strip().lower()
        self.enabled = mode not in {"0", "false", "off", "disabled"} and bool(self.api_key)
        self.last_error = ""

    def status(self) -> dict[str, str | bool]:
        """Return public, non-secret runtime status for the UI."""
        return {
            "enabled": self.enabled,
            "model": self.model if self.enabled else "",
            "base_url_configured": bool(self.base_url),
            "mode": "live-ai" if self.enabled else "rules",
        }

    def complete(self, system: str, user: str) -> str | None:
        if not self.enabled:
            return None
        self.last_error = ""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"].strip()
        except (KeyError, json.JSONDecodeError, urllib.error.URLError, TimeoutError) as exc:
            self.last_error = str(exc)
            return None
