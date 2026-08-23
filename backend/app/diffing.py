"""Decide whether two answers to the same question *materially* differ.

Used to catch the failure practitioners describe: an answer sent to one customer
contradicts an answer sent to another months earlier, and nobody notices. We
compare a freshly drafted answer against the approved library answer for the
same question and flag a real change — a flipped yes/no, a different number, a
different frequency, or a different named technology — while ignoring pure
wording changes.

Deliberately conservative: only flag when BOTH answers state a specific of the
same kind and the specifics conflict, so a reworded-but-equivalent answer does
not raise a false alarm.
"""
from __future__ import annotations

import re

from .drafting import infer_choice

_FREQ = {
    "hourly", "daily", "nightly", "weekly", "biweekly", "fortnightly", "monthly",
    "bimonthly", "quarterly", "semiannually", "biannually", "annually", "yearly",
    "continuously", "realtime",
}
_FREQ_RE = re.compile(r"\b(" + "|".join(_FREQ) + r")\b", re.IGNORECASE)

# Versioned/technical tokens: an UPPERCASE acronym glued to a number, e.g.
# AES-256, TLS1.2, SHA-256, SOC2, ISO27001. The uppercase stem avoids matching
# ordinary prose like "for 90" or "days 30" as a technology token. We normalise
# out spaces/dashes so "AES 256" and "AES-256" compare equal.
_TECH_RE = re.compile(r"\b([A-Z]{2,6})[\s\-]?(\d{2,5}(?:\.\d+)?)\b")


def _polarity(text: str) -> str:
    return infer_choice(text)


def _tech(text: str) -> set[str]:
    # Ignore pure years (e.g. ISO 27001 is a standard; "2024" alone is not tech).
    return {
        f"{m.group(1).lower()}{m.group(2)}"
        for m in _TECH_RE.finditer(text or "")
        if not re.fullmatch(r"(19|20)\d{2}", m.group(2))
    }


def _frequencies(text: str) -> set[str]:
    return {m.group(1).lower() for m in _FREQ_RE.finditer(text or "")}


def _numbers(text: str) -> set[str]:
    """Standalone numbers, after removing tech tokens (so the 256 in AES-256 or
    the 2 in SOC 2 is not mistaken for a bare figure)."""
    stripped = _TECH_RE.sub(" ", text or "")
    out = set()
    # Allow a hyphen OR a space between the number and its unit, so "72-hour" and
    # "72 hours" normalise to the same token (they mean the same thing).
    for m in re.finditer(
        r"\b(\d+(?:\.\d+)?)[-\s]*(%|percent|hours?|hrs?|days?|weeks?|months?|years?|minutes?|mins?)?",
        stripped, re.IGNORECASE,
    ):
        num = m.group(1)
        unit = (m.group(2) or "").lower().rstrip("s")
        unit = {"hr": "hour", "min": "minute"}.get(unit, unit)  # normalise abbreviations
        # Ignore lone small integers with no unit (list markers, "1-3 sentences").
        if unit:
            out.add(f"{num}{unit}")
        elif "." in num or len(num) >= 2:
            out.add(num)
    return out


def materially_differs(new: str, prior: str) -> str | None:
    """Return a short reason string if the two answers conflict on a specific,
    else None. Pure wording changes return None."""
    if not new or not prior:
        return None
    pn, pp = _polarity(new), _polarity(prior)
    if pn and pp and pn != pp:
        return f"answer changed from “{pp}” to “{pn}”"
    fn, fp = _frequencies(new), _frequencies(prior)
    if fn and fp and fn != fp:
        return f"frequency changed ({', '.join(sorted(fp))} → {', '.join(sorted(fn))})"
    tn, tp = _tech(new), _tech(prior)
    if tn and tp and tn != tp:
        return "a named technology or standard changed"
    nn, npr = _numbers(new), _numbers(prior)
    if nn and npr and nn != npr:
        return "a number or time period changed"
    return None
