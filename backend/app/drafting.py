"""Claude drafting layer.

Only called when the Answer Bank has no high-confidence verbatim match.
Grounds the model in the closest prior answers so drafts stay consistent
with what the company has already said. Degrades to a deterministic,
clearly-flagged fallback when no ANTHROPIC_API_KEY is present, so the whole
pipeline runs offline.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from . import config
from .retrieval import Match

SYSTEM_PROMPT = (
    "You are a security & compliance analyst helping a B2B SaaS vendor answer a "
    "customer's security questionnaire. Answer ONLY from the provided context of the "
    "company's previously approved answers and facts. Be concise, factual, and use the "
    "first person plural ('We ...'). If the context does not contain enough information "
    "to answer confidently, say what is known and set needs_review to true. Never invent "
    "certifications, controls, or commitments that are not supported by the context. "
    "Respond as strict JSON: {\"answer\": string, \"confidence\": number 0-100, "
    "\"needs_review\": boolean, \"rationale\": string}."
)


@dataclass
class Draft:
    answer: str
    confidence: float
    needs_review: bool
    match_type: str  # drafted | fallback


def _build_user_prompt(question: str, context: list[Match]) -> str:
    lines = ["QUESTION:", question, "", "CONTEXT — previously approved answers:"]
    if context:
        for i, m in enumerate(context, 1):
            lines.append(f"[{i}] (similarity {m.score:.0f}) Q: {m.question}")
            lines.append(f"    A: {m.answer}")
    else:
        lines.append("(no closely related prior answers)")
    lines.append("")
    lines.append("Draft the best answer to QUESTION grounded in the CONTEXT.")
    return "\n".join(lines)


# Below this similarity, an offline fallback must not paste a prior answer —
# it would be misleading. Say "no confident match" instead.
FALLBACK_MIN_SIMILARITY = 70.0


def _fallback(question: str, context: list[Match]) -> Draft:
    """No LLM available: reuse the nearest answer only if it is close enough."""
    if context and context[0].score >= FALLBACK_MIN_SIMILARITY:
        top = context[0]
        note = (
            f"{top.answer}\n\n[Attestly: drafting model disabled — adapted from a similar "
            f"prior answer (similarity {top.score:.0f}). Please review before sending.]"
        )
        return Draft(answer=note, confidence=min(top.score, 60.0),
                     needs_review=True, match_type="fallback")
    return Draft(
        answer="[No approved answer found. Please answer manually and approve so Attestly "
               "can reuse it next time.]",
        confidence=0.0,
        needs_review=True,
        match_type="fallback",
    )


def draft_answer(question: str, context: list[Match]) -> Draft:
    if not config.LLM_ENABLED:
        return _fallback(question, context)

    payload = {
        "model": config.ANTHROPIC_MODEL,
        "max_tokens": 700,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": _build_user_prompt(question, context)}],
    }
    headers = {
        "x-api-key": config.ANTHROPIC_API_KEY,
        "anthropic-version": config.ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{config.ANTHROPIC_BASE_URL}/v1/messages", headers=headers, json=payload
            )
            resp.raise_for_status()
            body = resp.json()
        text = "".join(
            block.get("text", "") for block in body.get("content", []) if block.get("type") == "text"
        ).strip()
        parsed = _extract_json(text)
        return Draft(
            answer=parsed.get("answer", text).strip(),
            confidence=float(parsed.get("confidence", 55)),
            needs_review=bool(parsed.get("needs_review", True)),
            match_type="drafted",
        )
    except Exception as exc:  # network/parse errors must not break the batch
        fb = _fallback(question, context)
        fb.answer += f"\n\n[Attestly: model call failed: {type(exc).__name__}]"
        return fb


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {"answer": text, "confidence": 50, "needs_review": True}
