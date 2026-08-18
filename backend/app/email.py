"""Outbound transactional email via Resend.

Cloudflare Email Routing (which serves hello@tryattestly.com) is INBOUND only,
so a real sending provider is needed for anything the app initiates — currently
just password-reset links.

Gated on ``config.RESEND_API_KEY``. When no key is set the app still works
end-to-end: :func:`send_password_reset` returns False and the caller logs the
link to the server log instead (fine for local dev / before the sending domain
is verified). In production, set RESEND_API_KEY and verify tryattestly.com in
Resend (SPF/DKIM DNS records) so the link actually reaches the user.
"""
from __future__ import annotations

import logging

import httpx

from . import config

log = logging.getLogger("attestly.email")


def _send(to: str, subject: str, html: str, text: str) -> bool:
    if not config.EMAIL_ENABLED:
        return False
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                f"{config.RESEND_BASE_URL}/emails",
                headers={
                    "Authorization": f"Bearer {config.RESEND_API_KEY}",
                    "content-type": "application/json",
                },
                json={
                    "from": config.RESEND_FROM,
                    "to": [to],
                    "subject": subject,
                    "html": html,
                    "text": text,
                },
            )
            resp.raise_for_status()
        return True
    except Exception:  # never surface provider errors to the caller / user
        log.exception("Resend send failed for %s", subject)
        return False


def send_password_reset(to: str, reset_url: str) -> bool:
    """Email a password-reset link. Returns True if the provider accepted it."""
    brand = config.BRAND_NAME
    subject = f"Reset your {brand} password"
    text = (
        f"We received a request to reset your {brand} password.\n\n"
        f"Reset it here (link expires in 1 hour):\n{reset_url}\n\n"
        "If you didn't request this, you can ignore this email — your password "
        "won't change."
    )
    html = f"""\
<div style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;max-width:520px;margin:0 auto;color:#14181c;line-height:1.6">
  <p style="font-weight:800;font-size:18px;letter-spacing:-.02em;color:#0a7d6b;margin:0 0 18px">{brand}</p>
  <p>We received a request to reset your {brand} password.</p>
  <p style="margin:24px 0">
    <a href="{reset_url}" style="background:#0a7d6b;color:#fff;text-decoration:none;font-weight:600;padding:11px 20px;border-radius:8px;display:inline-block">Reset password</a>
  </p>
  <p style="color:#58636d;font-size:14px">This link expires in 1 hour. If you didn't request this, you can ignore this email — your password won't change.</p>
  <p style="color:#58636d;font-size:13px;word-break:break-all">Or paste this link into your browser:<br>{reset_url}</p>
</div>"""
    return _send(to, subject, html, text)
