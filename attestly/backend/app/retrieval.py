"""Answer-Bank retrieval.

Security-questionnaire questions repeat near-verbatim across vendors, so a
strong lexical/fuzzy matcher over the org's own approved answers beats a
generic semantic index for the common case — and needs no embedding API.

``token_set_ratio`` is order/duplication insensitive, so
"Do you encrypt data at rest?" matches "Is data at rest encrypted?" highly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from rapidfuzz import fuzz, process

from . import config


@dataclass
class Match:
    answer_id: int
    question: str
    answer: str
    category: str
    score: float


def _scorer(query: str, choice: str, *, score_cutoff: float = 0, **_: object) -> float:
    # Blend two views: token_set (semantic-ish overlap) and partial (substring).
    # rapidfuzz passes score_cutoff/other kwargs to custom scorers, so absorb them.
    return max(
        fuzz.token_set_ratio(query, choice),
        0.6 * fuzz.token_sort_ratio(query, choice) + 0.4 * fuzz.partial_ratio(query, choice),
    )


def rank(question: str, bank: list[dict], limit: int = config.CONTEXT_TOP_K) -> list[Match]:
    """Return the top ``limit`` Answer-Bank matches, best first."""
    if not bank:
        return []
    choices = {a["id"]: a["question"] for a in bank}
    by_id = {a["id"]: a for a in bank}
    results = process.extract(
        question,
        choices,
        scorer=_scorer,
        limit=limit,
    )
    matches: list[Match] = []
    for _matched_text, score, aid in results:
        a = by_id[aid]
        matches.append(
            Match(
                answer_id=aid,
                question=a["question"],
                answer=a["answer"],
                category=a.get("category", "general"),
                score=float(score),
            )
        )
    return matches


def best_reusable(matches: list[Match]) -> Optional[Match]:
    """The top match if it clears the verbatim-reuse threshold, else None."""
    if matches and matches[0].score >= config.FUZZY_REUSE_THRESHOLD:
        return matches[0]
    return None


def context_matches(matches: list[Match]) -> list[Match]:
    """Matches good enough to ground an LLM draft."""
    return [m for m in matches if m.score >= config.FUZZY_CONTEXT_THRESHOLD]
