"""Voice rules (PLAYBOOK §10) enforced on the backend's user-facing strings.

copy-lint.mjs covers the marketing site and the React UI. Python prose doesn't
lint cleanly with a JS-oriented regex tool, so the strings a customer actually
sees from the backend (abstentions, block prompts, export labels) are guarded
here instead. Generated answer text is governed by the drafting prompt (grounded,
no hype) — and legitimately contains figures like "99.9%" or "AES-256", so we do
NOT ban percentages at runtime; we ban the marketing tells.
"""
import re

from app import drafting, engine, export

_EM_DASH = re.compile(r"[—–]")
_HYPE = re.compile(
    r"\b(game[- ]?chang(er|ing)|revolutionary|seamless(ly)?|effortless(ly)?|supercharge|"
    r"unlock the power|cutting[- ]edge|world[- ]class|best[- ]in[- ]class|leverage)\b",
    re.I,
)
_UNBACKED = re.compile(
    r"\b(\d{2,3}%\s*(accurate|accuracy)|trusted by|thousands of (teams|companies)|"
    r"industry[- ]leading)\b",
    re.I,
)

# Strings the customer sees coming out of the backend.
USER_FACING = [
    drafting.NO_EVIDENCE,
    engine.BLOCKED_ANSWER,
    export.LOCKED_TEXT,
]


def test_backend_user_facing_strings_follow_voice_rules():
    for s in USER_FACING:
        assert not _EM_DASH.search(s), f"em/en dash in user-facing string: {s!r}"
        assert not _HYPE.search(s), f"hype word in user-facing string: {s!r}"
        assert not _UNBACKED.search(s), f"unbacked claim in user-facing string: {s!r}"


def test_export_status_labels_are_the_fixed_set():
    labels = {
        export.status_of({"locked": 1}),
        export.status_of({"needs_review": True, "citations": "[]"}),
        export.status_of({"needs_review": True, "citations": '[{"text":"x"}]'}),
        export.status_of({"needs_review": False}),
    }
    assert labels == {"Locked", "No evidence", "Needs review", "Answered"}
