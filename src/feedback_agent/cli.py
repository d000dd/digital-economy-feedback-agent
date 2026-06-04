"""Command line interface for the feedback agent."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .agent import FeedbackAgent
from .data_loader import load_feedback, parse_text
from .feishu import FeishuWebhookClient
from .server import run_server


SAMPLE_ROWS = [
    ("1", "数字经济里数据要素和平台经济的区别还不够清楚，希望老师补充企业案例。", "一班", "2026-05-01"),
    ("2", "Python 数据处理作业有点难，pandas 报错后不知道怎么定位问题。", "一班", "2026-05-02"),
    ("3", "飞书通知很及时，课件资料也方便查找。", "二班", "2026-05-02"),
    ("4", "考试范围和评分标准希望提前说明，不然复习压力比较大。", "二班", "2026-05-03"),
    ("5", "论文选题想结合直播电商和平台治理，希望有文献阅读模板。", "三班", "2026-05-03"),
    ("6", "课堂节奏有时太快，基础弱的同学来不及跟上。", "三班", "2026-05-04"),
    ("7", "案例讨论很有用，建议增加数字人民币或跨境电商的数据集。", "一班", "2026-05-05"),
    ("8", "小组展示分工不清楚，希望能在飞书表格里明确负责人和截止时间。", "二班", "2026-05-05"),
]


def main(argv: list[str] | None = None) -> int:
    _load_dotenv(Path(".env"))
    parser = argparse.ArgumentParser(
        prog="feedback-agent",
        description="数字经济课程反馈分析与飞书通知智能体",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="分析 CSV/JSON/TXT 反馈文件")
    analyze_parser.add_argument("-i", "--input", required=True, help="输入文件路径")
    analyze_parser.add_argument("-o", "--output", help="Markdown 报告输出路径")
    analyze_parser.add_argument("--json", dest="json_output", help="JSON 结果输出路径")
    analyze_parser.add_argument("--push-feishu", action="store_true", help="推送摘要到飞书机器人")

    sample_parser = subparsers.add_parser("sample", help="生成示例反馈 CSV")
    sample_parser.add_argument(
        "-o", "--output", default="data/sample_feedback.csv", help="示例文件输出路径"
    )

    serve_parser = subparsers.add_parser("serve", help="启动 Web 界面")
    serve_parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    serve_parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8765")))

    quick_parser = subparsers.add_parser("quick", help="直接分析一段换行分隔文本")
    quick_parser.add_argument("text", help="反馈文本，多条反馈可用换行分隔")

    args = parser.parse_args(argv)
    if args.command == "sample":
        return _write_sample(Path(args.output))
    if args.command == "serve":
        run_server(host=args.host, port=args.port)
        return 0
    if args.command == "quick":
        result = FeedbackAgent().analyze(parse_text(args.text))
        print(result.report_markdown)
        return 0
    if args.command == "analyze":
        return _analyze(args)
    return 2


def _analyze(args: argparse.Namespace) -> int:
    items = load_feedback(args.input)
    result = FeedbackAgent().analyze(items)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result.report_markdown, encoding="utf-8")
    if args.json_output:
        json_output = Path(args.json_output)
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if args.push_feishu:
        send_result = FeishuWebhookClient().send_result(result)
        print(send_result.message)
        if not send_result.ok:
            return 1
    if not args.output and not args.json_output:
        print(result.report_markdown)
    return 0


def _write_sample(path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["id,text,group,created_at"]
    for row_id, text, group, created_at in SAMPLE_ROWS:
        safe_text = '"' + text.replace('"', '""') + '"'
        lines.append(f"{row_id},{safe_text},{group},{created_at}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已生成示例数据：{path}")
    return 0


def _load_dotenv(path: Path) -> None:
    """Load KEY=VALUE lines from a local .env file without external dependencies."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
