"""Answer-Library retrieval — lexical fuzzy matching, blended with semantics.

Security-questionnaire questions repeat near-verbatim across vendors, so a
strong lexical/fuzzy matcher over the org's own approved answers already wins
the common case with no embedding API. ``token_set_ratio`` is
order/duplication insensitive, so "Do you encrypt data at rest?" matches
"Is data at rest encrypted?" highly.

When a Voyage key is configured, we additionally blend a semantic cosine score
so paraphrases that share little surface wording ("Where is data stored?" vs
"In which region does customer data reside?") still match. The blend is a
``max``: semantics can only *raise* recall, never drop a strong lexical hit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from . import config, embeddings, fuzzy


@dataclass
class Match:
    answer_id: int
    question: str
    answer: str
    category: str
    score: float


def _scorer(query: str, choice: str) -> float:
    # Blend two views: token_set (order/duplication-insensitive overlap) and a
    # sort+substring blend (catches close phrasings and embedded matches).
    return max(
        fuzzy.token_set_ratio(query, choice),
        0.6 * fuzzy.token_sort_ratio(query, choice) + 0.4 * fuzzy.partial_ratio(query, choice),
    )


def rank(question: str, bank: list[dict], limit: int = config.CONTEXT_TOP_K) -> list[Match]:
    """Return the top ``limit`` Answer-Library matches, best first."""
    if not bank:
        return []

    # Optional semantic layer: embed the query once, cosine against stored
    # question vectors. Skipped entirely (query_vec == []) when disabled.
    query_vec = embeddings.embed_one(question, input_type="query")

    scored: list[tuple[float, dict]] = []
    for a in bank:
        lexical = _scorer(question, a["question"])
        final = lexical
        if query_vec:
            vec = embeddings.from_blob(a.get("embedding"))
            if vec:
                semantic = embeddings.cosine(query_vec, vec) * config.SEMANTIC_WEIGHT
                final = max(final, semantic)
        scored.append((final, a))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    matches: list[Match] = []
    for score, a in scored[:limit]:
        matches.append(
            Match(
                answer_id=a["id"],
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
