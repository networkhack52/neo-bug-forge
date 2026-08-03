"""Pure-Python fuzzy string matching (no native dependencies).

Replaces rapidfuzz so the app installs anywhere — including Windows without a
C++ toolchain — with zero compilation. Implements the fuzzywuzzy-style scorers
used for Answer-Bank matching, on top of the stdlib ``difflib``.

Scores are 0-100. For a few hundred to a few thousand bank entries this is
plenty fast (matching is milliseconds); swap back to a native lib only if the
bank grows into the tens of thousands.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> list[str]:
    return _TOKEN.findall(s.lower())


def _ratio(a: str, b: str) -> float:
    if not a and not b:
        return 100.0
    return SequenceMatcher(None, a, b).ratio() * 100.0


def ratio(a: str, b: str) -> float:
    return _ratio(a, b)


def token_sort_ratio(a: str, b: str) -> float:
    """Ratio after sorting each string's tokens — order-insensitive."""
    sa = " ".join(sorted(_tokens(a)))
    sb = " ".join(sorted(_tokens(b)))
    return _ratio(sa, sb)


def token_set_ratio(a: str, b: str) -> float:
    """Set-based ratio: high when one string's tokens are a subset of the other.

    Matches "Do you encrypt data at rest?" to "Is data at rest encrypted?"
    strongly, regardless of word order or extra words.
    """
    ta, tb = set(_tokens(a)), set(_tokens(b))
    if not ta and not tb:
        return 100.0
    intersection = ta & tb
    diff_ab = ta - tb
    diff_ba = tb - ta
    sect = " ".join(sorted(intersection))
    combined_ab = (sect + " " + " ".join(sorted(diff_ab))).strip()
    combined_ba = (sect + " " + " ".join(sorted(diff_ba))).strip()
    return max(
        _ratio(sect, combined_ab),
        _ratio(sect, combined_ba),
        _ratio(combined_ab, combined_ba),
    )


def partial_ratio(a: str, b: str) -> float:
    """Best matching-substring ratio (the shorter slid across the longer)."""
    if not a or not b:
        return 0.0
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    sm = SequenceMatcher(None, shorter, longer)
    best = 0.0
    seen = set()
    for i, j, n in sm.get_matching_blocks():
        start = max(j - i, 0)
        if start in seen:
            continue
        seen.add(start)
        window = longer[start : start + len(shorter)]
        best = max(best, _ratio(shorter, window))
        if best >= 100.0:
            break
    return best
