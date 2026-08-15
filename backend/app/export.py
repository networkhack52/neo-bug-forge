"""Write approved answers back into an .xlsx the customer can return.

Two modes:
  * ``export_simple`` — a clean two-column (Question / Answer) workbook,
    always available.
  * ``export_original`` — the customer's own uploaded file with the status
    and answer cells filled in, so they get their exact template back.
Answers are written next to their questions with a confidence column so the
reviewer can spot anything still flagged.
"""
from __future__ import annotations

import csv
import io
import json
import re

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

# Internal review/status notes (e.g. "[Attestly review: …]") are for the review
# screen only — strip them from anything the customer receives.
_NOTE_RE = re.compile(r"\s*\[Attestly[^\]]*\]", re.IGNORECASE)

LOCKED_TEXT = "Locked · upgrade to answer"


def clean_answer(text: str) -> str:
    return _NOTE_RE.sub("", text or "").strip()


def _citations(item: dict) -> list[dict]:
    raw = item.get("citations")
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw or "[]")
    except (ValueError, TypeError):
        return []


def status_of(item: dict) -> str:
    """One of Answered / Needs review / No evidence / Locked."""
    if item.get("locked"):
        return "Locked"
    if item.get("needs_review"):
        return "Needs review" if _citations(item) else "No evidence"
    return "Answered"


def source_cell(item: dict) -> str:
    """Document name + quoted line per citation, one per line."""
    lines = []
    for c in _citations(item):
        title = str(c.get("title") or "").strip()
        text = str(c.get("text") or "").strip()
        label = title if c.get("kind") == "document" else (title or "Approved answer")
        if label and text:
            lines.append(f'{label}: "{text}"')
        elif label:
            lines.append(label)
        elif text:
            lines.append(f'"{text}"')
    return "\n".join(lines)


def vendor_response(item: dict) -> str:
    """The answer text the customer sends: status prefix + detail, cleaned."""
    if item.get("locked"):
        return LOCKED_TEXT
    choice = (item.get("choice") or "").strip()
    answer = clean_answer(item.get("answer", ""))
    if choice and answer and not answer.lower().startswith(choice.lower()):
        return f"{choice}. {answer}"
    return answer or choice


def export_simple(name: str, items: list[dict]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Responses"

    header_fill = PatternFill("solid", fgColor="1F2937")
    header_font = Font(bold=True, color="FFFFFF")
    # The whole product is "proof of answer": every response carries its Source
    # (document + quoted line) and a Status the reviewer can scan.
    headers = ["Section", "Question", "Vendor Response", "Source", "Status"]
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(vertical="center")

    widths = [18, 55, 60, 50, 14]
    for c, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + c)].width = w

    review_fill = PatternFill("solid", fgColor="FEF3C7")
    locked_fill = PatternFill("solid", fgColor="E5E7EB")
    wrap_top = Alignment(wrap_text=True, vertical="top")
    for i, item in enumerate(items, start=1):
        r = i + 1
        status = status_of(item)
        ws.cell(row=r, column=1, value=item.get("section", "")).alignment = wrap_top
        ws.cell(row=r, column=2, value=item["question"]).alignment = wrap_top
        ws.cell(row=r, column=3, value=vendor_response(item)).alignment = wrap_top
        ws.cell(row=r, column=4, value=source_cell(item)).alignment = wrap_top
        ws.cell(row=r, column=5, value=status).alignment = Alignment(vertical="top")
        fill = locked_fill if status == "Locked" else (review_fill if item.get("needs_review") else None)
        if fill:
            for c in range(1, len(headers) + 1):
                ws.cell(row=r, column=c).fill = fill

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _cell_text(choice: str, answer: str, detail_col: bool) -> tuple[str, str]:
    """Split an item into (status_cell, detail_cell) text.

    When the template has a distinct comments column the status goes in the
    answer column and the free-text in the comments column. Otherwise the two
    are combined into the single answer column.
    """
    choice = (choice or "").strip()
    answer = clean_answer(answer)
    if detail_col:
        return choice, answer
    if choice and answer:
        # Avoid "Yes. Yes. …" when the answer already opens with the status.
        if answer.lower().startswith(choice.lower()):
            return answer, ""
        return f"{choice}. {answer}", ""
    return (choice or answer), ""


def can_export_original(q: dict) -> bool:
    """True when we captured enough of the upload to fill it back in."""
    return bool(q.get("source_bytes")) and bool(q.get("answer_col"))


def export_original(q: dict, items: list[dict]) -> bytes:
    """Fill the customer's own uploaded file and return the same format."""
    source = q.get("source_bytes")
    if not source:
        raise ValueError("no original file stored for this questionnaire")
    answer_col = q.get("answer_col")
    detail_col = q.get("detail_col")
    has_detail = bool(detail_col)
    kind = (q.get("source_kind") or "xlsx").lower()

    if kind == "csv":
        return _fill_csv(source, items, answer_col, detail_col, has_detail)
    return _fill_xlsx(source, q.get("sheet_name"), items, answer_col, detail_col, has_detail)


def _fill_xlsx(source: bytes, sheet_name, items, answer_col, detail_col, has_detail) -> bytes:
    wb = load_workbook(io.BytesIO(source), read_only=False, data_only=False)
    ws = wb[sheet_name] if sheet_name and sheet_name in wb.sheetnames else wb.active
    review_fill = PatternFill("solid", fgColor="FEF3C7")
    for item in items:
        row = int(item.get("excel_row") or 0)
        if row < 1:
            continue
        if item.get("locked"):
            status_text, detail_text = LOCKED_TEXT, ""
        else:
            status_text, detail_text = _cell_text(item.get("choice", ""), item.get("answer", ""), has_detail)
        c = ws.cell(row=row, column=answer_col, value=status_text)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if has_detail and detail_col:
            d = ws.cell(row=row, column=detail_col, value=detail_text)
            d.alignment = Alignment(wrap_text=True, vertical="top")
        if item.get("needs_review"):
            c.fill = review_fill
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _fill_csv(source: bytes, items, answer_col, detail_col, has_detail) -> bytes:
    text = source.decode("utf-8-sig", errors="replace")
    rows = [list(r) for r in csv.reader(io.StringIO(text))]
    by_row = {int(it.get("excel_row") or 0): it for it in items}
    a_idx = answer_col - 1
    d_idx = (detail_col - 1) if detail_col else None
    for excel_row, item in by_row.items():
        if excel_row < 1 or excel_row > len(rows):
            continue
        r = rows[excel_row - 1]
        needed = max(a_idx, d_idx if d_idx is not None else a_idx) + 1
        if len(r) < needed:
            r.extend([""] * (needed - len(r)))
        if item.get("locked"):
            status_text, detail_text = LOCKED_TEXT, ""
        else:
            status_text, detail_text = _cell_text(item.get("choice", ""), item.get("answer", ""), has_detail)
        r[a_idx] = status_text
        if d_idx is not None:
            r[d_idx] = detail_text
    out = io.StringIO()
    csv.writer(out).writerows(rows)
    return out.getvalue().encode("utf-8")
