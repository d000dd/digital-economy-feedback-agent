"""Input loading utilities for CSV, JSON, and plain text feedback."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .models import FeedbackItem


TEXT_FIELDS = ("text", "feedback", "content", "comment", "意见", "反馈", "评价", "建议")
GROUP_FIELDS = ("group", "class", "班级", "小组", "来源")
TIME_FIELDS = ("created_at", "time", "date", "提交时间", "时间")


def load_feedback(path: str | Path) -> list[FeedbackItem]:
    """Load feedback records from a CSV, JSON, JSONL, or TXT file."""
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return _load_csv(file_path)
    if suffix in {".json", ".jsonl"}:
        return _load_json(file_path)
    return parse_text(file_path.read_text(encoding="utf-8"), source=file_path.name)


def parse_text(text: str, source: str = "manual") -> list[FeedbackItem]:
    """Parse newline-separated free text into feedback items."""
    rows = []
    for index, line in enumerate(text.splitlines(), start=1):
        clean = line.strip()
        if not clean:
            continue
        rows.append(FeedbackItem(id=str(index), text=clean, source=source))
    if not rows and text.strip():
        rows.append(FeedbackItem(id="1", text=text.strip(), source=source))
    return rows


def parse_csv_text(text: str, source: str = "web-csv") -> list[FeedbackItem]:
    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames:
        return _items_from_dict_rows(reader, source=source)
    return parse_text(text, source=source)


def _load_csv(path: Path) -> list[FeedbackItem]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(2048)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(handle, dialect=dialect)
        if reader.fieldnames:
            return _items_from_dict_rows(reader, source=path.name)

        handle.seek(0)
        plain_reader = csv.reader(handle, dialect=dialect)
        items = []
        for index, row in enumerate(plain_reader, start=1):
            text = " ".join(cell.strip() for cell in row if cell.strip())
            if text:
                items.append(FeedbackItem(id=str(index), text=text, source=path.name))
        return items


def _load_json(path: Path) -> list[FeedbackItem]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        payload = json.loads(text)
        rows = payload.get("items", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("JSON 输入应为列表，或包含 items 列表。")
    return _items_from_dict_rows(rows, source=path.name)


def _items_from_dict_rows(rows: Any, source: str) -> list[FeedbackItem]:
    items: list[FeedbackItem] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            text = str(row).strip()
            if text:
                items.append(FeedbackItem(id=str(index), text=text, source=source))
            continue

        text = _first_value(row, TEXT_FIELDS)
        if not text:
            continue
        item_id = str(row.get("id") or row.get("编号") or index)
        items.append(
            FeedbackItem(
                id=item_id,
                text=text,
                source=str(row.get("source") or source),
                group=_first_value(row, GROUP_FIELDS),
                created_at=_first_value(row, TIME_FIELDS),
            )
        )
    return items


def _first_value(row: dict[str, Any], fields: tuple[str, ...]) -> str:
    lowered = {str(key).lower(): value for key, value in row.items()}
    for field in fields:
        value = row.get(field)
        if value is None:
            value = lowered.get(field.lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""

