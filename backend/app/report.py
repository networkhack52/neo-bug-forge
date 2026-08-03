"""Render a Security-Questionnaire Readiness Assessment as a self-contained,
shareable HTML page — the artifact a founder emails to a prospect.

No external assets (inline CSS only) so it renders anywhere and can be attached
or hosted as-is.
"""
from __future__ import annotations

import html

from . import config
from .assessment import Assessment

GRADE_COLORS = {"A": "#059669", "B": "#0891b2", "C": "#d97706", "D": "#dc2626", "F": "#b91c1c"}


def render(a: Assessment, cta_url: str = "https://app.example.com") -> str:
    brand = html.escape(config.BRAND_NAME)
    company = html.escape(a.company)
    color = GRADE_COLORS.get(a.grade, "#334155")

    findings_rows = ""
    for f in sorted(a.findings, key=lambda x: (x.ok, -x.weight)):
        icon = "✓" if f.ok else "✕"
        icon_color = "#059669" if f.ok else "#dc2626"
        note = "" if f.ok else f'<div class="note">{html.escape(f.note)}</div>'
        findings_rows += f"""
        <tr>
          <td class="ico" style="color:{icon_color}">{icon}</td>
          <td><strong>{html.escape(f.label)}</strong>{note}</td>
        </tr>"""

    sample_html = ""
    if a.sample:
        rows = ""
        for s in a.sample:
            if s["matched"]:
                badge = f'<span class="badge ok">auto-answered · {int(s["confidence"])}%</span>'
                ans = html.escape(s["answer"][:180]) + ("…" if len(s["answer"]) > 180 else "")
            else:
                badge = '<span class="badge no">needs input</span>'
                ans = '<span class="muted">no match yet — becomes reusable once answered once</span>'
            rows += f"""
            <tr><td><strong>{html.escape(s['question'])}</strong><br>{badge}<div class="ans">{ans}</div></td></tr>"""
        sample_html = f"""
        <h2>Live proof — {a.autoanswer_rate}% of a standard questionnaire auto-answered</h2>
        <p class="muted">We ran a standard security questionnaire through {brand} using only a
        generic starter library. With your own approved answers loaded, coverage climbs fast.</p>
        <table class="sample">{rows}</table>"""

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{company} — Security Questionnaire Readiness</title>
<style>
  body {{ font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
         color:#0f172a; background:#f1f5f9; margin:0; padding:24px; }}
  .wrap {{ max-width:720px; margin:0 auto; background:#fff; border:1px solid #e2e8f0;
          border-radius:16px; overflow:hidden; }}
  .head {{ padding:28px 32px; border-bottom:1px solid #e2e8f0; }}
  .brand {{ font-weight:700; color:#2563eb; letter-spacing:-.02em; }}
  h1 {{ font-size:22px; margin:12px 0 4px; }}
  .sub {{ color:#64748b; font-size:14px; }}
  .scorecard {{ display:flex; align-items:center; gap:24px; padding:28px 32px; background:#f8fafc; }}
  .grade {{ font-size:64px; font-weight:800; line-height:1; color:{color}; }}
  .score {{ font-size:15px; color:#334155; }}
  .score b {{ font-size:20px; }}
  .body {{ padding:8px 32px 28px; }}
  h2 {{ font-size:16px; margin:24px 0 8px; }}
  table {{ width:100%; border-collapse:collapse; }}
  td {{ padding:10px 6px; border-bottom:1px solid #eef2f6; vertical-align:top; font-size:14px; }}
  .ico {{ width:24px; font-weight:800; font-size:16px; text-align:center; }}
  .note {{ color:#64748b; font-size:13px; margin-top:3px; }}
  .cost {{ background:#fef2f2; border:1px solid #fecaca; border-radius:12px; padding:16px 20px; margin:20px 0; }}
  .cost b {{ color:#b91c1c; }}
  .badge {{ display:inline-block; font-size:11px; font-weight:700; padding:2px 8px; border-radius:999px; }}
  .badge.ok {{ background:#ecfdf5; color:#059669; }}
  .badge.no {{ background:#f1f5f9; color:#64748b; }}
  .ans {{ font-size:13px; color:#334155; margin-top:6px; }}
  .muted {{ color:#94a3b8; }}
  .cta {{ display:inline-block; background:#2563eb; color:#fff; text-decoration:none;
         padding:12px 22px; border-radius:10px; font-weight:600; margin-top:8px; }}
  .foot {{ padding:20px 32px; border-top:1px solid #e2e8f0; color:#94a3b8; font-size:12px; }}
</style></head>
<body><div class="wrap">
  <div class="head">
    <div class="brand">◆ {brand}</div>
    <h1>Security Questionnaire Readiness — {company}</h1>
    <div class="sub">How prepared your team is to answer vendor security questionnaires fast.</div>
  </div>
  <div class="scorecard">
    <div class="grade">{a.grade}</div>
    <div class="score"><b>{a.score}/100</b><br>{html.escape(a.grade_summary)}</div>
  </div>
  <div class="body">
    <h2>What we looked at</h2>
    <table>{findings_rows}</table>

    <div class="cost">
      At ~{a.monthly_questionnaires} questionnaires/month, your team spends roughly
      <b>{a.hours_saved_per_month:.0f} recoverable hours every month</b> re-answering the same
      questions — about <b>${a.annual_time_cost:,.0f}/year</b> of loaded time, before counting
      deals slowed or lost to late responses.
    </div>
    {sample_html}

    <h2>Close the gap</h2>
    <p class="muted">{brand} turns your approved answers into a reusable bank, auto-answers the
    repeats, and drafts the rest — so questionnaires take minutes, not weeks.</p>
    <a class="cta" href="{html.escape(cta_url)}">Answer your next questionnaire free →</a>
  </div>
  <div class="foot">Prepared by {brand}. Estimates are directional, based on the signals provided.</div>
</div></body></html>"""
