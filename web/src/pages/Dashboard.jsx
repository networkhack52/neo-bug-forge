import { useState, useEffect } from "react";
import { supabase } from "../supabase";
import { useNavigate, Link } from "react-router-dom";

const API_BASE = import.meta.env.VITE_API_URL || "https://api.neobugforge.io";

const STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #05050d; --bg2: #0d0d1a; --bg3: #141425;
    --border: #1e1e35; --border2: #2a2a4a;
    --accent: #7c6cfc; --accent2: #a78bfa; --cyan: #06b6d4;
    --green: #10b981; --green2: #34d399;
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
    text-decoration: none;
  }
  .nav-right { display: flex; align-items: center; gap: 1rem; }
  .nav-email { font-size: .8rem; color: var(--muted2); }
  .btn-signout {
    font-size: .8rem; font-weight: 600; padding: .4rem 1rem;
    border-radius: 6px; border: 1px solid var(--border2);
    background: transparent; color: var(--muted2); cursor: pointer;
    font-family: var(--font); transition: all .2s;
  }
  .btn-signout:hover { border-color: var(--accent2); color: var(--text); }

  .container { max-width: 860px; margin: 0 auto; padding: 3rem 1.5rem; }

  .page-header { margin-bottom: 2.5rem; }
  .page-header h1 { font-size: 1.8rem; font-weight: 800; letter-spacing: -.5px; margin-bottom: .35rem; }
  .page-header p { color: var(--muted2); font-size: .95rem; }

  .cards-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; margin-bottom: 2rem; }
  @media (max-width: 640px) { .cards-grid { grid-template-columns: 1fr; } }

  .stat-card {
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: 12px; padding: 1.25rem 1.5rem;
  }
  .stat-label { font-size: .75rem; font-weight: 600; color: var(--muted); letter-spacing: .08em; text-transform: uppercase; margin-bottom: .5rem; }
  .stat-value { font-size: 1.8rem; font-weight: 800; letter-spacing: -.5px; }
  .stat-value.accent { color: var(--accent2); }
  .stat-value.green { color: var(--green2); }
  .stat-sub { font-size: .8rem; color: var(--muted); margin-top: .25rem; }

  .key-card {
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: 12px; padding: 1.75rem; margin-bottom: 1.5rem;
  }
  .key-card h2 { font-size: 1rem; font-weight: 700; margin-bottom: .35rem; }
  .key-card p { color: var(--muted2); font-size: .875rem; margin-bottom: 1.25rem; }

  .key-box {
    display: flex; align-items: center; gap: .75rem;
    background: var(--bg3); border: 1px solid var(--border2);
    border-radius: 8px; padding: .75rem 1rem;
  }
  .key-value {
    flex: 1; font-family: var(--mono); font-size: .875rem; color: var(--accent2);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .key-masked { color: var(--muted); letter-spacing: .1em; }
  .btn-icon {
    background: transparent; border: 1px solid var(--border2);
    border-radius: 6px; padding: .4rem .75rem; cursor: pointer;
    font-size: .8rem; font-weight: 600; font-family: var(--font);
    color: var(--muted2); transition: all .2s; white-space: nowrap;
  }
  .btn-icon:hover { border-color: var(--accent2); color: var(--text); }
  .btn-icon.copied { border-color: var(--green); color: var(--green2); }

  .tier-badge {
    display: inline-flex; align-items: center; gap: .4rem;
    font-size: .75rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase;
    padding: .3rem .85rem; border-radius: 999px;
  }
  .tier-free { background: rgba(100,116,139,.1); border: 1px solid rgba(100,116,139,.3); color: var(--muted2); }
  .tier-pro  { background: rgba(124,108,252,.1); border: 1px solid rgba(124,108,252,.3); color: var(--accent2); }
  .tier-team { background: rgba(16,185,129,.1);  border: 1px solid rgba(16,185,129,.3);  color: var(--green2); }

  .upgrade-card {
    background: linear-gradient(135deg, rgba(124,108,252,.08), var(--bg2));
    border: 1px solid rgba(124,108,252,.25);
    border-radius: 12px; padding: 1.75rem;
    margin-bottom: 1.5rem;
  }
  .upgrade-card h2 { font-size: 1rem; font-weight: 700; margin-bottom: .35rem; }
  .upgrade-card p { color: var(--muted2); font-size: .875rem; margin-bottom: 1.25rem; }
  .btn-upgrade {
    display: inline-block; padding: .7rem 1.75rem; border-radius: 8px; border: none;
    background: linear-gradient(135deg, #7c6cfc, #5b45d4);
    color: #fff; font-family: var(--font); font-size: .9rem; font-weight: 700;
    cursor: pointer; text-decoration: none;
    box-shadow: 0 0 16px rgba(124,108,252,.3);
    transition: opacity .2s, transform .15s;
  }
  .btn-upgrade:hover { opacity: .9; transform: translateY(-1px); }

  .quota-bar-wrap { margin-top: 1rem; }
  .quota-bar-label { display: flex; justify-content: space-between; font-size: .8rem; color: var(--muted2); margin-bottom: .5rem; }
  .quota-bar-bg { background: var(--bg3); border-radius: 999px; height: 6px; overflow: hidden; }
  .quota-bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--accent), var(--cyan)); transition: width .6s ease; }

  .setup-card {
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: 12px; padding: 1.75rem; margin-bottom: 1.5rem;
  }
  .setup-card h2 { font-size: 1rem; font-weight: 700; margin-bottom: 1rem; }
  .setup-steps { display: flex; flex-direction: column; gap: .75rem; }
  .setup-step {
    display: flex; align-items: flex-start; gap: .75rem;
    font-size: .875rem; color: var(--muted2);
  }
  .step-num {
    width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
    background: rgba(124,108,252,.15); border: 1px solid rgba(124,108,252,.3);
    display: flex; align-items: center; justify-content: center;
    font-size: .7rem; font-weight: 700; color: var(--accent2);
  }
  .setup-step code {
    font-family: var(--mono); font-size: .8rem;
    background: var(--bg3); border: 1px solid var(--border2);
    border-radius: 4px; padding: .15rem .4rem; color: var(--accent2);
  }

  .loading-screen {
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    color: var(--muted2); font-size: .95rem;
  }
`;

export default function Dashboard() {
  const [user, setUser]         = useState(null);
  const [keyRow, setKeyRow]     = useState(null);
  const [loading, setLoading]   = useState(true);
  const [showKey, setShowKey]   = useState(false);
  const [copied, setCopied]     = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (!session) { navigate("/login"); return; }
      setUser(session.user);
      await loadOrCreateKey(session);
      setLoading(false);
    });
  }, []);

  async function loadOrCreateKey(session) {
    // Call backend to get or create API key for this user
    const res = await fetch(`${API_BASE}/v1/keys`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({ label: "default" }),
    });
    if (res.ok) {
      const data = await res.json();
      setKeyRow(data);
    } else {
      // Key may already exist — try fetching usage instead
      const usageRes = await fetch(`${API_BASE}/v1/usage`, {
        headers: { "Authorization": `Bearer ${session.access_token}` },
      });
      if (usageRes.ok) setKeyRow(await usageRes.json());
    }
  }

  async function handleSignOut() {
    await supabase.auth.signOut();
    navigate("/login");
  }

  function handleCopy() {
    if (!keyRow?.api_key) return;
    navigator.clipboard.writeText(keyRow.api_key).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  if (loading) return (
    <>
      <style>{STYLES}</style>
      <div className="loading-screen">Loading your dashboard...</div>
    </>
  );

  const tier       = keyRow?.tier || "free";
  const fixesUsed  = keyRow?.fixes_used ?? 0;
  const fixesLimit = tier === "free" ? 100 : tier === "pro" ? 500 : null;
  const pct        = fixesLimit ? Math.min((fixesUsed / fixesLimit) * 100, 100) : 0;

  return (
    <>
      <style>{STYLES}</style>

      <nav>
        <a href="https://neobugforge.io" className="nav-logo">NeoBugForge</a>
        <div className="nav-right">
          <span className="nav-email">{user?.email}</span>
          <button className="btn-signout" onClick={handleSignOut}>Sign out</button>
        </div>
      </nav>

      <div className="container">
        <div className="page-header">
          <h1>Dashboard</h1>
          <p>Your API key, usage, and plan details.</p>
        </div>

        {/* Stats */}
        <div className="cards-grid">
          <div className="stat-card">
            <div className="stat-label">Plan</div>
            <div style={{ marginTop: ".35rem" }}>
              <span className={`tier-badge tier-${tier}`}>
                {tier === "free" ? "🆓 Free" : tier === "pro" ? "⚡ Pro" : "👥 Team"}
              </span>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Fixes Used</div>
            <div className="stat-value accent">{fixesUsed}</div>
            <div className="stat-sub">{fixesLimit ? `of ${fixesLimit} this month` : "Unlimited (fair use)"}</div>
          </div>
          <div className="stat-card">
            <div className="stat-label">Status</div>
            <div className="stat-value green" style={{ fontSize: "1.2rem", marginTop: ".25rem" }}>● Active</div>
          </div>
        </div>

        {/* API Key */}
        <div className="key-card">
          <h2>Your API Key</h2>
          <p>Use this key in the VS Code extension or any API request. Keep it secret — don't share it.</p>
          <div className="key-box">
            <span className="key-value">
              {keyRow?.api_key
                ? (showKey ? keyRow.api_key : keyRow.api_key.slice(0, 8) + "••••••••••••••••••••••••••••••••")
                : "Generating key..."}
            </span>
            <button className="btn-icon" onClick={() => setShowKey(v => !v)}>
              {showKey ? "Hide" : "Show"}
            </button>
            <button className={`btn-icon ${copied ? "copied" : ""}`} onClick={handleCopy}>
              {copied ? "✓ Copied" : "Copy"}
            </button>
          </div>

          {fixesLimit && (
            <div className="quota-bar-wrap">
              <div className="quota-bar-label">
                <span>Monthly usage</span>
                <span>{fixesUsed} / {fixesLimit} fixes</span>
              </div>
              <div className="quota-bar-bg">
                <div className="quota-bar-fill" style={{ width: `${pct}%` }} />
              </div>
            </div>
          )}
        </div>

        {/* Upgrade CTA (only for free/pro) */}
        {tier !== "team" && (
          <div className="upgrade-card">
            <h2>{tier === "free" ? "Upgrade to Pro" : "Upgrade to Team"}</h2>
            <p>
              {tier === "free"
                ? "Get 500 fixes/month, priority processing, and unlock the full power of Neo Bug Forge."
                : "Unlimited fixes (fair use) and up to 10 seats for your team."}
            </p>
            <a href="https://neobugforge.io/#pricing" className="btn-upgrade">
              View Plans →
            </a>
          </div>
        )}

        {/* Setup Guide */}
        <div className="setup-card">
          <h2>Quick Setup</h2>
          <div className="setup-steps">
            <div className="setup-step">
              <div className="step-num">1</div>
              <div>Install the <strong>Neo Bug Forge</strong> extension in VS Code (search in Extensions tab)</div>
            </div>
            <div className="setup-step">
              <div className="step-num">2</div>
              <div>Press <code>Ctrl+Shift+P</code> → <strong>Neo Bug Forge: Set API Key</strong></div>
            </div>
            <div className="setup-step">
              <div className="step-num">3</div>
              <div>Paste your API key above and press Enter</div>
            </div>
            <div className="setup-step">
              <div className="step-num">4</div>
              <div>Select broken code → <code>Ctrl+Shift+F</code> → done! 🎉</div>
            </div>
          </div>
        </div>

      </div>
    </>
  );
}
