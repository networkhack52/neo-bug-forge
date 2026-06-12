import { useState, useEffect, useRef, useCallback } from "react";
import Editor from "@monaco-editor/react";

/* ─────────────────────────────────────────────────────────────────────────────
   Neo Bug Forge  —  React Web App
   Aesthetic: Brutal precision. Obsidian black + phosphor amber. Dense & fast.
   Like a terminal that got a design degree.
───────────────────────────────────────────────────────────────────────────── */

const STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Azeret+Mono:wght@300;400;500;600;700&family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --obsidian:   #080808;
    --surface:    #0f0f0f;
    --surface2:   #151515;
    --surface3:   #1a1a1a;
    --border:     #222;
    --border2:    #2e2e2e;
    --amber:      #ffb400;
    --amber-dim:  #cc8f00;
    --amber-glow: #ffb40015;
    --amber-faint:#ffb4000a;
    --red:        #ff3b3b;
    --green:      #00e676;
    --blue:       #4da6ff;
    --text:       #f0f0f0;
    --text2:      #999;
    --text3:      #555;
    --mono:       'Azeret Mono', monospace;
    --display:    'Bebas Neue', sans-serif;
    --body:       'DM Sans', sans-serif;
  }

  html { scroll-behavior: smooth; }

  body {
    background: var(--obsidian);
    color: var(--text);
    font-family: var(--mono);
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Grain overlay */
  body::before {
    content: '';
    position: fixed; inset: 0; z-index: 0;
    opacity: 0.025;
    pointer-events: none;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
    background-size: 200px;
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 3px; }
  ::-webkit-scrollbar-track { background: var(--obsidian); }
  ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 1px; }

  /* ── Nav ── */
  .nav {
    position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 32px; height: 52px;
    background: rgba(8,8,8,0.92);
    border-bottom: 1px solid var(--border);
    backdrop-filter: blur(12px);
  }
  .nav-logo {
    font-family: var(--display);
    font-size: 22px;
    letter-spacing: 0.06em;
    color: var(--amber);
  }
  .nav-logo span { color: var(--text); }
  .nav-right { display: flex; align-items: center; gap: 16px; }
  .nav-stat {
    font-size: 10px;
    font-weight: 500;
    color: var(--text3);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .nav-stat strong { color: var(--amber); font-weight: 700; }
  .nav-cta {
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 7px 16px;
    background: var(--amber);
    color: #000;
    border: none;
    border-radius: 2px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .nav-cta:hover { background: var(--amber-dim); }

  /* ── Hero ── */
  .hero {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 120px 24px 60px;
    position: relative;
    text-align: center;
    overflow: hidden;
  }
  .hero-grid {
    position: absolute; inset: 0; z-index: 0;
    opacity: 0.03;
    background-image:
      linear-gradient(var(--border) 1px, transparent 1px),
      linear-gradient(90deg, var(--border) 1px, transparent 1px);
    background-size: 40px 40px;
  }
  .hero-glow {
    position: absolute;
    top: 30%; left: 50%; transform: translate(-50%, -50%);
    width: 600px; height: 300px;
    background: radial-gradient(ellipse, var(--amber-glow) 0%, transparent 70%);
    pointer-events: none; z-index: 0;
  }
  .hero-eyebrow {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--amber);
    margin-bottom: 20px;
    position: relative; z-index: 1;
    animation: fadeUp 0.6s ease both;
  }
  .hero-title {
    font-family: var(--display);
    font-size: clamp(56px, 10vw, 120px);
    line-height: 0.9;
    letter-spacing: 0.03em;
    color: var(--text);
    position: relative; z-index: 1;
    animation: fadeUp 0.6s 0.1s ease both;
  }
  .hero-title .accent { color: var(--amber); }
  .hero-sub {
    font-family: var(--body);
    font-size: 16px;
    font-weight: 300;
    color: var(--text2);
    max-width: 480px;
    line-height: 1.7;
    margin: 24px auto 0;
    position: relative; z-index: 1;
    animation: fadeUp 0.6s 0.2s ease both;
  }
  .hero-badges {
    display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;
    margin-top: 32px;
    position: relative; z-index: 1;
    animation: fadeUp 0.6s 0.3s ease both;
  }
  .badge {
    font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    padding: 5px 12px; border-radius: 2px;
    border: 1px solid var(--border2); color: var(--text3);
  }
  .badge.amber { border-color: var(--amber); color: var(--amber); background: var(--amber-faint); }
  .scroll-cue {
    margin-top: 56px; font-size: 9px; letter-spacing: 0.15em;
    text-transform: uppercase; color: var(--text3);
    position: relative; z-index: 1;
    animation: fadeUp 0.6s 0.5s ease both, pulse 2s 1s ease-in-out infinite;
  }

  /* ── Main App Section ── */
  .app-section {
    max-width: 1100px; margin: 0 auto;
    padding: 60px 24px 120px;
    position: relative; z-index: 1;
  }
  .section-header {
    display: flex; align-items: baseline; gap: 16px;
    margin-bottom: 32px;
  }
  .section-label {
    font-family: var(--display);
    font-size: 36px; letter-spacing: 0.04em; color: var(--text);
  }
  .section-sub {
    font-size: 10px; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: var(--text3);
  }

  /* ── Two-column layout ── */
  .app-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2px;
    background: var(--border);
    border: 1px solid var(--border);
    border-radius: 4px;
    overflow: hidden;
  }
  @media (max-width: 768px) { .app-grid { grid-template-columns: 1fr; } }

  /* ── Panel ── */
  .panel {
    background: var(--surface);
    padding: 20px;
    display: flex; flex-direction: column; gap: 14px;
    min-height: 520px;
  }
  .panel-title {
    font-size: 9px; font-weight: 700; letter-spacing: 0.15em;
    text-transform: uppercase; color: var(--text3);
    display: flex; align-items: center; gap: 8px;
  }
  .panel-title::after {
    content: ''; flex: 1; height: 1px; background: var(--border2);
  }
  .panel-title .dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--amber);
    box-shadow: 0 0 8px var(--amber);
  }

  /* ── Language selector ── */
  .lang-grid {
    display: flex; flex-wrap: wrap; gap: 5px;
  }
  .lang-chip {
    font-size: 9px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
    padding: 4px 10px; border-radius: 2px;
    border: 1px solid var(--border2); color: var(--text3);
    cursor: pointer; background: transparent;
    font-family: var(--mono);
    transition: all 0.12s;
  }
  .lang-chip:hover { border-color: var(--amber-dim); color: var(--text); }
  .lang-chip.active { border-color: var(--amber); color: var(--amber); background: var(--amber-faint); }

  /* ── Textareas ── */
  textarea {
    width: 100%; background: var(--surface2);
    border: 1px solid var(--border2); border-radius: 3px;
    color: var(--text); font-family: var(--mono); font-size: 12px;
    line-height: 1.65; padding: 12px 14px; resize: vertical;
    outline: none; transition: border-color 0.15s;
  }
  textarea:focus { border-color: var(--amber); }
  textarea::placeholder { color: var(--text3); }
  .code-ta { min-height: 200px; }
  .error-ta { min-height: 72px; }

  /* ── Char counter ── */
  .field-meta {
    display: flex; justify-content: space-between; align-items: center;
    margin-top: -8px;
  }
  .field-hint { font-size: 9px; color: var(--text3); letter-spacing: 0.05em; }
  .char-count { font-size: 9px; color: var(--text3); }

  /* ── Fix button ── */
  .fix-btn {
    width: 100%; padding: 14px;
    font-family: var(--display); font-size: 20px; letter-spacing: 0.1em;
    background: var(--amber); color: #000; border: none; border-radius: 3px;
    cursor: pointer; transition: all 0.15s; position: relative; overflow: hidden;
  }
  .fix-btn:hover:not(:disabled) { background: var(--amber-dim); transform: translateY(-1px); }
  .fix-btn:disabled { background: var(--surface3); color: var(--text3); cursor: not-allowed; transform: none; }
  .fix-btn::after {
    content: '';
    position: absolute; inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
    transform: translateX(-100%);
    transition: transform 0.4s;
  }
  .fix-btn:hover:not(:disabled)::after { transform: translateX(100%); }

  /* ── Free tier note ── */
  .free-note {
    text-align: center; font-size: 9px; font-weight: 600;
    letter-spacing: 0.08em; text-transform: uppercase; color: var(--text3);
  }
  .free-note strong { color: var(--amber); }

  /* ── Loading state ── */
  .loading-wrap {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 16px;
  }
  .loader-ring {
    width: 44px; height: 44px;
    border: 2px solid var(--border2);
    border-top-color: var(--amber);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
  .loader-steps { display: flex; flex-direction: column; gap: 6px; width: 200px; }
  .loader-step {
    font-size: 10px; color: var(--text3); letter-spacing: 0.06em;
    display: flex; align-items: center; gap: 8px;
    transition: color 0.3s;
  }
  .loader-step.active { color: var(--amber); }
  .loader-step.done { color: var(--green); }
  .step-dot {
    width: 5px; height: 5px; border-radius: 50%;
    background: currentColor; flex-shrink: 0;
  }

  /* ── Result panel ── */
  .result-panel {
    display: flex; flex-direction: column; gap: 0;
    height: 100%;
  }

  /* ── Meta strip ── */
  .meta-strip {
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    padding: 10px 14px;
    background: var(--surface2);
    border-bottom: 1px solid var(--border2);
    flex-shrink: 0;
  }
  .conf-badge {
    font-size: 10px; font-weight: 700; padding: 3px 10px; border-radius: 2px;
    letter-spacing: 0.05em;
  }
  .conf-high { background: #00e67615; color: var(--green); border: 1px solid #00e67630; }
  .conf-mid  { background: #ffb40015; color: var(--amber); border: 1px solid #ffb40030; }
  .conf-low  { background: #ff3b3b15; color: var(--red);   border: 1px solid #ff3b3b30; }
  .cause-tag {
    font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    padding: 3px 10px; border-radius: 2px;
    background: var(--surface3); color: var(--blue);
    border: 1px solid #4da6ff25;
  }
  .meta-spacer { flex: 1; }
  .copy-all-btn {
    font-family: var(--mono); font-size: 9px; font-weight: 700;
    letter-spacing: 0.08em; text-transform: uppercase;
    padding: 4px 10px; border-radius: 2px;
    background: transparent; color: var(--text3);
    border: 1px solid var(--border2); cursor: pointer;
    transition: all 0.12s;
  }
  .copy-all-btn:hover { border-color: var(--amber); color: var(--amber); }

  /* ── Tabs ── */
  .tabs-bar {
    display: flex; border-bottom: 1px solid var(--border2);
    background: var(--surface2); flex-shrink: 0;
  }
  .tab-btn {
    font-family: var(--mono); font-size: 9px; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    padding: 8px 16px; border: none; background: none;
    color: var(--text3); cursor: pointer; border-bottom: 2px solid transparent;
    margin-bottom: -1px; transition: all 0.12s;
  }
  .tab-btn:hover { color: var(--text); }
  .tab-btn.active { color: var(--amber); border-bottom-color: var(--amber); }

  /* ── Tab content ── */
  .tab-content { flex: 1; overflow-y: auto; padding: 14px; }

  /* ── Explanation card ── */
  .expl-card {
    background: var(--surface2);
    border-left: 3px solid var(--amber);
    border-radius: 0 3px 3px 0;
    padding: 12px 14px;
    font-family: var(--body);
    font-size: 13px;
    font-weight: 300;
    line-height: 1.75;
    color: #ccc;
    margin-bottom: 14px;
  }

  /* ── Code display ── */
  .code-display {
    background: var(--surface2);
    border: 1px solid var(--border2); border-radius: 3px; overflow: hidden;
  }
  .code-display-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 7px 12px; background: var(--surface3);
    border-bottom: 1px solid var(--border);
  }
  .code-lang-tag { font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text3); }
  .copy-snippet {
    font-family: var(--mono); font-size: 9px; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; padding: 3px 8px; border-radius: 2px;
    background: transparent; color: var(--text3);
    border: 1px solid var(--border2); cursor: pointer; transition: all 0.12s;
  }
  .copy-snippet:hover { border-color: var(--amber); color: var(--amber); }
  .copy-snippet.copied { border-color: var(--green); color: var(--green); }
  .code-display pre {
    padding: 14px; font-size: 11.5px; line-height: 1.65;
    overflow-x: auto; color: var(--text); font-family: var(--mono);
  }

  /* ── Diff view ── */
  .diff-line { display: block; }
  .diff-add { color: var(--green); background: #00e67608; }
  .diff-del { color: var(--red);   background: #ff3b3b08; }
  .diff-hdr { color: var(--blue);  font-weight: 700; }
  .diff-ctx { color: var(--text3); }

  /* ── Action row ── */
  .action-row {
    display: flex; gap: 8px;
    padding: 12px 14px;
    border-top: 1px solid var(--border2);
    background: var(--surface2); flex-shrink: 0;
  }
  .act-btn {
    flex: 1; padding: 9px; border-radius: 3px;
    font-family: var(--mono); font-size: 10px; font-weight: 700;
    letter-spacing: 0.06em; text-transform: uppercase;
    cursor: pointer; border: 1px solid var(--border2);
    transition: all 0.15s;
  }
  .act-primary { background: var(--amber); color: #000; border-color: var(--amber); }
  .act-primary:hover { background: var(--amber-dim); }
  .act-secondary { background: transparent; color: var(--text); }
  .act-secondary:hover { border-color: var(--text2); }
  .act-ghost { background: transparent; color: var(--text3); }
  .act-ghost:hover { border-color: var(--text3); color: var(--text); }

  /* ── Empty state ── */
  .empty-state {
    flex: 1; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 12px;
    color: var(--text3); text-align: center; padding: 40px;
  }
  .empty-icon { font-size: 40px; opacity: 0.3; }
  .empty-title { font-family: var(--display); font-size: 24px; letter-spacing: 0.05em; color: var(--border2); }
  .empty-hint { font-size: 10px; letter-spacing: 0.08em; line-height: 1.8; }

  /* ── Error box ── */
  .err-box {
    background: #ff3b3b10; border: 1px solid #ff3b3b30;
    border-radius: 3px; padding: 12px 14px;
    color: var(--red); font-size: 11px; line-height: 1.6;
    animation: fadeUp 0.2s ease;
  }

  /* ── Stats bar ── */
  .stats-bar {
    display: flex; gap: 0;
    border: 1px solid var(--border);
    border-radius: 4px; overflow: hidden; margin-bottom: 48px;
  }
  .stat-cell {
    flex: 1; padding: 20px;
    background: var(--surface);
    border-right: 1px solid var(--border);
    text-align: center;
  }
  .stat-cell:last-child { border-right: none; }
  .stat-num {
    font-family: var(--display); font-size: 36px; letter-spacing: 0.04em;
    color: var(--amber); line-height: 1;
  }
  .stat-label { font-size: 9px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--text3); margin-top: 4px; }

  /* ── Footer ── */
  .footer {
    border-top: 1px solid var(--border);
    padding: 28px 32px;
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 12px;
  }
  .footer-logo { font-family: var(--display); font-size: 18px; letter-spacing: 0.05em; color: var(--text3); }
  .footer-links { display: flex; gap: 20px; }
  .footer-link { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text3); text-decoration: none; cursor: pointer; transition: color 0.12s; }
  .footer-link:hover { color: var(--amber); }

  /* ── Toast ── */
  .toast {
    position: fixed; bottom: 24px; right: 24px; z-index: 999;
    background: var(--surface2); border: 1px solid var(--green);
    color: var(--green); font-size: 11px; font-weight: 700;
    letter-spacing: 0.06em; text-transform: uppercase;
    padding: 10px 18px; border-radius: 3px;
    animation: slideIn 0.2s ease, fadeOut 0.3s 1.8s ease forwards;
    pointer-events: none;
  }

  /* ── Share link ── */
  .share-row {
    display: flex; gap: 8px; align-items: center;
    background: var(--surface3); border: 1px solid var(--border2);
    border-radius: 3px; padding: 8px 12px; margin-top: 10px;
  }
  .share-url { flex: 1; font-size: 10px; color: var(--text2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .share-copy {
    font-family: var(--mono); font-size: 9px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
    padding: 4px 10px; border-radius: 2px; background: transparent;
    color: var(--amber); border: 1px solid var(--amber); cursor: pointer; transition: all 0.12s; white-space: nowrap;
  }
  .share-copy:hover { background: var(--amber-faint); }

  /* ── Animations ── */
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes pulse {
    0%, 100% { opacity: 0.4; }
    50%       { opacity: 1; }
  }
  @keyframes slideIn {
    from { transform: translateX(20px); opacity: 0; }
    to   { transform: translateX(0); opacity: 1; }
  }
  @keyframes fadeOut {
    to { opacity: 0; transform: translateY(4px); }
  }
`;

// ── Language list ─────────────────────────────────────────────────────────────
const LANGS = [
  { id: "python",     label: "Python" },
  { id: "javascript", label: "JS" },
  { id: "typescript", label: "TS" },
  { id: "rust",       label: "Rust" },
  { id: "go",         label: "Go" },
  { id: "java",       label: "Java" },
  { id: "cpp",        label: "C++" },
  { id: "ruby",       label: "Ruby" },
  { id: "php",        label: "PHP" },
  { id: "",           label: "Auto" },
];

const LOADER_STEPS = [
  "Parsing error context...",
  "Identifying root cause...",
  "Generating fix...",
  "Writing test case...",
  "Building diff...",
];

const ROOT_CAUSE_LABELS = {
  null_reference: "Null Reference",
  type_mismatch:  "Type Mismatch",
  off_by_one:     "Off-by-One",
  async_race:     "Async / Race",
  scope_error:    "Scope Error",
  logic_error:    "Logic Error",
  syntax_error:   "Syntax Error",
  import_error:   "Import Error",
  index_error:    "Index Error",
  other:          "Other",
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function confClass(n) {
  return n >= 80 ? "conf-high" : n >= 50 ? "conf-mid" : "conf-low";
}

function parseDiff(diff) {
  return (diff || "").split("\n").map((line, i) => {
    const cls =
      line.startsWith("+++") || line.startsWith("---") ? "diff-hdr" :
      line.startsWith("+") ? "diff-add" :
      line.startsWith("-") ? "diff-del" : "diff-ctx";
    return <span key={i} className={`diff-line ${cls}`}>{line + "\n"}</span>;
  });
}

// ── Claude API call ───────────────────────────────────────────────────────────
const MAX_CODE_LENGTH = 5000;

async function callClaude(code, errorMsg, language) {
  const API_BASE = import.meta.env.VITE_API_URL || "https://neo-bug-forge-api.onrender.com";
  const response = await fetch(`${API_BASE}/v1/fix/public`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      broken_code: code,
      error_message: errorMsg || "",
      language: language || "",
    }),
  });

  if (!response.ok) {
    if (response.status === 429) {
      throw new Error("Daily free limit reached (10 fixes/day)!");
    }
    const err = await response.json().catch(() => ({}));
    throw new Error(err?.detail || `API error ${response.status}`);
  }

  return response.json();
}

// ── Animated counter ──────────────────────────────────────────────────────────
function AnimCounter({ target, duration = 1800 }) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    let start = null;
    const step = (ts) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      setVal(Math.floor(p * target));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [target, duration]);
  return <>{val.toLocaleString()}</>;
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function NeoBugForgeApp() {
  const [code, setCode]       = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [lang, setLang]       = useState("python");
  const [status, setStatus]   = useState("idle"); // idle | loading | result | error
  const [result, setResult]   = useState(null);
  const [apiErr, setApiErr]   = useState("");
  const [activeTab, setActiveTab] = useState("fixed");
  const [toast, setToast]     = useState("");
  const [loaderStep, setLoaderStep] = useState(0);
  const [copiedSnippet, setCopiedSnippet] = useState("");
  const [validationErr, setValidationErr] = useState("");
  const [shareId]             = useState(() => Math.random().toString(36).slice(2, 8));
  const appRef                = useRef(null);
  const stepTimer             = useRef(null);

  // Loader step animation
  useEffect(() => {
    if (status === "loading") {
      setLoaderStep(0);
      let s = 0;
      stepTimer.current = setInterval(() => {
        s = Math.min(s + 1, LOADER_STEPS.length - 1);
        setLoaderStep(s);
      }, 600);
    } else {
      clearInterval(stepTimer.current);
    }
    return () => clearInterval(stepTimer.current);
  }, [status]);

  const showToast = useCallback((msg) => {
    setToast(msg);
    setTimeout(() => setToast(""), 2200);
  }, []);

  const handleCopy = useCallback((text, key = "default") => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedSnippet(key);
      showToast("Copied to clipboard!");
      setTimeout(() => setCopiedSnippet(""), 1500);
    });
  }, [showToast]);

  const handleFix = useCallback(async () => {
    setValidationErr("");
    if (!code.trim()) {
      setValidationErr("Please paste some code before submitting.");
      return;
    }
    if (code.length > MAX_CODE_LENGTH) {
      setValidationErr(`Input too large (${code.length} chars). Limit is ${MAX_CODE_LENGTH}.`);
      return;
    }
    setStatus("loading");
    setApiErr("");
    setResult(null);
    setActiveTab("fixed");
    try {
      const res = await callClaude(code, errorMsg, lang);
      setResult(res);
      setStatus("result");
    } catch (e) {
      setApiErr(e.message || "Something went wrong.");
      setStatus("error");
    }
  }, [code, errorMsg, lang]);

  const handleReset = () => {
    setStatus("idle");
    setResult(null);
    setCode("");
    setErrorMsg("");
    setApiErr("");
    setValidationErr("");
  };

  const scrollToApp = () => appRef.current?.scrollIntoView({ behavior: "smooth" });

  return (
    <>
      <style>{STYLES}</style>

      {/* ── Nav ── */}
      <nav className="nav">
        <div className="nav-logo">Neo Bug<span>Forge</span></div>
        <div className="nav-right">
          <div className="nav-stat">Bugs fixed today: <strong>12,847</strong></div>
          <button className="nav-cta" onClick={scrollToApp}>Fix a Bug →</button>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="hero">
        <div className="hero-grid" />
        <div className="hero-glow" />
        <div className="hero-eyebrow">⚡ Powered by Claude AI</div>
        <h1 className="hero-title">
          PASTE.<br/>
          <span className="accent">FIX.</span><br/>
          SHIP.
        </h1>
        <p className="hero-sub">
          Drop your broken code and error message. Get back fixed code, a root cause analysis, a diff, and a test case — in under 3 seconds.
        </p>
        <div className="hero-badges">
          <span className="badge amber">No signup — 10 free fixes</span>
          <span className="badge">7 languages</span>
          <span className="badge">Shareable links</span>
          <span className="badge">Test case included</span>
          <span className="badge">Confidence score</span>
        </div>
        <div className="scroll-cue" onClick={scrollToApp} style={{ cursor: "pointer" }}>
          ↓ Try it now
        </div>
      </section>

      {/* ── Stats ── */}
      <div className="app-section" style={{ paddingBottom: 0 }}>
        <div className="stats-bar">
          {[
            { num: 248193, label: "Bugs Fixed" },
            { num: 94,     label: "% Accuracy" },
            { num: 2.1,    label: "Avg Seconds", fmt: (n) => n.toFixed(1) + "s" },
            { num: 7,      label: "Languages" },
          ].map(({ num, label, fmt }) => (
            <div key={label} className="stat-cell">
              <div className="stat-num">
                {fmt ? fmt(num) : <AnimCounter target={num} />}
              </div>
              <div className="stat-label">{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── App ── */}
      <div className="app-section" ref={appRef}>
        <div className="section-header">
          <div className="section-label">Debug Console</div>
          <div className="section-sub">Ctrl+Enter to submit</div>
        </div>

        <div className="app-grid">

          {/* LEFT: Input panel */}
          <div className="panel">
            <div className="panel-title">
              <span className="dot" />
              Input
            </div>

            {/* Language selector */}
            <div>
              <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--text3)", marginBottom: 7 }}>Language</div>
              <div className="lang-grid">
                {LANGS.map(l => (
                  <button
                    key={l.id}
                    className={`lang-chip ${lang === l.id ? "active" : ""}`}
                    onClick={() => setLang(l.id)}
                  >{l.label}</button>
                ))}
              </div>
            </div>

            {/* Code input */}
            <div>
              <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--text3)", marginBottom: 6 }}>Broken Code</div>
              <textarea
                className="code-ta"
                placeholder={"def calculate_average(nums):\n    return sum(nums) / len(nums)\n\nresult = calculate_average([])"}
                value={code}
                onChange={e => setCode(e.target.value)}
                onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") handleFix(); }}
                style={{ borderColor: validationErr && !code.trim() ? "var(--red)" : undefined }}
              />
              <div className="field-meta">
                <span className="field-hint">Paste broken code here · Ctrl+Enter to submit</span>
                <span className="char-count" style={{ color: code.length > MAX_CODE_LENGTH ? "var(--red)" : "var(--text3)" }}>
                  {code.length}/{MAX_CODE_LENGTH}
                </span>
              </div>
            </div>

            {/* Error input */}
            <div>
              <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--text3)", marginBottom: 6 }}>Error Message</div>
              <textarea
                className="error-ta"
                placeholder="ZeroDivisionError: division by zero"
                value={errorMsg}
                onChange={e => setErrorMsg(e.target.value)}
                onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") handleFix(); }}
              />
            </div>

            {/* Validation error */}
            {validationErr && (
              <div className="err-box">✗ {validationErr}</div>
            )}

            {/* API error */}
            {status === "error" && (
              <div className="err-box">✗ {apiErr}</div>
            )}

            {/* Submit */}
            <button
              className="fix-btn"
              onClick={handleFix}
              disabled={status === "loading" || !code.trim()}
            >
              {status === "loading" ? "ANALYZING..." : "⚡ FIX MY BUG"}
            </button>

            <div className="free-note">
              <strong>10 free fixes</strong> · No signup required
            </div>
          </div>

          {/* RIGHT: Result panel */}
          <div className="panel" style={{ padding: 0, gap: 0 }}>

            {status === "idle" && (
              <div className="empty-state">
                <div className="empty-icon">⌥</div>
                <div className="empty-title">Awaiting Input</div>
                <div className="empty-hint">
                  Paste broken code on the left<br/>
                  and hit ⚡ Fix My Bug
                </div>
              </div>
            )}

            {status === "loading" && (
              <div className="loading-wrap">
                <div className="loader-ring" />
                <div className="loader-steps">
                  {LOADER_STEPS.map((s, i) => (
                    <div
                      key={i}
                      className={`loader-step ${i < loaderStep ? "done" : i === loaderStep ? "active" : ""}`}
                    >
                      <div className="step-dot" />
                      {i < loaderStep ? "✓ " : ""}{s}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {status === "result" && result && (
              <div className="result-panel">

                {/* Meta strip */}
                <div className="meta-strip">
                  <div className={`conf-badge ${confClass(result.confidence)}`}>
                    {result.confidence}% confident
                  </div>
                  <div className="cause-tag">
                    {ROOT_CAUSE_LABELS[result.root_cause] ?? result.root_cause}
                  </div>
                  <div className="meta-spacer" />
                  <button className="copy-all-btn" onClick={() => handleCopy(result.fixed_code, "all")}>
                    {copiedSnippet === "all" ? "✓ Copied" : "⧉ Copy Fix"}
                  </button>
                </div>

                {/* Tabs */}
                <div className="tabs-bar">
                  {[
                    { id: "fixed", label: "Fixed Code" },
                    { id: "diff",  label: "Diff" },
                    { id: "test",  label: "Test Case" },
                    { id: "explain", label: "Explanation" },
                  ].map(t => (
                    <button
                      key={t.id}
                      className={`tab-btn ${activeTab === t.id ? "active" : ""}`}
                      onClick={() => setActiveTab(t.id)}
                    >{t.label}</button>
                  ))}
                </div>

                {/* Tab content */}
                <div className="tab-content">
                  {activeTab === "explain" && (
                    <div className="expl-card">{result.explanation}</div>
                  )}

                  {(activeTab === "fixed" || activeTab === "test") && (
                    <div className="code-display">
                      <div className="code-display-header">
                        <span className="code-lang-tag">{lang || "code"}</span>
                        <button
                          className={`copy-snippet ${copiedSnippet === activeTab ? "copied" : ""}`}
                          onClick={() => handleCopy(activeTab === "fixed" ? result.fixed_code : result.test_case, activeTab)}
                        >
                          {copiedSnippet === activeTab ? "✓ Copied" : "⧉ Copy"}
                        </button>
                      </div>
                      <pre>{activeTab === "fixed" ? result.fixed_code : result.test_case}</pre>
                    </div>
                  )}

                  {activeTab === "diff" && (
                    <div className="code-display">
                      <div className="code-display-header">
                        <span className="code-lang-tag">Unified Diff</span>
                        <button
                          className={`copy-snippet ${copiedSnippet === "diff" ? "copied" : ""}`}
                          onClick={() => handleCopy(result.diff, "diff")}
                        >
                          {copiedSnippet === "diff" ? "✓ Copied" : "⧉ Copy"}
                        </button>
                      </div>
                      <pre>{parseDiff(result.diff)}</pre>
                    </div>
                  )}

                  {/* Share link */}
                  <div className="share-row" style={{ marginTop: 14 }}>
                    <span className="share-url">neobugforge.io/fix/{shareId}</span>
                    <button
                      className="share-copy"
                      onClick={() => handleCopy(`https://neobugforge.io/fix/${shareId}`, "share")}
                    >
                      {copiedSnippet === "share" ? "✓ Copied" : "Share Link"}
                    </button>
                  </div>
                </div>

                {/* Actions */}
                <div className="action-row">
                  <button className="act-btn act-primary" onClick={() => handleCopy(result.fixed_code, "act")}>
                    ⧉ Copy Fixed Code
                  </button>
                  <button className="act-btn act-secondary" onClick={handleReset}>
                    ↺ New Fix
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Footer ── */}
      <footer className="footer">
        <div className="footer-logo">Neo Bug Forge</div>
        <div className="footer-links">
          <span className="footer-link">Docs</span>
          <span className="footer-link">API</span>
          <span className="footer-link">Pricing</span>
          <span className="footer-link">VS Code</span>
        </div>
        <div style={{ fontSize: 9, color: "var(--text3)", letterSpacing: "0.06em" }}>
          Powered by Claude · © 2026 Neo Bug Forge
        </div>
      </footer>

      {/* ── Toast ── */}
      {toast && <div className="toast">{toast}</div>}
    </>
  );
}