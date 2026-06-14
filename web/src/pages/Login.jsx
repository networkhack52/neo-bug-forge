import { useState } from "react";
import { supabase } from "../supabase";
import { useNavigate, Link } from "react-router-dom";

const STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #05050d; --bg2: #0d0d1a; --bg3: #141425;
    --border: #1e1e35; --border2: #2a2a4a;
    --accent: #7c6cfc; --accent2: #a78bfa; --cyan: #06b6d4;
    --green: #10b981; --text: #e2e8f0; --muted: #64748b; --muted2: #94a3b8;
    --font: 'Space Grotesk', sans-serif; --mono: 'JetBrains Mono', monospace;
  }
  body { background: var(--bg); color: var(--text); font-family: var(--font); min-height: 100vh; }
  .auth-wrap {
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    padding: 2rem 1rem;
    background: radial-gradient(ellipse 80% 50% at 50% -10%, rgba(124,108,252,.12) 0%, transparent 70%);
  }
  .auth-card {
    width: 100%; max-width: 420px;
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: 16px; padding: 2.5rem;
  }
  .auth-logo {
    font-size: 1.3rem; font-weight: 800; margin-bottom: 2rem; text-align: center;
    background: linear-gradient(135deg, #a78bfa, #06b6d4);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  h1 { font-size: 1.5rem; font-weight: 800; margin-bottom: .35rem; }
  .subtitle { color: var(--muted2); font-size: .9rem; margin-bottom: 2rem; }
  .field { margin-bottom: 1.25rem; }
  label { display: block; font-size: .8rem; font-weight: 600; color: var(--muted2); margin-bottom: .5rem; letter-spacing: .04em; }
  input {
    width: 100%; padding: .75rem 1rem;
    background: var(--bg3); border: 1px solid var(--border2);
    border-radius: 8px; color: var(--text); font-family: var(--font); font-size: .95rem;
    outline: none; transition: border-color .2s;
  }
  input:focus { border-color: var(--accent); }
  .btn-primary {
    width: 100%; padding: .85rem; border-radius: 10px; border: none;
    background: linear-gradient(135deg, #7c6cfc, #5b45d4);
    color: #fff; font-family: var(--font); font-size: 1rem; font-weight: 700;
    cursor: pointer; transition: opacity .2s, transform .15s;
    box-shadow: 0 0 16px rgba(124,108,252,.3);
    margin-top: .5rem;
  }
  .btn-primary:hover:not(:disabled) { opacity: .9; transform: translateY(-1px); }
  .btn-primary:disabled { opacity: .5; cursor: not-allowed; }
  .divider {
    display: flex; align-items: center; gap: 1rem;
    margin: 1.5rem 0; color: var(--muted); font-size: .8rem;
  }
  .divider::before, .divider::after { content: ''; flex: 1; height: 1px; background: var(--border); }
  .btn-github {
    width: 100%; padding: .85rem; border-radius: 10px;
    background: var(--bg3); border: 1px solid var(--border2);
    color: var(--text); font-family: var(--font); font-size: .95rem; font-weight: 600;
    cursor: pointer; transition: border-color .2s, background .2s;
    display: flex; align-items: center; justify-content: center; gap: .75rem;
  }
  .btn-github:hover { border-color: var(--accent2); background: rgba(124,108,252,.05); }
  .err-box {
    background: rgba(239,68,68,.08); border: 1px solid rgba(239,68,68,.25);
    border-radius: 8px; padding: .75rem 1rem;
    color: #f87171; font-size: .875rem; margin-bottom: 1rem;
  }
  .footer-link { text-align: center; margin-top: 1.5rem; font-size: .875rem; color: var(--muted2); }
  .footer-link a { color: var(--accent2); text-decoration: none; font-weight: 600; }
  .footer-link a:hover { text-decoration: underline; }
`;

export default function Login() {
  const [email, setEmail]     = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  const navigate = useNavigate();

  async function handleLogin(e) {
    e.preventDefault();
    setError(""); setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    setLoading(false);
    if (error) { setError(error.message); return; }
    navigate("/dashboard");
  }

  async function handleGitHub() {
    setError("");
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "github",
      options: { redirectTo: `${window.location.origin}/dashboard` },
    });
    if (error) setError(error.message);
  }

  return (
    <>
      <style>{STYLES}</style>
      <div className="auth-wrap">
        <div className="auth-card">
          <div className="auth-logo">NeoBugForge</div>
          <h1>Welcome back</h1>
          <p className="subtitle">Sign in to access your API key and dashboard.</p>

          {error && <div className="err-box">⚠ {error}</div>}

          <button className="btn-github" onClick={handleGitHub}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
            </svg>
            Continue with GitHub
          </button>

          <div className="divider">or</div>

          <form onSubmit={handleLogin}>
            <div className="field">
              <label>Email</label>
              <input type="email" placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)} required />
            </div>
            <div className="field">
              <label>Password</label>
              <input type="password" placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)} required />
            </div>
            <button className="btn-primary" disabled={loading}>
              {loading ? "Signing in..." : "Sign in →"}
            </button>
          </form>

          <div className="footer-link">
            Don't have an account? <Link to="/signup">Sign up free</Link>
          </div>
        </div>
      </div>
    </>
  );
}
