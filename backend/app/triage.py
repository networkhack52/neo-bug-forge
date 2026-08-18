"""Scope a questionnaire BEFORE any model call.

Every practitioner scopes a questionnaire before writing anything: what format
is it, how many questions, how many can my library already answer, and which
rows don't apply to my product. Doing this first stops us burning quota on rows
that should never have been answered.

Nothing here calls the drafting model. Coverage uses the same reuse ranking the
engine uses (semantic when embeddings are on, lexical otherwise), so the preview
matches what actually happens at answer time.
"""
from __future__ import annotations

import re

from . import config, db, embeddings, retrieval

# CAIQ/CCM control-id domains (e.g. AIS-01, IAM-02) are a strong CAIQ signal.
_CCM_ID = re.compile(r"\b(AIS|AAC|BCR|CCC|DCS|DSP|EKM|GRC|HRS|IAM|IPY|IVS|LOG|SEF|STA|TVM|UEM)-\d{2}\b")


def detect_framework(filename: str, questions: list) -> str:
    """Best-effort label: SIG | SIG Lite | CAIQ | CAIQ Lite | VSAQ | Custom."""
    fn = (filename or "").lower()
    # Filename tokens (split on non-alphanumerics), so "SIG_Lite.xlsx" yields
    # the token "sig" — a plain \b boundary fails against underscores.
    fn_tokens = set(re.split(r"[^a-z0-9]+", fn))
    raw = " ".join(getattr(q, "question", "")[:200] for q in questions[:60])
    sample = raw.lower()
    # We only call it "Lite" when the file says so — guessing a Lite variant from
    # question count is unreliable (a small upload may just be a partial file).
    lite = "lite" in fn

    if ("caiq" in fn or "caiq" in sample or "consensus assessment" in sample
            or len(_CCM_ID.findall(raw)) >= 3):
        return "CAIQ Lite" if lite else "CAIQ"
    if "vsaq" in fn or "vsaq" in sample or "vendor security assessment" in sample:
        return "VSAQ"
    if ("sig" in fn_tokens or "standardized information gathering" in sample
            or "shared assessments" in sample):
        return "SIG Lite" if lite else "SIG"
    return "Custom"


# --- Library coverage -----------------------------------------------------
def coverage_flags(org_id: int, questions: list) -> list[bool]:
    """Per-question: would the existing Answer Library reuse a verbatim answer?
    (i.e. this row costs no quota). Batch-embeds the questions in one call when
    embeddings are enabled, so this stays cheap even for a 261-row CAIQ."""
    bank = db.list_answers(org_id, status="approved")
    if not bank:
        return [False] * len(questions)
    texts = [getattr(q, "question", "") for q in questions]
    vecs = embeddings.embed_texts(texts, input_type="query") if config.EMBEDDINGS_ENABLED else None
    out: list[bool] = []
    for i, q in enumerate(texts):
        qv = vecs[i] if vecs and i < len(vecs) else None
        matches = retrieval.rank(q, bank, query_vec=qv)
        out.append(retrieval.best_reusable(matches) is not None)
    return out


# --- Out-of-scope suggestions --------------------------------------------
_PHYSICAL_RE = re.compile(
    r"\b(data\s?cent(er|re)|server room|badge|turnstile|cctv|closed[- ]circuit|"
    r"hvac|air conditioning|raised floor|physical (access|security|entry)|"
    r"visitor log|loading dock|on[- ]premises data cent|fire suppression|"
    r"biometric (reader|access)|man[- ]?trap)\b",
    re.IGNORECASE,
)
_CLOUD_RE = re.compile(
    r"\b(aws|amazon web services|gcp|google cloud|microsoft azure|\bazure\b|"
    r"cloud[- ]?(native|only|hosted|infrastructure)|iaas|paas|serverless|"
    r"heroku|render|vercel|digitalocean)\b",
    re.IGNORECASE,
)
_OWN_DC_RE = re.compile(
    r"\b(our (own )?data\s?cent(er|re)|we operate .{0,20}data\s?cent|"
    r"on[- ]premises? (data\s?cent|infrastructure|servers))\b",
    re.IGNORECASE,
)

_CLOUD_ONLY_REASON = (
    "Cloud-only infrastructure. Physical data-centre controls are handled by our "
    "cloud provider under their SOC 2, so this doesn't apply to us."
)


def _org_is_cloud_only(org_id: int) -> bool:
    """True when the org's trust documents describe cloud hosting and give no
    sign of owning/operating a physical data centre. Conservative: needs a cloud
    signal AND no own-data-centre signal."""
    chunks = db.list_chunks(org_id)
    if not chunks:
        return False
    corpus = " ".join(c.get("text", "") for c in chunks[:400])
    if _OWN_DC_RE.search(corpus):
        return False
    return bool(_CLOUD_RE.search(corpus))


def out_of_scope_suggestions(org_id: int, questions: list) -> dict[int, str]:
    """{row_index: reason} for rows that look out of scope for this org's product.
    Only suggests physical/data-centre rows when the org looks cloud-only — the
    user still confirms before anything is excluded."""
    if not _org_is_cloud_only(org_id):
        return {}
    out: dict[int, str] = {}
    for q in questions:
        text = getattr(q, "question", "")
        if _PHYSICAL_RE.search(text):
            out[getattr(q, "row_index", 0)] = _CLOUD_ONLY_REASON
    return out
