// Thin client for the Attestly API. Token is persisted in localStorage.
const BASE = import.meta.env.VITE_API_URL || "";

export function getToken() {
  return localStorage.getItem("attestly_token") || "";
}
export function setToken(t) {
  localStorage.setItem("attestly_token", t);
}
export function clearToken() {
  localStorage.removeItem("attestly_token");
}

async function req(path, { method = "GET", body, isForm = false } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  let payload = body;
  if (body && !isForm) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  const res = await fetch(BASE + path, { method, headers, body: payload });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.blob();
}

export const api = {
  health: () => req("/health"),
  plans: () => req("/v1/plans"),
  signup: (name, email, password) =>
    req("/v1/signup", { method: "POST", body: { name, email, password } }),
  login: (email, password) => req("/v1/login", { method: "POST", body: { email, password } }),
  forgotPassword: (email) => req("/v1/password/forgot", { method: "POST", body: { email } }),
  resetPassword: (token, password) =>
    req("/v1/password/reset", { method: "POST", body: { token, password } }),
  me: () => req("/v1/me"),
  rotateToken: () => req("/v1/token/rotate", { method: "POST" }),
  answers: () => req("/v1/answers"),
  addAnswer: (a) => req("/v1/answers", { method: "POST", body: a }),
  bulkAnswers: (answers) => req("/v1/answers/bulk", { method: "POST", body: { answers } }),
  seedStarter: () => req("/v1/answers/seed_starter", { method: "POST" }),
  listQuestionnaires: () => req("/v1/questionnaires"),
  getQuestionnaire: (id) => req(`/v1/questionnaires/${id}`),
  uploadQuestionnaire: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return req("/v1/questionnaires", { method: "POST", body: fd, isForm: true });
  },
  answerQuestionnaire: (id, exclude = []) =>
    req(`/v1/questionnaires/${id}/answer`, { method: "POST", body: { exclude } }),
  approveItem: (id, answer) => req(`/v1/items/${id}/approve`, { method: "POST", body: { answer } }),
  setRemediation: (id, body) => req(`/v1/items/${id}/remediation`, { method: "POST", body }),
  resolveContradiction: (id, keep) =>
    req(`/v1/items/${id}/resolve_contradiction`, { method: "POST", body: { keep } }),
  documents: () => req("/v1/documents"),
  uploadDocument: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return req("/v1/documents", { method: "POST", body: fd, isForm: true });
  },
  deleteDocument: (id) => req(`/v1/documents/${id}`, { method: "DELETE" }),
  checkout: (tier, interval = "month") =>
    req("/v1/billing/checkout", { method: "POST", body: { tier, interval } }),
  confirm: (tier) => req("/v1/billing/confirm", { method: "POST", body: { tier } }),
};

// Download the exported .xlsx WITH the auth header, then trigger a save.
// (A plain <a href> can't send the bearer token, so the server 401s.)
export async function downloadExport(id, filename = `responses_${id}.xlsx`, original = false) {
  const token = getToken();
  const qs = original ? "?original=true" : "";
  const res = await fetch(`${BASE}/v1/questionnaires/${id}/export${qs}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
