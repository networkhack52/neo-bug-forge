/**
 * api.js — Neo Bug Forge API client
 * All Claude calls go through the backend — API key never touches the browser.
 */

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function callBugFix(code, errorMsg, language) {
  const response = await fetch(`${API_BASE}/v1/fix/public`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      broken_code:   code,
      error_message: errorMsg,
      language:      language,
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    if (response.status === 429) {
      throw new Error("Daily free limit reached (10 fixes/day). Sign up for unlimited access.");
    }
    throw new Error(err?.detail || `API error ${response.status}`);
  }

  return response.json();
}
