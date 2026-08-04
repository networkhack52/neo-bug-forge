import React, { useEffect, useState } from "react";
import { api, getToken, setToken, clearToken, downloadExport } from "./api.js";

export default function App() {
  const [me, setMe] = useState(null);
  const [tab, setTab] = useState("upload");
  const [loading, setLoading] = useState(true);

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
  if (!me) return <Onboarding onDone={refresh} />;

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
          ["history", "History"],
          ["billing", "Plan & Billing"],
        ].map(([k, label]) => (
          <button key={k} className={tab === k ? "tab active" : "tab"} onClick={() => setTab(k)}>
            {label}
          </button>
        ))}
      </nav>

      <main className="content">
        {tab === "upload" && <Upload me={me} onChange={refresh} />}
        {tab === "bank" && <Bank me={me} onChange={refresh} />}
        {tab === "history" && <History />}
        {tab === "billing" && <Billing me={me} onChange={refresh} />}
      </main>
    </div>
  );
}

function Onboarding({ onDone }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const { api_token } = await api.signup(name, email);
      setToken(api_token);
      onDone();
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
        <h1>Answer security questionnaires in minutes, not weeks.</h1>
        <p className="muted">
          Upload a SIG, CAIQ, or custom vendor questionnaire. Attestly reuses your approved
          answers and drafts the rest, then hands you a filled spreadsheet to review and send.
        </p>
        <form onSubmit={submit} className="stack">
          <input placeholder="Company name" value={name} onChange={(e) => setName(e.target.value)} required />
          <input placeholder="Work email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          {err && <div className="error">{err}</div>}
          <button className="primary" disabled={busy}>
            {busy ? "Creating…" : "Start free — 25 answers, no card"}
          </button>
        </form>
      </div>
    </div>
  );
}

function Upload({ me, onChange }) {
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function onFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    setBusy(true);
    setErr("");
    setResult(null);
    try {
      const res = await api.uploadQuestionnaire(file);
      setResult(res);
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

  return (
    <div>
      {!result && (
        <div className="card dropzone">
          <h2>Upload a questionnaire</h2>
          <p className="muted">.xlsx or .csv — we auto-detect the question column.</p>
          <label className="primary filebtn">
            {busy ? "Answering…" : "Choose file"}
            <input type="file" accept=".xlsx,.xlsm,.csv" onChange={onFile} hidden />
          </label>
          {err && <div className="error">{err}</div>}
          <p className="muted small">
            {me.questions_remaining} answers left on your {me.tier_name} plan this month.
          </p>
        </div>
      )}

      {result && (
        <div>
          <div className="statsrow">
            <Stat label="Questions" value={result.total_questions} />
            <Stat label="Reused from library" value={result.reused_from_bank} accent="green" />
            <Stat label="Drafted" value={result.drafted} accent="blue" />
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
          <ReviewList items={result.items} onApprove={approve} />
          <button className="link" onClick={() => setResult(null)}>
            ← Upload another
          </button>
        </div>
      )}
    </div>
  );
}

function ReviewList({ items, onApprove }) {
  return (
    <div className="stack">
      {items.map((it) => (
        <ReviewItem key={it.id} item={it} onApprove={onApprove} />
      ))}
    </div>
  );
}

function ReviewItem({ item, onApprove }) {
  const [answer, setAnswer] = useState(item.answer);
  const approved = item.status === "approved";
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
        <span className="muted small">confidence {Math.round(item.confidence)}%</span>
        {approved && <span className="tag green">✓ approved</span>}
      </div>
      <div className="q">{item.question}</div>
      <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} rows={4} />
      {!approved && (
        <button className="secondary" onClick={() => onApprove(item, answer)}>
          Approve & save to library
        </button>
      )}
    </div>
  );
}

function Bank({ me, onChange }) {
  const [answers, setAnswers] = useState([]);
  const [q, setQ] = useState("");
  const [a, setA] = useState("");
  const [err, setErr] = useState("");

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
  return (
    <div>
      <h3>Questionnaires</h3>
      <table className="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Questions</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{r.name}</td>
              <td>{r.total_questions}</td>
              <td>
                <span className="tag gray">{r.status}</span>
              </td>
              <td>
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
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={4} className="muted">
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
