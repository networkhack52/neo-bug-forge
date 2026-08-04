"""Extract the list of questions from an uploaded questionnaire.

Supports .xlsx / .xlsm (openpyxl) and .csv. Vendor security questionnaires
are messy: header rows vary, there are section titles, blank rows, and an
answer column to fill. We auto-detect the question column by scoring each
column on how "question-like" its cells are, then return the cell
coordinates so answers can be written straight back into the same file.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Optional

from openpyxl import load_workbook


@dataclass
class ExtractedQuestion:
    row_index: int          # 0-based logical index across the sheet
    excel_row: int          # 1-based worksheet row (for write-back)
    question: str


@dataclass
class ParseResult:
    questions: list[ExtractedQuestion] = field(default_factory=list)
    question_col: Optional[int] = None   # 1-based worksheet column
    answer_col: Optional[int] = None     # 1-based; status/response goes here
    detail_col: Optional[int] = None     # 1-based; free-text comments go here (if distinct)
    sheet_name: Optional[str] = None
    kind: str = "xlsx"                    # xlsx | csv


_QUESTION_WORDS = (
    "do you", "does", "is ", "are ", "have you", "has ", "can ", "will ",
    "how ", "what ", "which ", "please describe", "please provide", "describe",
    "provide", "explain", "list ", "identify", "specify",
)


def _question_score(cell: str) -> float:
    if not cell:
        return 0.0
    text = cell.strip().lower()
    if len(text) < 8:
        return 0.0
    score = 0.0
    if "?" in text:
        score += 2.0
    if any(text.startswith(w) or (" " + w) in text for w in _QUESTION_WORDS):
        score += 1.5
    words = len(text.split())
    if 3 <= words <= 60:
        score += 1.0
    return score


def _looks_like_header(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in {"question", "questions", "control", "requirement", "item", "description"}


# Column a vendor fills with the Yes/No/Partially status.
_ANSWER_HEADERS = {"answer", "response", "vendor response", "compliant", "compliance",
                   "status", "yes/no", "answer (yes/no)"}
# Column a vendor fills with free-text explanation alongside the status.
_DETAIL_HEADERS = {"comments", "comment", "notes", "note", "details", "detail",
                   "additional information", "additional info", "explanation",
                   "description", "vendor comments", "evidence", "remarks"}


def _pick_columns(rows: list[list[str]]) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """Return (question_col, answer_col, detail_col) as 0-based indices.

    ``answer_col`` receives the compliance status; ``detail_col`` (when a
    distinct comments column exists) receives the free-text answer. When there
    is no separate comments column, ``detail_col`` is None and the two are
    written together into ``answer_col``.
    """
    if not rows:
        return None, None, None
    n_cols = max(len(r) for r in rows)
    col_scores = [0.0] * n_cols
    header = rows[0] if rows else []

    for r in rows[:200]:  # sample
        for c in range(n_cols):
            val = r[c] if c < len(r) else ""
            col_scores[c] += _question_score(val)

    # Header hints override weak signals.
    q_col = None
    for c in range(min(n_cols, len(header))):
        if _looks_like_header(header[c]):
            q_col = c
            break
    if q_col is None:
        q_col = max(range(n_cols), key=lambda c: col_scores[c]) if n_cols else None
    if q_col is None or col_scores[q_col] == 0:
        return None, None, None

    def _find_header(names: set[str]) -> Optional[int]:
        for c in range(min(n_cols, len(header))):
            if (header[c] or "").strip().lower() in names:
                return c
        return None

    # Answer (status) column: a matching header, else the column right of Q.
    a_col = _find_header(_ANSWER_HEADERS)
    if a_col is None:
        a_col = q_col + 1

    # Detail (comments) column: only when it's a distinct labelled column.
    d_col = _find_header(_DETAIL_HEADERS)
    if d_col == a_col:
        d_col = None
    return q_col, a_col, d_col


def parse_xlsx(data: bytes) -> ParseResult:
    wb = load_workbook(io.BytesIO(data), read_only=False, data_only=True)
    ws = wb.active
    rows: list[list[str]] = []
    for row in ws.iter_rows(values_only=True):
        rows.append(["" if v is None else str(v) for v in row])

    q_col, a_col, d_col = _pick_columns(rows)
    result = ParseResult(question_col=None if q_col is None else q_col + 1,
                         answer_col=None if a_col is None else a_col + 1,
                         detail_col=None if d_col is None else d_col + 1,
                         sheet_name=ws.title, kind="xlsx")
    if q_col is None:
        return result

    logical = 0
    header_seen = False
    for excel_row, r in enumerate(rows, start=1):
        cell = r[q_col] if q_col < len(r) else ""
        if _question_score(cell) <= 0:
            continue
        if not header_seen and _looks_like_header(cell):
            header_seen = True
            continue
        result.questions.append(
            ExtractedQuestion(row_index=logical, excel_row=excel_row, question=cell.strip())
        )
        logical += 1
    return result


def parse_csv(data: bytes) -> ParseResult:
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = [[c for c in row] for row in reader]
    q_col, a_col, d_col = _pick_columns(rows)
    result = ParseResult(question_col=None if q_col is None else q_col + 1,
                         answer_col=None if a_col is None else a_col + 1,
                         detail_col=None if d_col is None else d_col + 1,
                         kind="csv")
    if q_col is None:
        return result
    logical = 0
    header_seen = False
    for excel_row, r in enumerate(rows, start=1):
        cell = r[q_col] if q_col < len(r) else ""
        if _question_score(cell) <= 0:
            continue
        if not header_seen and _looks_like_header(cell):
            header_seen = True
            continue
        result.questions.append(
            ExtractedQuestion(row_index=logical, excel_row=excel_row, question=cell.strip())
        )
        logical += 1
    return result


def parse(filename: str, data: bytes) -> ParseResult:
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return parse_csv(data)
    if name.endswith((".xlsx", ".xlsm")):
        return parse_xlsx(data)
    # Best-effort: try xlsx, then csv.
    try:
        return parse_xlsx(data)
    except Exception:
        return parse_csv(data)
