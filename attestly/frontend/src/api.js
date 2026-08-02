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
  signup: (name, email) => req("/v1/signup", { method: "POST", body: { name, email } }),
  me: () => req("/v1/me"),
  answers: () => req("/v1/answers"),
  addAnswer: (a) => req("/v1/answers", { method: "POST", body: a }),
  bulkAnswers: (answers) => req("/v1/answers/bulk", { method: "POST", body: { answers } }),
  listQuestionnaires: () => req("/v1/questionnaires"),
  getQuestionnaire: (id) => req(`/v1/questionnaires/${id}`),
  uploadQuestionnaire: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return req("/v1/questionnaires", { method: "POST", body: fd, isForm: true });
  },
  approveItem: (id, answer) => req(`/v1/items/${id}/approve`, { method: "POST", body: { answer } }),
  exportUrl: (id) => `${BASE}/v1/questionnaires/${id}/export`,
  checkout: (tier) => req("/v1/billing/checkout", { method: "POST", body: { tier } }),
  confirm: (tier) => req("/v1/billing/confirm", { method: "POST", body: { tier } }),
};
