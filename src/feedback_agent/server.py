"""Small local HTTP server for the assignment web UI."""

from __future__ import annotations

import json
import mimetypes
import socket
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .agent import FeedbackAgent
from .data_loader import parse_csv_text, parse_text
from .feishu import FeishuWebhookClient
from .models import AnalysisResult


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = PROJECT_ROOT / "web"


def run_server(host: str = "0.0.0.0", port: int = 8765) -> None:
    """Run the local web UI and API server."""

    class Handler(AgentRequestHandler):
        agent = FeedbackAgent()

    server = ThreadingHTTPServer((host, port), Handler)
    _print_server_urls(host, port, Handler.agent.llm.status())
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


class AgentRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler with JSON APIs and static file serving."""

    agent: FeedbackAgent

    def do_GET(self) -> None:  # noqa: N802 - stdlib API
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"ok": True, "name": "digital-economy-feedback-agent"})
            return
        if parsed.path == "/api/config":
            self._send_json({"ok": True, "ai": self.agent.llm.status()})
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:  # noqa: N802 - stdlib API
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
            if parsed.path == "/api/analyze":
                self._handle_analyze(payload)
                return
            if parsed.path == "/api/feishu":
                self._handle_feishu(payload)
                return
            self._send_json({"ok": False, "error": "未知接口。"}, HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self._send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _handle_analyze(self, payload: dict) -> None:
        text = str(payload.get("text") or "")
        csv_text = str(payload.get("csv") or "")
        items = []
        if csv_text.strip():
            items.extend(parse_csv_text(csv_text, source="web-upload"))
        if text.strip():
            items.extend(parse_text(text, source="web-manual"))
        result = self.agent.analyze(items)
        self._send_json({"ok": True, "result": result.to_dict()})

    def _handle_feishu(self, payload: dict) -> None:
        result_payload = payload.get("result")
        if not isinstance(result_payload, dict):
            raise ValueError("缺少 result 对象。")
        result = _result_from_payload(result_payload)
        webhook_value = str(payload.get("webhook") or "").strip()
        secret_value = str(payload.get("secret") or "").strip()
        webhook = webhook_value or None
        secret = secret_value or None
        send_result = FeishuWebhookClient(webhook, secret).send_result(result)
        self._send_json(
            {
                "ok": send_result.ok,
                "status": send_result.status,
                "message": send_result.message,
                "response": send_result.response,
            },
            HTTPStatus.OK if send_result.ok else HTTPStatus.BAD_GATEWAY,
        )

    def _serve_static(self, request_path: str) -> None:
        if request_path in {"", "/"}:
            request_path = "/index.html"
        relative = unquote(request_path).lstrip("/")
        candidate = (WEB_DIR / relative).resolve()
        if not str(candidate).startswith(str(WEB_DIR.resolve())) or not candidate.is_file():
            self._send_json({"ok": False, "error": "文件不存在。"}, HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        body = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("请求体不是有效 JSON。") from exc
        if not isinstance(payload, dict):
            raise ValueError("请求体必须是 JSON 对象。")
        return payload

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _result_from_payload(payload: dict) -> AnalysisResult:
    top_keywords = []
    for entry in payload.get("top_keywords", []):
        if isinstance(entry, dict):
            top_keywords.append((str(entry.get("keyword", "")), int(entry.get("count", 0))))
        elif isinstance(entry, (list, tuple)) and len(entry) == 2:
            top_keywords.append((str(entry[0]), int(entry[1])))
    return AnalysisResult(
        generated_at=str(payload.get("generated_at") or ""),
        total=int(payload.get("total") or 0),
        category_counts=dict(payload.get("category_counts") or {}),
        sentiment_counts=dict(payload.get("sentiment_counts") or {}),
        priority_counts=dict(payload.get("priority_counts") or {}),
        top_keywords=top_keywords,
        summary=str(payload.get("summary") or ""),
        recommendations=[str(item) for item in payload.get("recommendations", [])],
        items=[],
        report_markdown=str(payload.get("report_markdown") or ""),
        feishu_message=str(payload.get("feishu_message") or ""),
        warnings=[str(item) for item in payload.get("warnings", [])],
    )


def _print_server_urls(host: str, port: int, ai_status: dict[str, str | bool]) -> None:
    mode = "Live AI" if ai_status.get("enabled") else "Rules"
    if host in {"0.0.0.0", "::"}:
        print(f"Web UI: http://127.0.0.1:{port}")
        lan_ip = _detect_lan_ip()
        if lan_ip:
            print(f"LAN URL: http://{lan_ip}:{port}")
    else:
        print(f"Web UI: http://{host}:{port}")
    print(f"AI mode: {mode}")


def _detect_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return ""
