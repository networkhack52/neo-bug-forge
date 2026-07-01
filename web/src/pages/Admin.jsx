import { useState, useEffect } from "react";
import { supabase } from "../supabase";
import { useNavigate } from "react-router-dom";

const API_BASE    = import.meta.env.VITE_API_URL || "https://api.neobugforge.io";
const ADMIN_EMAIL = "ya7308312@gmail.com";

const STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #05050d; --bg2: #0d0d1a; --bg3: #141425;
    --border: #1e1e35; --border2: #2a2a4a;
    --accent: #7c6cfc; --accent2: #a78bfa; --cyan: #06b6d4;
    --green: #10b981; --green2: #34d399; --red: #ef4444;
    --text: #e2e8f0; --muted: #64748b; --muted2: #94a3b8;
    --font: 'Space Grotesk', sans-serif; --mono: 'JetBrains Mono', monospace;
  }
  body { background: var(--bg); color: var(--text); font-family: var(--font); min-height: 100vh; }

  nav {
    position: sticky; top: 0; z-index: 100;
    display: flex; align-items: center; justify-content: space-between;
    padding: 1rem 2rem;
    background: rgba(5,5,13,0.9);
    border-bottom: 1px solid var(--border);
    backdrop-filter: blur(12px);
  }
  .nav-logo {
    font-size: 1.15rem; font-weight: 800;
    background: linear-gradient(135deg, #a78bfa, #06b6d4);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .nav-right { display: flex; align-items: center; gap: 1rem; }
  .nav-badge {
    font-size: .7rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
    padding: .25rem .75rem; border-radius: 999px;
    background: rgba(239,68,68,.1); border: 1px solid rgba(239,68,68,.3); color: #ef4444;
  }
  .btn-sm {
    font-size: .8rem; font-weight: 600; padding: .4rem 1rem;
    border-radius: 6px; border: 1px solid var(--border2);
    background: transparent; color: var(--muted2); cursor: pointer;
    font-family: var(--font); transition: all .2s;
  }
  .btn-sm:hover { border-color: var(--accent2); color: var(--text); }

  .container { max-width: 960px; margin: 0 auto; padding: 2.5rem 1.5rem; }

  h1 { font-size: 1.7rem; font-weight: 800; letter-spacing: -.5px; margin-bottom: .3rem; }
  .subtitle { color: var(--muted2); font-size: .9rem; margin-bottom: 2rem; }

  /* ── Upgrade card ── */
  .card {
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;
  }
  .card h2 { font-size: 1rem; font-weight: 700; margin-bottom: 1.25rem; }

  .input-row { display: flex; gap: .75rem; flex-wrap: wrap; }
  .input-group { display: flex; flex-direction: column; gap: .4rem; flex: 1; min-width: 200px; }
  .input-group label { font-size: .75rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
  .input-group input, .input-group select {
    background: var(--bg3); border: 1px solid var(--border2);
    border-radius: 8px; padding: .6rem .9rem;
    color: var(--text); font-family: var(--font); font-size: .9rem;
    outline: none; transition: border-color .2s;
  }
  .input-group input:focus, .input-group select:focus { border-color: var(--accent); }
  .input-group select option { background: var(--bg3); }

  .btn-upgrade {
    align-self: flex-end; padding: .65rem 1.75rem; border-radius: 8px; border: none;
    background: linear-gradient(135deg, #7c6cfc, #5b45d4);
    color: #fff; font-family: var(--font); font-size: .9rem; font-weight: 700;
    cursor: pointer; transition: opacity .2s, transform .15s;
    white-space: nowrap;
  }
  .btn-upgrade:hover:not(:disabled) { opacity: .9; transform: translateY(-1px); }
  .btn-upgrade:disabled { opacity: .5; cursor: not-allowed; }

  .result-banner {
    margin-top: 1rem; padding: .75rem 1rem; border-radius: 8px;
    font-size: .875rem; font-weight: 600;
  }
  .result-success { background: rgba(16,185,129,.1); border: 1px solid rgba(16,185,129,.3); color: var(--green2); }
  .result-error   { background: rgba(239,68,68,.1);  border: 1px solid rgba(239,68,68,.3);  color: #f87171; }

  /* ── Users table ── */
  .table-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 1rem;
  }
  .table-header h2 { font-size: 1rem; font-weight: 700; margin: 0; }
  .btn-refresh {
    font-size: .8rem; font-weight: 600; padding: .35rem .9rem;
    border-radius: 6px; border: 1px solid var(--border2);
    background: transparent; color: var(--muted2); cursor: pointer;
    font-family: var(--font); transition: all .2s;
  }
  .btn-refresh:hover { border-color: var(--cyan); color: var(--cyan); }
  .btn-refresh:disabled { opacity: .4; cursor: not-allowed; }

  .search-input {
    width: 100%; background: var(--bg3); border: 1px solid var(--border2);
    border-radius: 8px; padding: .6rem .9rem; margin-bottom: 1rem;
    color: var(--text); font-family: var(--font); font-size: .9rem;
    outline: none; transition: border-color .2s;
  }
  .search-input:focus { border-color: var(--accent); }
  .search-input::placeholder { color: var(--muted); }

  table { width: 100%; border-collapse: collapse; font-size: .875rem; }
  thead th {
    font-size: .7rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
    color: var(--muted); padding: .6rem .75rem; text-align: left;
    border-bottom: 1px solid var(--border2);
  }
  tbody tr { transition: background .15s; }
  tbody tr:hover { background: rgba(124,108,252,.04); }
  tbody td {
    padding: .7rem .75rem; border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }
  .email-cell { font-family: var(--mono); font-size: .8rem; color: var(--muted2); }
  .date-cell  { font-family: var(--mono); font-size: .75rem; color: var(--muted); }

  .tier-badge {
    display: inline-flex; align-items: center; gap: .3rem;
    font-size: .7rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
    padding: .2rem .7rem; border-radius: 999px;
  }
  .tier-free { background: rgba(100,116,139,.1); border: 1px solid rgba(100,116,139,.3); color: var(--muted2); }
  .tier-pro  { background: rgba(124,108,252,.1); border: 1px solid rgba(124,108,252,.3); color: var(--accent2); }
  .tier-team { background: rgba(16,185,129,.1);  border: 1px solid rgba(16,185,129,.3);  color: var(--green2); }

  .usage-cell { font-size: .8rem; color: var(--muted2); }
  .usage-cell strong { color: var(--text); }

  .inline-btn {
    font-size: .72rem; font-weight: 700; padding: .25rem .65rem;
    border-radius: 5px; border: 1px solid var(--border2);
    background: transparent; color: var(--muted2); cursor: pointer;
    font-family: var(--font); transition: all .15s;
  }
  .inline-btn:hover { border-color: var(--accent2); color: var(--accent2); }
  .inline-btn.pro  { border-color: rgba(124,108,252,.4); color: var(--accent2); }
  .inline-btn.team { border-color: rgba(16,185,129,.4);  color: var(--green2); }
  .inline-btn.free { border-color: rgba(239,68,68,.3);   color: #f87171; }

  .empty-state { text-align: center; padding: 3rem; color: var(--muted); font-size: .9rem; }

  .loading-screen {
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    color: var(--muted2); font-size: .95rem;
  }

  .stat-row {
    display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap;
  }
  .mini-stat {
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: 10px; padding: 1rem 1.25rem; flex: 1; min-width: 120px;
  }
  .mini-stat-label { font-size: .7rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .08em; margin-bottom: .35rem; }
  .mini-stat-value { font-size: 1.5rem; font-weight: 800; letter-spacing: -.5px; }
  .mini-stat-value.accent { color: var(--accent2); }
  .mini-stat-value.green  { color: var(--green2); }
  .mini-stat-value.cyan   { color: var(--cyan); }
`;

const TIER_LABELS = { free: "🆓 Free", pro: "⚡ Pro", team: "👥 Team" };

export default function Admin() {
  const [user,      setUser]      = useState(null);
  const [loading,   setLoading]   = useState(true);
  const [users,     setUsers]     = useState([]);
  const [fetching,  setFetching]  = useState(false);
  const [fetchError, setFetchError] = useState(null);
  const [search,    setSearch]    = useState("");
  const [copied,    setCopied]    = useState(false);

  // Upgrade form
  const [email,     setEmail]     = useState("");
  const [tier,      setTier]      = useState("pro");
  const [upgrading, setUpgrading] = useState(false);
  const [result,    setResult]    = useState(null); // { ok, message }

  const navigate = useNavigate();

  useEffect(() => {
    // Always refresh session first so the token is never stale
    supabase.auth.refreshSession().then(({ data: { session } }) => {
      if (!session) {
        supabase.auth.getSession().then(({ data: { session: s } }) => {
          if (!s) { navigate("/login"); return; }
          if (s.user.email !== ADMIN_EMAIL) { navigate("/dashboard"); return; }
          setUser(s.user);
          setLoading(false);
          fetchUsers(s.access_token);
        });
        return;
      }
      if (session.user.email !== ADMIN_EMAIL) { navigate("/dashboard"); return; }
      setUser(session.user);
      setLoading(false);
      fetchUsers(session.access_token);
    });
  }, []);

  async function getToken() {
    // Try to refresh first, fall back to current session
    const { data: { session: refreshed } } = await supabase.auth.refreshSession();
    if (refreshed?.access_token) return refreshed.access_token;
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token;
  }

  async function fetchUsers(token) {
    setFetching(true);
    setFetchError(null);
    try {
      const t = token || await getToken();
      if (!t) { setFetchError("No auth token — please log out and back in."); setFetching(false); return; }
      const res = await fetch(`${API_BASE}/v1/admin/users`, {
        headers: { Authorization: `Bearer ${t}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUsers(data.users || []);
      } else {
        let errMsg = `API error ${res.status}`;
        try { const body = await res.json(); errMsg += `: ${body.detail || JSON.stringify(body)}`; } catch {}
        setFetchError(errMsg);
      }
    } catch (err) {
      setFetchError(`Network error: ${err.message}`);
    }
    setFetching(false);
  }

  async function handleUpgrade(e) {
    e.preventDefault();
    if (!email.trim()) return;
    setUpgrading(true);
    setResult(null);
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/v1/admin/upgrade`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ email: email.trim().toLowerCase(), tier }),
      });
      const data = await res.json();
      if (res.ok) {
        setResult({ ok: true, message: `✓ ${data.email} upgraded to ${data.tier} (${data.fixes_limit} fixes/mo)` });
        setEmail("");
        fetchUsers();
      } else {
        setResult({ ok: false, message: data.detail || "Something went wrong." });
      }
    } catch (err) {
      setResult({ ok: false, message: err.message });
    }
    setUpgrading(false);
  }

  function exportEmails(tierFilter) {
    const list = (tierFilter ? users.filter(u => u.tier === tierFilter) : users)
      .map(u => u.user_email)
      .filter(Boolean)
      .join(", ");
    navigator.clipboard.writeText(list).then(() => {
      setCopied(tierFilter || "all");
      setTimeout(() => setCopied(false), 2000);
    });
  }

  async function quickUpgrade(userEmail, newTier) {
    const token = await getToken();
    const res = await fetch(`${API_BASE}/v1/admin/upgrade`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ email: userEmail, tier: newTier }),
    });
    if (res.ok) fetchUsers();
  }

  if (loading) return (
    <>
      <style>{STYLES}</style>
      <div className="loading-screen">Verifying access...</div>
    </>
  );

  const filtered = users.filter(u =>
    !search || u.user_email?.toLowerCase().includes(search.toLowerCase())
  );

  const counts = {
    total: users.length,
    pro:   users.filter(u => u.tier === "pro").length,
    team:  users.filter(u => u.tier === "team").length,
    free:  users.filter(u => u.tier === "free").length,
  };

  return (
    <>
      <style>{STYLES}</style>

      <nav>
        <div className="nav-logo">NeoBugForge Admin</div>
        <div className="nav-right">
          <span className="nav-badge">Admin</span>
          <button className="btn-sm" onClick={() => navigate("/dashboard")}>← Dashboard</button>
        </div>
      </nav>

      <div className="container">
        <h1>User Management</h1>
        <p className="subtitle">Upgrade reviewers and manage user tiers.</p>

        {/* Stats */}
        <div className="stat-row">
          <div className="mini-stat">
            <div className="mini-stat-label">Total Users</div>
            <div className="mini-stat-value accent">{counts.total}</div>
          </div>
          <div className="mini-stat">
            <div className="mini-stat-label">Pro</div>
            <div className="mini-stat-value cyan">{counts.pro}</div>
          </div>
          <div className="mini-stat">
            <div className="mini-stat-label">Team</div>
            <div className="mini-stat-value green">{counts.team}</div>
          </div>
          <div className="mini-stat">
            <div className="mini-stat-label">Free</div>
            <div className="mini-stat-value" style={{ color: "var(--muted2)" }}>{counts.free}</div>
          </div>
        </div>

        {/* Upgrade form */}
        <div className="card">
          <h2>Upgrade a Reviewer</h2>
          <form onSubmit={handleUpgrade}>
            <div className="input-row">
              <div className="input-group" style={{ flex: 2 }}>
                <label>User Email</label>
                <input
                  type="email"
                  placeholder="user@example.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                />
              </div>
              <div className="input-group">
                <label>New Tier</label>
                <select value={tier} onChange={e => setTier(e.target.value)}>
                  <option value="pro">⚡ Pro (500 fixes/mo)</option>
                  <option value="team">👥 Team (unlimited)</option>
                  <option value="free">🆓 Free (100 fixes/mo)</option>
                </select>
              </div>
              <button className="btn-upgrade" type="submit" disabled={upgrading}>
                {upgrading ? "Upgrading…" : "Upgrade →"}
              </button>
            </div>
          </form>

          {result && (
            <div className={`result-banner ${result.ok ? "result-success" : "result-error"}`}>
              {result.message}
            </div>
          )}
        </div>

        {/* Users table */}
        <div className="card">
          <div className="table-header">
            <h2>All Users</h2>
            <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap" }}>
              <button className="btn-refresh" onClick={() => exportEmails(null)}>
                {copied === "all" ? "✓ Copied!" : `⧉ Copy All Emails (${users.length})`}
              </button>
              <button className="btn-refresh" onClick={() => exportEmails("free")} style={{ color: "var(--muted2)" }}>
                {copied === "free" ? "✓ Copied!" : `Free (${counts.free})`}
              </button>
              <button className="btn-refresh" onClick={() => exportEmails("pro")} style={{ color: "var(--cyan)" }}>
                {copied === "pro" ? "✓ Copied!" : `Pro (${counts.pro})`}
              </button>
              <button
                className="btn-refresh"
                onClick={() => fetchUsers()}
                disabled={fetching}
              >
                {fetching ? "Loading…" : "↻ Refresh"}
              </button>
            </div>
          </div>

          <input
            className="search-input"
            placeholder="Search by email…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />

          {fetchError && (
            <div className="result-banner result-error" style={{ marginBottom: "1rem" }}>
              ⚠ Failed to load users: {fetchError}
            </div>
          )}

          {filtered.length === 0 ? (
            <div className="empty-state">{fetching ? "Loading users…" : fetchError ? "Could not load users — see error above." : "No users found."}</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Tier</th>
                  <th>Usage</th>
                  <th>Joined</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(u => (
                  <tr key={u.user_email}>
                    <td className="email-cell">{u.user_email}</td>
                    <td>
                      <span className={`tier-badge tier-${u.tier}`}>
                        {TIER_LABELS[u.tier] ?? u.tier}
                      </span>
                    </td>
                    <td className="usage-cell">
                      <strong>{u.fixes_used ?? 0}</strong> / {u.fixes_limit ?? "?"}
                    </td>
                    <td className="date-cell">
                      {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: ".4rem", flexWrap: "wrap" }}>
                        {u.tier !== "pro" && (
                          <button
                            className="inline-btn pro"
                            onClick={() => quickUpgrade(u.user_email, "pro")}
                          >Pro</button>
                        )}
                        {u.tier !== "team" && (
                          <button
                            className="inline-btn team"
                            onClick={() => quickUpgrade(u.user_email, "team")}
                          >Team</button>
                        )}
                        {u.tier !== "free" && (
                          <button
                            className="inline-btn free"
                            onClick={() => quickUpgrade(u.user_email, "free")}
                          >Revoke</button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}
