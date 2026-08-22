import React, { useEffect, useState } from "react";
import { api, getToken, setToken, clearToken, downloadExport } from "./api.js";

// Citations are stored as a JSON string in the DB; accept either form.
function parseCitations(c) {
  if (Array.isArray(c)) return c;
  try {
    const p = JSON.parse(c || "[]");
    return Array.isArray(p) ? p : [];
  } catch (_) {
    return [];
  }
}

// Epoch seconds -> YYYY-MM-DD (a document's source date).
function fmtEpoch(epoch) {
  if (!epoch) return "";
  return new Date(epoch * 1000).toISOString().slice(0, 10);
}
// A source is stale when it's older than 12 months.
function docStale(epoch) {
  if (!epoch) return false;
  return Date.now() / 1000 - epoch > 365 * 86400;
}

// Rows that can't export yet (mirrors the server gate): a bare "No" needs a
// remediation date or an explicit no-plan; an "N/A" needs a reason.
function gateIssues(items) {
  return (items || []).filter((it) => {
    if (it.locked) return false;
    const choice = (it.choice || "").trim();
    if (it.excluded) return !(it.exclusion_reason || "").trim();
    if (choice === "No") return !(it.remediation_date || "").trim() && !it.no_plan;
    if (choice === "Not Applicable") return !(it.na_reason || "").trim();
    return false;
  });
}

// "Open 3d", "Open 5h": how long a questionnaire has been sitting.
function openFor(createdAtEpoch) {
  const hrs = (Date.now() / 1000 - createdAtEpoch) / 3600;
  if (hrs < 1) return { label: "Open <1h", hours: hrs };
  if (hrs < 48) return { label: `Open ${Math.round(hrs)}h`, hours: hrs };
  return { label: `Open ${Math.round(hrs / 24)}d`, hours: hrs };
}

export default function App() {
  const [me, setMe] = useState(null);
  const [tab, setTab] = useState("upload");
  const [loading, setLoading] = useState(true);
  const [showAuth, setShowAuth] = useState(false); // logged-out: land on the pitch first

  async function refresh() {
    if (!getToken()) {
      setMe(null);
      setLoading(false);
      return;
    }
    try {
      setMe(await api.me());
    } catch (_) {
      clearToken();
      setMe(null);
    }
    setLoading(false);
  }
  useEffect(() => {
    refresh();
  }, []);

  if (loading) return <div className="center muted">Loading…</div>;
  // A password-reset link (?reset=<token>) takes precedence over everything.
  // The user may be logged out, or logged in on a different device.
  const resetToken = new URLSearchParams(window.location.search).get("reset");
  if (resetToken) return <ResetPassword token={resetToken} onDone={refresh} />;
  if (!me)
    return showAuth ? (
      <Onboarding onDone={refresh} onBack={() => setShowAuth(false)} />
    ) : (
      <Landing onStart={() => setShowAuth(true)} />
    );

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">◆</span> Attestly
        </div>
        <div className="usage">
          <span className="pill">{me.tier_name}</span>
          <span className="muted">
            {me.questions_used}/{me.question_limit} answers · Library {me.bank_size}
          </span>
          <button
            className="link"
            onClick={() => {
              clearToken();
              setMe(null);
            }}
          >
            Sign out
          </button>
        </div>
      </header>

      <nav className="tabs">
        {[
          ["upload", "Answer a questionnaire"],
          ["bank", "Answer Library"],
          ["documents", "Trust Documents"],
          ["history", "History"],
          ["billing", "Plan & Billing"],
        ].map(([k, label]) => (
          <button key={k} className={tab === k ? "tab active" : "tab"} onClick={() => setTab(k)}>
            {label}
          </button>
        ))}
      </nav>

      <main className="content">
        {tab === "upload" && <Upload me={me} onChange={refresh} onNavigate={setTab} />}
        {tab === "bank" && <Bank me={me} onChange={refresh} />}
        {tab === "documents" && <Documents />}
        {tab === "history" && <History />}
        {tab === "billing" && <Billing me={me} onChange={refresh} />}
      </main>
    </div>
  );
}

function Landing({ onStart }) {
  return (
    <div className="lp">
      <header className="lp-nav">
        <div className="lp-brand"><span className="lp-mark">◆</span> Attestly</div>
        <div className="lp-navcta">
          <button className="lp-ghost" onClick={onStart}>Log in</button>
          <button className="lp-btn" onClick={onStart}>Start free</button>
        </div>
      </header>

      <section className="lp-hero">
        <div>
          <div className="lp-eyebrow">Security questionnaires · with receipts</div>
          <h1 className="lp-h1">Answer security questionnaires in minutes. And prove every answer.</h1>
          <p className="lp-lede">
            Attestly drafts each answer from your own SOC&nbsp;2 and security policies, cites the exact
            source, and reuses your approved answers so every questionnaire gets faster.
          </p>
          <div className="lp-cta-row">
            <button className="lp-btn lp-big" onClick={onStart}>Start free · 150 answers, no card</button>
            <a className="lp-ghost lp-big" href="#how">See how it works</a>
          </div>
          <div className="lp-assure">150 free answers · no credit card · no sales demo</div>
          <div className="lp-formats">
            <span className="lp-lbl">Works with</span>
            <span>SIG</span><span>CAIQ</span><span>VSAQ</span><span>Custom .xlsx / .csv</span>
          </div>
        </div>

        <div className="lp-device" aria-hidden="true">
          <div className="lp-chrome"><i></i><i></i><i></i><span className="lp-url">🔒 tryattestly.com/review</span></div>
          <div className="lp-app">
            <div className="lp-card lp-dim">
              <div className="lp-chips"><span className="lp-chip yes">Yes</span><span className="lp-chip ver">✓ Verified</span></div>
              <div className="lp-q">Is customer data encrypted at rest?</div>
              <div className="lp-a">Yes. All customer data is encrypted at rest using AES-256, including databases, backups, and object storage.</div>
            </div>
            <div className="lp-card">
              <div className="lp-chips"><span className="lp-chip yes">Yes</span><span className="lp-chip blue">AI draft</span><span className="lp-chip ver">✓ Verified</span></div>
              <div className="lp-q">Is access granted on least privilege?</div>
              <div className="lp-a">We grant access on a least-privilege basis using role-based access control, reviewed quarterly.</div>
              <span className="lp-proof">🔍 2 sources · show proof</span>
            </div>
            <div className="lp-drawer">
              <div className="lp-kick">Grounded in your sources</div>
              <div className="lp-dt">Proof of answer</div>
              <div className="lp-sub">Source · document</div>
              <div className="lp-src">
                <span className="lp-frm">📄 Acme_Information_Security_Policy.pdf</span>
                <span className="lp-qt">“Access is granted on the principle of least privilege using role-based access control (RBAC)…”</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="lp-eval">
        <div className="lp-eval-num">35/35</div>
        <div>
          <strong>It catches the near-miss traps.</strong> We tested Attestly on 35 questions where the
          evidence is close but wrong: a wrong date, a wrong key size, a flipped yes/no. It confirmed
          none of them, and kept false confidence under 1% across 150 questions. When your documents
          don't cover something, it says so instead of guessing.
        </div>
      </section>

      <section id="how" className="lp-section">
        <h2 className="lp-h2">Upload, review, done.</h2>
        <p className="lp-sec-sub">No integration. No onboarding call. Three steps from a blank questionnaire to a filled one you can send.</p>
        <div className="lp-steps">
          <div className="lp-step"><div className="lp-n">01</div><h3>Upload the questionnaire</h3><p>SIG, CAIQ, VSAQ, or a custom .xlsx/.csv. We auto-detect the questions.</p></div>
          <div className="lp-step"><div className="lp-n">02</div><h3>Attestly answers each one</h3><p>Reused from your library or drafted from your SOC&nbsp;2 and policies, each with the exact source cited.</p></div>
          <div className="lp-step"><div className="lp-n">03</div><h3>Review &amp; download</h3><p>Get your own template back, filled in, with a Source and Status on every row.</p></div>
        </div>
      </section>

      <section className="lp-section lp-alt">
        <h2 className="lp-h2">Start free. Upgrade when it pays for itself.</h2>
        <div className="lp-price">
          <div className="lp-plan"><div className="lp-pt">Free</div><div className="lp-pp">$0</div><div className="lp-pd">150 answers to start, no card. Every answer cited.</div></div>
          <div className="lp-plan lp-feat"><div className="lp-pt">Starter</div><div className="lp-pp">$99<span>/mo</span></div><div className="lp-pd">750 answers/mo. For a team fielding questionnaires regularly.</div></div>
          <div className="lp-plan"><div className="lp-pt">Growth</div><div className="lp-pp">$249<span>/mo</span></div><div className="lp-pd">3,000 answers/mo, 5 seats, unlimited library.</div></div>
        </div>
        <p className="lp-sec-sub">No demo, no annual lock-in. Self-serve. Cancel anytime.</p>
      </section>

      <section className="lp-final">
        <h2 className="lp-h2">Stop dreading the security review.</h2>
        <p className="lp-sec-sub">Answer your next questionnaire in minutes, with a receipt for every line.</p>
        <button className="lp-btn lp-big" onClick={onStart}>Start free · 150 answers, no card</button>
      </section>

      <footer className="lp-foot">
        <div className="lp-brand"><span className="lp-mark">◆</span> Attestly</div>
        <div className="lp-built">
          Built for the people who answer these every week. Ideas or gaps?{" "}
          <a href="mailto:hello@tryattestly.com">hello@tryattestly.com</a>
        </div>
        <div className="lp-legal">
          <a href="/terms.html">Terms</a>
          <a href="/privacy.html">Privacy</a>
          <a href="/dpa.html">DPA</a>
        </div>
        <div className="lp-disc">Attestly drafts answers to help your team respond faster. You review and approve every answer before it is sent. Sample company names and documents shown are illustrative.</div>
      </footer>
    </div>
  );
}

function Onboarding({ onDone, onBack }) {
  const [mode, setMode] = useState("signup"); // signup | login | forgot
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const login = mode === "login";
  const forgot = mode === "forgot";

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      if (forgot) {
        const { message } = await api.forgotPassword(email);
        setSent(message || "If an account exists for that email, a reset link is on its way.");
        setBusy(false);
        return;
      }
      const { api_token } = login
        ? await api.login(email, password)
        : await api.signup(name, email, password);
      setToken(api_token);
      onDone();
    } catch (e) {
      setErr(e.message);
      setBusy(false);
    }
  }

  if (forgot)
    return (
      <div className="center">
        <div className="card hero">
          <div className="brand big">
            <span className="logo">◆</span> Attestly
          </div>
          <h1>Reset your password</h1>
          {sent ? (
            <>
              <p className="muted">{sent}</p>
              <p className="muted small">
                Check your inbox (and spam) for a link from hello@tryattestly.com. It expires in 1 hour.
              </p>
            </>
          ) : (
            <>
              <p className="muted">
                Enter your account email and we'll send you a link to set a new password.
              </p>
              <form onSubmit={submit} className="stack">
                <input
                  placeholder="Work email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                {err && <div className="error">{err}</div>}
                <button className="primary" disabled={busy}>
                  {busy ? "Please wait…" : "Send reset link"}
                </button>
              </form>
            </>
          )}
          <p className="muted small" style={{ marginTop: 12 }}>
            <button
              className="link"
              style={{ display: "inline", padding: 0 }}
              onClick={() => {
                setErr("");
                setSent(false);
                setMode("login");
              }}
            >
              ← Back to log in
            </button>
          </p>
        </div>
      </div>
    );

  return (
    <div className="center">
      <div className="card hero">
        <div className="brand big">
          <span className="logo">◆</span> Attestly
        </div>
        <h1>Answer security questionnaires in minutes, not weeks.</h1>
        <p className="muted">
          Upload a SIG, CAIQ, or custom vendor questionnaire. Attestly reuses your approved
          answers and drafts the rest, then hands you a filled spreadsheet to review and send.
        </p>
        <form onSubmit={submit} className="stack">
          {!login && (
            <input placeholder="Company name" value={name} onChange={(e) => setName(e.target.value)} required />
          )}
          <input
            placeholder="Work email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            placeholder={login ? "Password" : "Choose a password (8+ characters)"}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {err && <div className="error">{err}</div>}
          <button className="primary" disabled={busy}>
            {busy ? "Please wait…" : login ? "Log in" : "Start free · 150 answers, no card"}
          </button>
        </form>
        {login && (
          <p className="muted small" style={{ marginTop: 10 }}>
            <button
              className="link"
              style={{ display: "inline", padding: 0 }}
              onClick={() => {
                setErr("");
                setMode("forgot");
              }}
            >
              Forgot password?
            </button>
          </p>
        )}
        {!login && (
          <p className="muted xsmall" style={{ marginTop: 12 }}>
            By continuing you agree to our <a href="/terms.html" target="_blank" rel="noreferrer">Terms</a> and{" "}
            <a href="/privacy.html" target="_blank" rel="noreferrer">Privacy Policy</a>.
          </p>
        )}
        {onBack && (
          <p className="muted small" style={{ marginTop: 10 }}>
            <button className="link" style={{ display: "inline", padding: 0 }} onClick={onBack}>
              ← Back to home
            </button>
          </p>
        )}
        <p className="muted small" style={{ marginTop: 12 }}>
          {login ? "New to Attestly? " : "Already have an account? "}
          <button
            className="link"
            style={{ display: "inline", padding: 0 }}
            onClick={() => {
              setErr("");
              setMode(login ? "signup" : "login");
            }}
          >
            {login ? "Create an account" : "Log in"}
          </button>
        </p>
      </div>
    </div>
  );
}

function ResetPassword({ token, onDone }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  function clearResetParam() {
    // Strip ?reset=… so a refresh doesn't re-open this view or replay the token.
    window.history.replaceState({}, "", window.location.pathname);
  }

  async function submit(e) {
    e.preventDefault();
    setErr("");
    if (password.length < 8) return setErr("Password must be at least 8 characters.");
    if (password !== confirm) return setErr("Passwords don't match.");
    setBusy(true);
    try {
      const { api_token } = await api.resetPassword(token, password);
      setToken(api_token);
      clearResetParam();
      onDone(); // signed straight in with the fresh token
    } catch (e) {
      setErr(e.message);
      setBusy(false);
    }
  }

  return (
    <div className="center">
      <div className="card hero">
        <div className="brand big">
          <span className="logo">◆</span> Attestly
        </div>
        <h1>Choose a new password</h1>
        <p className="muted">Set a new password for your account. You'll be signed in right after.</p>
        <form onSubmit={submit} className="stack">
          <input
            placeholder="New password (8+ characters)"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <input
            placeholder="Confirm new password"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
          />
          {err && <div className="error">{err}</div>}
          <button className="primary" disabled={busy}>
            {busy ? "Please wait…" : "Set new password"}
          </button>
        </form>
        <p className="muted small" style={{ marginTop: 12 }}>
          <button
            className="link"
            style={{ display: "inline", padding: 0 }}
            onClick={() => {
              clearResetParam();
              onDone();
            }}
          >
            ← Back to log in
          </button>
        </p>
      </div>
    </div>
  );
}

function Upload({ me, onChange, onNavigate }) {
  const [result, setResult] = useState(null);
  const [triage, setTriage] = useState(null); // triage summary before answering
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [library, setLibrary] = useState([]);
  const [sources, setSources] = useState(null); // { item, cites }
  const [seeding, setSeeding] = useState(false);

  const empty = me.bank_size === 0 && me.doc_count === 0;

  async function loadStarter() {
    setSeeding(true);
    setErr("");
    try {
      await api.seedStarter();
      onChange();
    } catch (e) {
      setErr(e.message);
    }
    setSeeding(false);
  }

  // Load the Answer Library once so citations can resolve to full source text.
  useEffect(() => {
    api.answers().then((r) => setLibrary(r.answers)).catch(() => {});
  }, []);

  async function onFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    setBusy(true);
    setErr("");
    setResult(null);
    setTriage(null);
    try {
      const res = await api.uploadQuestionnaire(file); // triage, no answering yet
      setTriage(res);
    } catch (e) {
      setErr(e.message);
    }
    setBusy(false);
  }

  async function runAnswer(exclude) {
    setBusy(true);
    setErr("");
    try {
      const res = await api.answerQuestionnaire(triage.questionnaire_id, exclude);
      setResult(res);
      setTriage(null);
      onChange();
    } catch (e) {
      setErr(e.message);
    }
    setBusy(false);
  }

  async function approve(item, answer) {
    await api.approveItem(item.id, answer);
    const fresh = await api.getQuestionnaire(result.questionnaire_id);
    setResult({ ...result, items: fresh.items });
    onChange();
  }

  async function saveMeta(itemId, body) {
    await api.setRemediation(itemId, body);
    const fresh = await api.getQuestionnaire(result.questionnaire_id);
    setResult((r) => ({ ...r, items: fresh.items }));
  }

  async function resolveContradiction(itemId, keep) {
    await api.resolveContradiction(itemId, keep);
    const fresh = await api.getQuestionnaire(result.questionnaire_id);
    setResult((r) => ({ ...r, items: fresh.items }));
    onChange(); // library may have changed
  }

  return (
    <div>
      {!result && !triage && empty && (
        <div className="card nudge">
          <h2>New here? Do this first ↓</h2>
          <p className="muted">
            Attestly answers from <em>your</em> approved answers and trust documents, and cites
            the exact source. With an empty library it can only say “not enough information,” so
            give it something to ground on before your first questionnaire:
          </p>
          <ol className="nudgesteps">
            <li>
              <div>
                <strong>Load starter answers</strong>
                <span className="muted small">
                  Common SIG/CAIQ answers (incl. PDPL, ISO 27001, DIFC/ADGM, VARA) as a baseline. Edit any later.
                </span>
              </div>
              <button className="primary" onClick={loadStarter} disabled={seeding}>
                {seeding ? "Loading…" : "Load starter answers"}
              </button>
            </li>
            <li>
              <div>
                <strong>Upload your SOC 2 or policies</strong>
                <span className="muted small">
                  So drafted answers cite the exact line: the “it’s not making things up” proof.
                </span>
              </div>
              <button className="secondary" onClick={() => onNavigate("documents")}>
                Upload your SOC 2 →
              </button>
            </li>
          </ol>
          {err && <div className="error">{err}</div>}
          <p className="muted small">
            Or skip ahead and upload a questionnaire now. You can always add sources later.
          </p>
        </div>
      )}

      {!result && !triage && (
        <div className="card dropzone">
          <h2>Upload a questionnaire</h2>
          <p className="muted">.xlsx or .csv. We auto-detect the question column.</p>
          <label className="primary filebtn">
            {busy ? "Reading…" : "Choose file"}
            <input type="file" accept=".xlsx,.xlsm,.csv" onChange={onFile} hidden />
          </label>
          {err && <div className="error">{err}</div>}
          <p className="muted small">
            {me.answers_remaining} answers left on your {me.tier_name} plan. We scope the file first,
            so you answer only what you choose; the rest stays locked until you upgrade.
          </p>
        </div>
      )}

      {triage && !result && (
        <TriagePanel
          triage={triage}
          busy={busy}
          err={err}
          onAnswer={runAnswer}
          onCancel={() => {
            setTriage(null);
            setErr("");
          }}
        />
      )}

      {result && (
        <div>
          {result.blocked > 0 && result.spend_paused && (
            <div className="lockbanner">
              {result.blocked} rows were not drafted: free capacity for this month has been reached.
              Upgrade to keep drafting, or try again next month. Reused answers are unaffected.
            </div>
          )}
          {result.blocked > 0 && !result.spend_paused && (
            <div className="lockbanner">
              {result.blocked} rows need a source document to answer. Upload your SOC 2 or a policy, then
              re-run this questionnaire.{" "}
              <button className="link" onClick={() => onNavigate && onNavigate("documents")}>
                Upload your SOC 2 →
              </button>
            </div>
          )}
          {result.locked > 0 && (
            <div className="lockbanner">
              {result.locked} of {result.total_questions} rows are locked because you reached your plan
              limit. The rest are answered and in your export. Upgrade to answer the locked rows.
            </div>
          )}
          {gateIssues(result.items).length > 0 && (
            <div className="lockbanner">
              {gateIssues(result.items).length} row(s) can't export yet. Every “No” needs a fix date (or
              a note that there's no plan), and every “N/A” needs a one-line reason. Fill the highlighted
              rows below.
            </div>
          )}
          <div className="statsrow">
            <Stat label="Answered" value={result.answered} />
            <Stat label="Reused from library" value={result.reused_from_bank} accent="green" />
            <Stat label="Drafted" value={result.drafted} accent="blue" />
            {result.excluded > 0 && <Stat label="N/A (excluded)" value={result.excluded} />}
            {result.locked > 0 && <Stat label="Locked" value={result.locked} accent="amber" />}
            {result.can_export_original && (
              <button
                className="primary"
                onClick={() =>
                  downloadExport(
                    result.questionnaire_id,
                    `questionnaire_filled.${result.source_kind === "csv" ? "csv" : "xlsx"}`,
                    true
                  ).catch((e) => alert("Export failed: " + e.message))
                }
              >
                Download filled original
              </button>
            )}
            <button
              className="secondary"
              onClick={() =>
                downloadExport(result.questionnaire_id, "questionnaire_answers.xlsx").catch((e) =>
                  alert("Export failed: " + e.message)
                )
              }
            >
              Clean .xlsx
            </button>
          </div>
          <ReviewList
            items={result.items}
            onApprove={approve}
            onShowSources={setSources}
            onSaveMeta={saveMeta}
            onResolveContradiction={resolveContradiction}
          />
          <button className="link" onClick={() => setResult(null)}>
            ← Upload another
          </button>
        </div>
      )}

      {sources && (
        <SourcePanel data={sources} library={library} onClose={() => setSources(null)} />
      )}
    </div>
  );
}

function TriagePanel({ triage, busy, err, onAnswer, onCancel }) {
  // Per-item exclusion state, seeded from the server's out-of-scope suggestions.
  const [excluded, setExcluded] = useState(() => {
    const m = {};
    for (const it of triage.items) {
      if (it.suggested_exclude) m[it.id] = it.suggested_reason || "Out of scope for our product.";
    }
    return m;
  });

  const isExcluded = (id) => Object.prototype.hasOwnProperty.call(excluded, id);
  function toggle(it) {
    setExcluded((m) => {
      const next = { ...m };
      if (isExcluded(it.id)) delete next[it.id];
      else next[it.id] = it.suggested_reason || "Out of scope for our product.";
      return next;
    });
  }
  function setReason(id, reason) {
    setExcluded((m) => ({ ...m, [id]: reason }));
  }

  const total = triage.total_questions;
  const covered = triage.library_covered;
  const excludedCount = Object.keys(excluded).length;
  // Rows that will consume an answer: not covered by the library, not excluded.
  const willUse = triage.items.filter((it) => !it.covered && !isExcluded(it.id)).length;
  const remaining = triage.answers_remaining;
  const overBudget = Math.max(0, willUse - remaining);

  function answer() {
    const exclude = Object.entries(excluded).map(([id, reason]) => ({
      id: Number(id),
      reason,
    }));
    onAnswer(exclude);
  }

  return (
    <div className="card">
      <div className="triage-head">
        <div>
          <span className="pill">{triage.framework}</span>
          <h2 style={{ marginTop: 8 }}>Scope this questionnaire</h2>
        </div>
        <button className="link" onClick={onCancel}>
          Cancel
        </button>
      </div>

      <div className="triage-summary">
        <span>
          <strong>{total}</strong> questions
        </span>
        <span>
          <strong>{covered}</strong> covered by your library
        </span>
        {excludedCount > 0 && (
          <span>
            <strong>{excludedCount}</strong> excluded (N/A)
          </span>
        )}
        <span>
          <strong>{willUse}</strong> answers will be used
        </span>
        <span className={overBudget ? "stale" : ""}>
          <strong>{remaining}</strong> remaining
        </span>
      </div>

      {overBudget > 0 && (
        <div className="lockbanner">
          This would use {willUse} answers but you have {remaining} left. The first {remaining} rows
          are answered; the other {overBudget} are locked until you upgrade. Exclude out-of-scope rows
          to fit more of what matters.
        </div>
      )}
      {triage.no_docs && (
        <div className="lockbanner">
          Drafting needs a trust document. Rows your library can't cover will be blocked until you
          upload your SOC 2 or a policy. Reused answers still work.
        </div>
      )}
      {triage.suggested_exclusions.length > 0 && (
        <p className="muted small">
          We pre-selected {triage.suggested_exclusions.length} row(s) that look out of scope for your
          product (they're marked N/A with a reason). Uncheck any that do apply.
        </p>
      )}

      <div className="triage-list">
        {triage.items.map((it) => {
          const ex = isExcluded(it.id);
          return (
            <div key={it.id} className={`triage-row ${ex ? "excluded" : ""}`}>
              <label className="triage-check">
                <input type="checkbox" checked={ex} onChange={() => toggle(it)} />
                <span className="triage-q">{it.question}</span>
              </label>
              <div className="triage-tags">
                {it.covered && <span className="tag green">Library</span>}
                {!it.covered && <span className="tag blue">Will draft</span>}
                {it.suggested_exclude && !ex && <span className="tag amber">Maybe N/A</span>}
              </div>
              {ex && (
                <input
                  className="triage-reason"
                  value={excluded[it.id]}
                  onChange={(e) => setReason(it.id, e.target.value)}
                  placeholder="Reason for N/A (required)"
                />
              )}
            </div>
          );
        })}
      </div>

      {err && <div className="error">{err}</div>}
      <div className="triage-actions">
        <button className="primary" onClick={answer} disabled={busy}>
          {busy ? "Answering…" : `Answer ${total - excludedCount} questions`}
        </button>
        <span className="muted small">Excluded rows are marked N/A in your export and use no quota.</span>
      </div>
    </div>
  );
}

function ReviewList({ items, onApprove, onShowSources, onSaveMeta, onResolveContradiction }) {
  return (
    <div className="stack">
      {items.map((it) => (
        <ReviewItem
          key={it.id}
          item={it}
          onApprove={onApprove}
          onShowSources={onShowSources}
          onSaveMeta={onSaveMeta}
          onResolveContradiction={onResolveContradiction}
        />
      ))}
    </div>
  );
}

function ContradictionPanel({ item, onResolve }) {
  let data = {};
  try {
    data = JSON.parse(item.contradiction || "{}");
  } catch (_) {
    data = {};
  }
  if (!data || !data.prior_answer) return null;
  const priorDate = data.prior_date ? fmtEpoch(data.prior_date) : "earlier";
  return (
    <div className="contra">
      <div className="contra-head">
        ⚠ This differs from what you answered before: {data.reason || "a specific changed"}. Confirm which
        is current.
      </div>
      <div className="contra-cols">
        <div className="contra-col">
          <div className="contra-label">Previously approved · {priorDate}</div>
          <div className="contra-text">{data.prior_answer}</div>
          <button className="secondary" onClick={() => onResolve(item.id, "prior")}>
            Keep this one
          </button>
        </div>
        <div className="contra-col current">
          <div className="contra-label">New answer · today</div>
          <div className="contra-text">{data.new_answer || item.answer}</div>
          <button className="primary" onClick={() => onResolve(item.id, "new")}>
            Use new &amp; update library
          </button>
        </div>
      </div>
    </div>
  );
}

function RemediationFields({ item, onSaveMeta }) {
  const isNo = (item.choice || "").trim() === "No";
  const isNa = (item.choice || "").trim() === "Not Applicable" && !item.excluded;
  if (!isNo && !isNa) return null;

  const [remDate, setRemDate] = useState(item.remediation_date || "");
  const [noPlan, setNoPlan] = useState(!!item.no_plan);
  const [naReason, setNaReason] = useState(item.na_reason || "");

  const unresolved = isNo ? !remDate.trim() && !noPlan : !naReason.trim();

  function save(patch) {
    onSaveMeta(item.id, {
      remediation_date: remDate,
      no_plan: noPlan,
      na_reason: naReason,
      ...patch,
    });
  }

  if (isNo)
    return (
      <div className={`gatebox ${unresolved ? "unresolved" : ""}`}>
        <div className="gatelabel">
          This is a “No”. Add a fix date or note there’s no plan before you export.
        </div>
        <div className="gaterow">
          <label className="gatefield">
            Remediation date
            <input
              type="date"
              value={remDate}
              onChange={(e) => {
                setRemDate(e.target.value);
                setNoPlan(false);
              }}
              onBlur={() => save({ no_plan: false })}
            />
          </label>
          <label className="gatecheck">
            <input
              type="checkbox"
              checked={noPlan}
              onChange={(e) => {
                const v = e.target.checked;
                setNoPlan(v);
                if (v) setRemDate("");
                save({ no_plan: v, remediation_date: v ? "" : remDate });
              }}
            />
            No remediation planned
          </label>
        </div>
      </div>
    );

  return (
    <div className={`gatebox ${unresolved ? "unresolved" : ""}`}>
      <div className="gatelabel">This is “N/A”. Add a one-line reason before you export.</div>
      <input
        placeholder="Why is this not applicable? (e.g. we don't process card data)"
        value={naReason}
        onChange={(e) => setNaReason(e.target.value)}
        onBlur={() => save({})}
      />
    </div>
  );
}

function ReviewItem({ item, onApprove, onShowSources, onSaveMeta, onResolveContradiction }) {
  const [answer, setAnswer] = useState(item.answer);
  const approved = item.status === "approved";
  const hasContradiction = !!(item.contradiction && item.contradiction !== "" && item.contradiction !== "{}");
  const cites = parseCitations(item.citations);
  const stale = cites.some((c) => c && c.stale);
  const docDate = (cites.find((c) => c && c.kind === "document" && c.date) || {}).date;
  const verified = item.verification === "supported";
  const badge =
    { reuse: ["Reused", "green"], drafted: ["AI draft", "blue"], fallback: ["Needs review", "amber"] }[
      item.match_type
    ] || ["", "gray"];
  return (
    <div className={`card item ${item.needs_review && !approved ? "review" : ""}`}>
      <div className="itemhead">
        {item.choice ? (
          <span className="tag choice">{item.choice}</span>
        ) : (
          <span className="tag amber">No status</span>
        )}
        <span className={`tag ${badge[1]}`}>{badge[0]}</span>
        {verified && <span className="tag green" title="Checked against your approved sources">✓ Verified</span>}
        {stale && (
          <span className="tag amber" title="The cited document is over 12 months old">
            ⚠ Source {docDate}
          </span>
        )}
        {hasContradiction && (
          <span className="tag amber" title="Differs from a previously approved answer">
            ⚠ Differs from before
          </span>
        )}
        <span className="muted small">confidence {Math.round(item.confidence)}%</span>
        {approved && <span className="tag green">✓ approved</span>}
      </div>
      <div className="q">{item.question}</div>
      <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} rows={4} />
      {hasContradiction && onResolveContradiction && (
        <ContradictionPanel item={item} onResolve={onResolveContradiction} />
      )}
      {onSaveMeta && <RemediationFields item={item} onSaveMeta={onSaveMeta} />}
      <div className="itemfoot">
        {cites.length > 0 ? (
          <button className="citebtn" onClick={() => onShowSources({ item, cites })}>
            🔍 {cites.length} source{cites.length > 1 ? "s" : ""} · show proof
          </button>
        ) : (
          <span className="muted xsmall">No grounded source. Review before sending.</span>
        )}
        {!approved && (
          <button className="secondary" onClick={() => onApprove(item, answer)}>
            Approve &amp; save to library
          </button>
        )}
      </div>
    </div>
  );
}

// Audit-ready trust: click a citation to see the exact approved source the
// answer was grounded in. Proof the AI didn't fabricate it.
function SourcePanel({ data, library, onClose }) {
  const { item, cites } = data;
  const norm = (s) => (s || "").trim().toLowerCase();
  // Citations may be legacy strings or structured { title, text, kind }.
  const resolved = cites.map((cite) => {
    const c = typeof cite === "string" ? { title: cite, text: "", kind: "library" } : cite || {};
    const title = c.title || "";
    let text = c.text || "";
    let category = null;
    if (c.kind !== "document") {
      const hit = library.find((x) => norm(x.question) === norm(title));
      if (hit) {
        if (!text) text = hit.answer;
        category = hit.category;
      }
    }
    return {
      title,
      text,
      kind: c.kind || "library",
      category,
      date: c.date || "",
      dateBasis: c.date_basis || "",
      stale: !!c.stale,
    };
  });
  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label="Answer sources">
        <div className="drawer-head">
          <div>
            <div className="drawer-kicker">Grounded in your approved sources</div>
            <h3 className="drawer-title">Proof of answer</h3>
          </div>
          <button className="link" onClick={onClose}>
            Close ✕
          </button>
        </div>

        <div className="drawer-q">{item.question}</div>
        <div className="drawer-a">{item.answer}</div>
        <div className="drawer-meta">
          {item.choice && <span className="tag choice">{item.choice}</span>}
          {item.verification === "supported" && <span className="tag green">✓ Verified</span>}
          <span className="muted xsmall">confidence {Math.round(item.confidence)}%</span>
        </div>

        <div className="drawer-sub">Sources ({resolved.length})</div>
        <div className="stack">
          {resolved.map((s, i) => {
            const isDoc = s.kind === "document";
            // Drop the label prefix the model echoes back ("Document: x" / "Approved answer").
            const name = (s.title || "").replace(/^document:\s*/i, "").trim();
            const generic = !name || /^approved answer$/i.test(name);
            return (
              <div key={i} className="source-item">
                <div className="source-tophead">
                  <span className={`tag ${isDoc ? "blue" : "gray"}`}>
                    {isDoc ? "📄 Document" : "✔ Approved answer"}
                  </span>
                  {!generic && <span className="q small">{name}</span>}
                </div>
                {s.text ? (
                  <div className="source-quote">{s.text}</div>
                ) : (
                  <div className="muted xsmall">Cited source (exact text not loaded).</div>
                )}
                {isDoc && s.date && (
                  <div className={`sourcedate ${s.stale ? "stale" : ""}`}>
                    {s.dateBasis === "stated" ? "Reviewed" : "Dated"} {s.date}
                    {s.stale && " · over 12 months old, a reviewer may ask you to refresh it"}
                  </div>
                )}
                {s.category && <div className="muted xsmall">{s.category}</div>}
              </div>
            );
          })}
        </div>
        <p className="muted xsmall drawer-foot">
          Every answer is grounded only in your approved answers and trust documents. The
          highlighted spans are the exact text the model cited. Nothing here is invented.
        </p>
      </aside>
    </>
  );
}

function Documents() {
  const [docs, setDocs] = useState([]);
  const [enabled, setEnabled] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function load() {
    const r = await api.documents();
    setDocs(r.documents);
    setEnabled(r.embeddings_enabled);
  }
  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  async function onFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    setBusy(true);
    setErr("");
    try {
      await api.uploadDocument(file);
      await load();
    } catch (e) {
      setErr(e.message);
    }
    setBusy(false);
  }

  async function remove(id) {
    await api.deleteDocument(id);
    await load();
  }

  return (
    <div className="grid2">
      <div className="card">
        <h3>Add a trust document</h3>
        <p className="muted small">
          Upload your SOC 2 report, security policies, or DPA (PDF or text). Drafted answers will
          cite the exact passage they came from: proof for a reviewing CTO that nothing is
          invented.
        </p>
        <label className="primary filebtn">
          {busy ? "Indexing…" : "Upload document"}
          <input type="file" accept=".pdf,.txt,.md" onChange={onFile} hidden />
        </label>
        {err && <div className="error">{err}</div>}
        <p className="muted xsmall" style={{ marginTop: 12 }}>
          {enabled
            ? "Semantic search is ON. Passages are matched by meaning."
            : "Semantic search is OFF (no embeddings key). Passages are matched lexically. Set VOYAGE_API_KEY to enable meaning-based grounding."}
        </p>
      </div>
      <div>
        <h3>{docs.length} document{docs.length === 1 ? "" : "s"}</h3>
        <div className="stack">
          {docs.map((d) => (
            <div key={d.id} className="card compact">
              <div className="itemhead">
                <span className="tag blue">📄 {d.kind}</span>
                <span className="q small">{d.name}</span>
              </div>
              <div className="muted xsmall">
                {d.chunk_count} passage{d.chunk_count === 1 ? "" : "s"} ·{" "}
                {Math.round(d.char_count / 1000)}k chars
                {d.source_date && (
                  <>
                    {" · "}
                    <span className={docStale(d.source_date) ? "stale" : ""}>
                      {d.date_basis === "stated" ? "reviewed" : "dated"} {fmtEpoch(d.source_date)}
                      {docStale(d.source_date) && " ⚠"}
                    </span>
                  </>
                )}
              </div>
              <button className="link" onClick={() => remove(d.id)}>
                Remove
              </button>
            </div>
          ))}
          {docs.length === 0 && <p className="muted small">No documents yet.</p>}
        </div>
      </div>
    </div>
  );
}

function Bank({ me, onChange }) {
  const [answers, setAnswers] = useState([]);
  const [q, setQ] = useState("");
  const [a, setA] = useState("");
  const [err, setErr] = useState("");
  const [seeding, setSeeding] = useState(false);
  const [msg, setMsg] = useState("");

  async function load() {
    setAnswers((await api.answers()).answers);
  }
  useEffect(() => {
    load();
  }, []);

  async function add(e) {
    e.preventDefault();
    setErr("");
    try {
      await api.addAnswer({ question: q, answer: a });
      setQ("");
      setA("");
      await load();
      onChange();
    } catch (e) {
      setErr(e.message);
    }
  }

  async function seed() {
    setSeeding(true);
    setErr("");
    setMsg("");
    try {
      const r = await api.seedStarter();
      setMsg(
        r.created > 0
          ? `Added ${r.created} starter answers${r.skipped ? ` (${r.skipped} already present)` : ""}.`
          : "You already have these starter answers."
      );
      await load();
      onChange();
    } catch (e) {
      setErr(e.message);
    }
    setSeeding(false);
  }

  return (
    <div className="grid2">
      <div className="card">
        <h3>Add an approved answer</h3>
        <form onSubmit={add} className="stack">
          <input placeholder="Question" value={q} onChange={(e) => setQ(e.target.value)} required />
          <textarea placeholder="Your approved answer" value={a} onChange={(e) => setA(e.target.value)} rows={4} required />
          {err && <div className="error">{err}</div>}
          <button className="primary">Add to library</button>
        </form>
        <p className="muted small">
          {me.bank_size}/{me.bank_limit === 100000 ? "∞" : me.bank_limit} entries. Every answer you approve
          from a questionnaire lands here automatically.
        </p>
        <div className="seedbox">
          <div className="small">
            <strong>New here?</strong> Load a starter set of common security answers (MFA,
            encryption, SOC 2, GDPR, incident response…) to review and edit as your own.
          </div>
          <button className="secondary" onClick={seed} disabled={seeding}>
            {seeding ? "Loading…" : "Load starter answers"}
          </button>
          {msg && <div className="notice small">{msg}</div>}
        </div>
      </div>
      <div>
        <h3>{answers.length} approved answers</h3>
        <div className="stack">
          {answers.map((x) => (
            <div key={x.id} className="card compact">
              <div className="q small">{x.question}</div>
              <div className="muted small clamp">{x.answer}</div>
              <div className="muted xsmall">
                {x.category} · reused {x.times_reused}×
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function History() {
  const [rows, setRows] = useState([]);
  useEffect(() => {
    api.listQuestionnaires().then((r) => setRows(r.questionnaires));
  }, []);

  // Speed SLA: surface questionnaires still open (not exported) and how long
  // they've been sitting. The "close the deal faster" nudge.
  const open = rows.filter((r) => r.status !== "exported");
  const stale = open
    .map((r) => ({ r, age: openFor(r.created_at) }))
    .filter((x) => x.age.hours >= 48)
    .sort((a, b) => b.age.hours - a.age.hours);

  return (
    <div>
      <h3>Questionnaires</h3>
      {stale.length > 0 && (
        <div className="sla-banner">
          ⏱ {stale.length} questionnaire{stale.length > 1 ? "s have" : " has"} been open over 48h,
          the oldest for {stale[0].age.label.replace("Open ", "")}. Approve the remaining drafts to
          close the deal.
        </div>
      )}
      <table className="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Questions</th>
            <th>Status</th>
            <th>Open for</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const age = openFor(r.created_at);
            const isOpen = r.status !== "exported";
            return (
            <tr key={r.id}>
              <td>{r.name}</td>
              <td>{r.total_questions}</td>
              <td>
                <span className="tag gray">{r.status}</span>
              </td>
              <td>
                {isOpen ? (
                  <span className={age.hours >= 48 ? "sla late" : "sla"}>{age.label}</span>
                ) : (
                  <span className="muted xsmall">closed</span>
                )}
              </td>
              <td>
                <div className="rowactions">
                  {r.can_export_original && (
                    <button
                      className="link"
                      onClick={() =>
                        downloadExport(
                          r.id,
                          `${(r.name || "responses").replace(/\.[^.]+$/, "")}_filled.${
                            r.source_kind === "csv" ? "csv" : "xlsx"
                          }`,
                          true
                        ).catch((e) => alert("Export failed: " + e.message))
                      }
                    >
                      Filled original
                    </button>
                  )}
                  <button
                    className="link"
                    onClick={() =>
                      downloadExport(r.id, `${(r.name || "responses").replace(/\.[^.]+$/, "")}_answers.xlsx`).catch(
                        (e) => alert("Export failed: " + e.message)
                      )
                    }
                  >
                    Clean
                  </button>
                </div>
              </td>
            </tr>
            );
          })}
          {rows.length === 0 && (
            <tr>
              <td colSpan={5} className="muted">
                No questionnaires yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function Billing({ me, onChange }) {
  const [plans, setPlans] = useState({});
  const [msg, setMsg] = useState("");
  const [interval, setInterval] = useState("year"); // default to annual (better value)
  const [delText, setDelText] = useState("");
  const [delBusy, setDelBusy] = useState(false);
  useEffect(() => {
    api.plans().then((r) => setPlans(r.plans));
  }, []);

  async function choose(tier) {
    setMsg("");
    const res = await api.checkout(tier, interval);
    if (res.simulated) {
      await api.confirm(tier);
      setMsg(`Upgraded to ${tier} (${interval}ly, simulated — no Stripe key configured).`);
      onChange();
    } else {
      window.location.href = res.checkout_url;
    }
  }

  const yearly = interval === "year";

  return (
    <div>
      <h3>Plans</h3>
      {msg && <div className="notice">{msg}</div>}

      <div className="cycletoggle">
        <button className={yearly ? "cyc" : "cyc active"} onClick={() => setInterval("month")}>
          Monthly
        </button>
        <button className={yearly ? "cyc active" : "cyc"} onClick={() => setInterval("year")}>
          Annual <span className="save">2 months free</span>
        </button>
      </div>

      <div className="plans">
        {Object.entries(plans).map(([key, p]) => {
          const effMonthly = yearly && p.price ? (p.yearly_price / 12).toFixed(2) : null;
          return (
            <div key={key} className={`card plan ${me.tier === key ? "current" : ""}`}>
              <div className="planname">{p.name}</div>
              <div className="price">
                ${yearly ? p.yearly_price : p.price}
                <span className="muted">{p.price === 0 ? "" : yearly ? "/yr" : "/mo"}</span>
              </div>
              {effMonthly && (
                <div className="muted small">≈ ${effMonthly}/mo · save ${p.price * 12 - p.yearly_price}</div>
              )}
              <ul>
                <li>{p.question_limit === 100000 ? "Unlimited" : p.question_limit} answers/mo</li>
                <li>{p.bank_limit === 100000 ? "Unlimited" : p.bank_limit} library entries</li>
                <li>{p.seats} seat{p.seats > 1 ? "s" : ""}</li>
              </ul>
              {me.tier === key ? (
                <button className="secondary" disabled>
                  Current plan
                </button>
              ) : (
                key !== "free" && (
                  <button className="primary" onClick={() => choose(key)}>
                    Choose {p.name}
                  </button>
                )
              )}
            </div>
          );
        })}
      </div>

      <div className="card" style={{ marginTop: 24 }}>
        <h3>Security</h3>
        <p className="muted small">
          Your API key authenticates this browser. If you think it may have been exposed, rotate it.
          This immediately invalidates the old key and signs out any other sessions.
        </p>
        <button
          className="secondary"
          onClick={async () => {
            if (!confirm("Rotate your API key? Other signed-in sessions will be logged out.")) return;
            try {
              const { api_token } = await api.rotateToken();
              setToken(api_token);
              setMsg("API key rotated. Other sessions are now signed out.");
            } catch (e) {
              setMsg("Could not rotate key: " + e.message);
            }
          }}
        >
          Rotate API key
        </button>
      </div>

      <div className="card dangerzone" style={{ marginTop: 24 }}>
        <h3>Delete my data</h3>
        <p className="muted small">
          Permanently delete your account and everything in it: questionnaires, uploaded documents,
          and your answer library. This can't be undone, and we keep nothing. Your data is never used
          to train AI models.
        </p>
        <div className="dangerrow">
          <input
            placeholder="Type DELETE to confirm"
            value={delText}
            onChange={(e) => setDelText(e.target.value)}
            aria-label="Type DELETE to confirm"
          />
          <button
            className="danger"
            disabled={delText !== "DELETE" || delBusy}
            onClick={async () => {
              setDelBusy(true);
              try {
                await api.deleteAccount();
                clearToken();
                window.location.reload();
              } catch (e) {
                setMsg("Could not delete your data: " + e.message);
                setDelBusy(false);
              }
            }}
          >
            {delBusy ? "Deleting…" : "Delete everything"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, accent }) {
  return (
    <div className={`stat ${accent || ""}`}>
      <div className="statnum">{value}</div>
      <div className="muted small">{label}</div>
    </div>
  );
}
