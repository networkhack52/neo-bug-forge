"""Parse a document's own stated review/effective date from its text.

Reviewers treat stale evidence as a red flag, so Attestly surfaces the date of
the document behind every cited answer. We prefer a date the document states
about itself (a "Last reviewed" / "Effective date" line) over the upload date,
because that is the date a reviewer actually cares about.

Pure functions, no I/O — easy to unit test.
"""
from __future__ import annotations

import datetime as _dt
import re

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

# Freshness labels a policy/SOC 2 uses about itself. We only trust a date that
# sits next to one of these, so a random date in the body isn't mistaken for the
# review date.
_KEYWORD = (
    r"(?:last\s+review(?:ed)?|review(?:ed)?\s+date|effective\s+date|effective"
    r"|last\s+updated|last\s+revised|updated|revised|revision\s+date"
    r"|version\s+date|as\s+of|date\s+of\s+issue|issue\s+date|issued"
    r"|approved(?:\s+on)?|report\s+date|period\s+ending)"
)

# Date shapes, tried in priority order against the text just after a keyword.
# Each is its own regex (stdlib `re` forbids reusing a group name across an
# alternation), and each yields (y, m, d) via `_from_match`.
_PATTERNS = [
    # March 14, 2025  /  Mar. 14 2025
    re.compile(r"(?P<mon>[A-Za-z]{3,9})\.?\s+(?P<d>\d{1,2})(?:st|nd|rd|th)?,?\s+(?P<y>\d{4})"),
    # 14 March 2025
    re.compile(r"(?P<d>\d{1,2})(?:st|nd|rd|th)?\s+(?P<mon>[A-Za-z]{3,9})\.?,?\s+(?P<y>\d{4})"),
    # 2025-03-14  /  2025/03/14
    re.compile(r"(?P<y>\d{4})[-/.](?P<m>\d{1,2})[-/.](?P<d>\d{1,2})"),
    # 03/14/2025 (US month/day/year)
    re.compile(r"(?P<m>\d{1,2})/(?P<d>\d{1,2})/(?P<y>\d{2,4})"),
]
_KW_RE = re.compile(_KEYWORD, re.IGNORECASE)


def _valid(y: int, m: int, d: int) -> float | None:
    now_year = _dt.datetime.now(_dt.timezone.utc).year
    if y < 100:
        y += 2000
    if not (2000 <= y <= now_year + 1) or not (1 <= m <= 12) or not (1 <= d <= 31):
        return None
    try:
        return _dt.datetime(y, m, d, tzinfo=_dt.timezone.utc).timestamp()
    except ValueError:
        return None


def _from_match(gd: dict) -> float | None:
    mon = gd.get("mon")
    if mon:
        m = _MONTHS.get(mon.lower().rstrip("."))
        if not m:
            return None
        return _valid(int(gd["y"]), m, int(gd["d"]))
    return _valid(int(gd["y"]), int(gd["m"]), int(gd["d"]))


def parse_stated_date(text: str, scan_chars: int = 6000) -> float | None:
    """Return the epoch of the document's own stated review/effective date, or
    None. Scans the head of the document (where these lines almost always sit),
    looks just after each freshness keyword for a date, and picks the most
    recent valid one."""
    head = (text or "")[:scan_chars]
    best: float | None = None
    for kw in _KW_RE.finditer(head):
        window = head[kw.end(): kw.end() + 45]
        for pat in _PATTERNS:
            m = pat.search(window)
            if not m:
                continue
            ts = _from_match(m.groupdict())
            if ts is not None and (best is None or ts > best):
                best = ts
            break  # first pattern that matches this window wins
    return best


def to_iso(epoch: float | None) -> str:
    """YYYY-MM-DD for display/export, or '' if no date."""
    if not epoch:
        return ""
    return _dt.datetime.fromtimestamp(epoch, _dt.timezone.utc).strftime("%Y-%m-%d")


def months_old(epoch: float | None, now: float | None = None) -> float | None:
    """Age of a date in months (30.44-day months), or None."""
    if not epoch:
        return None
    now = now if now is not None else _dt.datetime.now(_dt.timezone.utc).timestamp()
    return (now - epoch) / (30.44 * 86400)
