import { useState, useEffect, useRef, useCallback } from "react";

/* ─────────────────────────────────────────────────────────────────────────────
   Neo Bug Forge  —  Landing Page v2
   Redesigned: hero GIF, features, pricing, live demo
───────────────────────────────────────────────────────────────────────────── */

const STYLES = `
  @import url('https://fonts.googleapis.com/css2?family=Azeret+Mono:wght@300;400;500;600;700&family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');

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

  body::before {
    content: '';
    position: fixed; inset: 0; z-index: 0;
    opacity: 0.02;
    pointer-events: none;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
    background-size: 200px;
  }

  ::-webkit-scrollbar { width: 3px; }
  ::-webkit-scrollbar-track { background: var(--obsidian); }
  ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 1px; }

  /* ── Announcement bar ── */
  .announce-bar {
    position: fixed; top: 0; left: 0; right: 0; z-index: 101;
    background: var(--amber); color: #000;
    text-align: center; font-family: var(--mono);
    font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
    padding: 7px 16px;
    display: flex; align-items: center; justify-content: center; gap: 10px;
  }
  .announce-bar .spots {
    background: #000; color: var(--amber);
    padding: 2px 8px; border-radius: 2px; font-size: 11px;
  }
  .announce-bar .announce-cta {
    background: transparent; border: 1.5px solid #000; color: #000;
    padding: 2px 10px; border-radius: 2px;
    font-family: var(--mono); font-size: 10px; font-weight: 700;
    letter-spacing: .08em; text-transform: uppercase;
    cursor: pointer; transition: all .15s; text-decoration: none;
  }
  .announce-bar .announce-cta:hover { background: #00000018; }

  /* ── Nav ── */
  .nav {
    position: fixed; top: 33px; left: 0; right: 0; z-index: 100;
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 40px; height: 54px;
    background: rgba(8,8,8,.92);
    border-bottom: 1px solid var(--border);
    backdrop-filter: blur(12px);
  }
  .nav-logo { font-family: var(--display); font-size: 22px; letter-spacing: .06em; color: var(--amber); }
  .nav-logo span { color: var(--text); }
  .nav-links { display: flex; align-items: center; gap: 28px; }
  .nav-link {
    font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase;
    color: var(--text3); text-decoration: none; cursor: pointer; transition: color .15s;
  }
  .nav-link:hover { color: var(--text); }
  .nav-cta {
    font-family: var(--mono); font-size: 10px; font-weight: 700;
    letter-spacing: .1em; text-transform: uppercase;
    padding: 8px 18px; background: var(--amber); color: #000;
    border: none; border-radius: 2px; cursor: pointer; transition: background .15s;
    text-decoration: none;
  }
  .nav-cta:hover { background: var(--amber-dim); }

  /* ── Hero ── */
  .hero {
    min-height: 100vh;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    padding: 160px 24px 80px;
    position: relative; text-align: center; overflow: hidden;
  }
  .hero-grid {
    position: absolute; inset: 0; z-index: 0; opacity: .03;
    background-image:
      linear-gradient(var(--border) 1px, transparent 1px),
      linear-gradient(90deg, var(--border) 1px, transparent 1px);
    background-size: 40px 40px;
  }
  .hero-glow {
    position: absolute; top: 35%; left: 50%; transform: translate(-50%, -50%);
    width: 700px; height: 350px;
    background: radial-gradient(ellipse, #ffb40012 0%, transparent 70%);
    pointer-events: none; z-index: 0;
  }
  .hero-eyebrow {
    font-size: 10px; font-weight: 700; letter-spacing: .2em; text-transform: uppercase;
    color: var(--amber); margin-bottom: 20px;
    position: relative; z-index: 1;
    animation: fadeUp .6s ease both;
  }
  .hero-title {
    font-family: var(--display);
    font-size: clamp(64px, 11vw, 130px);
    line-height: .9; letter-spacing: .03em; color: var(--text);
    position: relative; z-index: 1;
    animation: fadeUp .6s .1s ease both;
  }
  .hero-title .accent { color: var(--amber); }
  .hero-sub {
    font-family: var(--body); font-size: 17px; font-weight: 300;
    color: var(--text2); max-width: 520px; line-height: 1.75;
    margin: 24px auto 0;
    position: relative; z-index: 1;
    animation: fadeUp .6s .2s ease both;
  }
  .hero-actions {
    display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;
    margin-top: 36px; position: relative; z-index: 1;
    animation: fadeUp .6s .3s ease both;
  }
  .btn-primary {
    font-family: var(--display); font-size: 18px; letter-spacing: .1em;
    padding: 14px 36px; background: var(--amber); color: #000;
    border: none; border-radius: 3px; cursor: pointer; transition: all .15s;
    text-decoration: none; display: inline-block;
  }
  .btn-primary:hover { background: var(--amber-dim); transform: translateY(-1px); }
  .btn-secondary {
    font-family: var(--mono); font-size: 11px; font-weight: 700; letter-spacing: .1em;
    text-transform: uppercase; padding: 14px 28px;
    background: transparent; color: var(--text2);
    border: 1px solid var(--border2); border-radius: 3px;
    cursor: pointer; transition: all .15s; text-decoration: none; display: inline-block;
  }
  .btn-secondary:hover { border-color: var(--text2); color: var(--text); }
  .hero-badges {
    display: flex; gap: 8px; justify-content: center; flex-wrap: wrap;
    margin-top: 24px; position: relative; z-index: 1;
    animation: fadeUp .6s .4s ease both;
  }
  .badge {
    font-size: 9px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase;
    padding: 4px 12px; border-radius: 2px;
    border: 1px solid var(--border2); color: var(--text3);
  }
  .badge.amber { border-color: var(--amber); color: var(--amber); background: var(--amber-faint); }

  /* ── Demo GIF ── */
  .demo-wrap {
    position: relative; z-index: 1; margin-top: 56px;
    animation: fadeUp .6s .5s ease both;
    width: 100%; max-width: 860px;
  }
  .demo-frame {
    border: 1px solid var(--border2); border-radius: 6px; overflow: hidden;
    box-shadow: 0 0 80px rgba(255,180,0,.06), 0 40px 120px rgba(0,0,0,.6);
  }
  .demo-frame-bar {
    background: var(--surface2); padding: 9px 14px;
    display: flex; align-items: center; gap: 7px;
    border-bottom: 1px solid var(--border);
  }
  .dot-r { width:10px; height:10px; border-radius:50%; background:#ff5f57; }
  .dot-y { width:10px; height:10px; border-radius:50%; background:#ffbd2e; }
  .dot-g { width:10px; height:10px; border-radius:50%; background:#28ca41; }
  .demo-frame-title {
    flex: 1; text-align: center; font-size: 10px; font-weight: 700;
    letter-spacing: .08em; text-transform: uppercase; color: var(--text3);
  }
  .demo-frame img { width: 100%; display: block; }

  /* ── Stats ── */
  .stats-section { position: relative; z-index: 1; }
  .stats-bar {
    display: flex; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
    overflow: hidden;
  }
  .stat-cell {
    flex: 1; padding: 24px 20px; background: var(--surface);
    border-right: 1px solid var(--border); text-align: center;
  }
  .stat-cell:last-child { border-right: none; }
  .stat-num { font-family: var(--display); font-size: 40px; letter-spacing: .04em; color: var(--amber); line-height: 1; }
  .stat-label { font-size: 9px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--text3); margin-top: 5px; }

  /* ── Section wrapper ── */
  .section { max-width: 1100px; margin: 0 auto; padding: 100px 24px; position: relative; z-index: 1; }
  .section-eyebrow {
    font-size: 10px; font-weight: 700; letter-spacing: .2em; text-transform: uppercase;
    color: var(--amber); margin-bottom: 14px;
  }
  .section-title {
    font-family: var(--display); font-size: clamp(36px, 5vw, 60px);
    letter-spacing: .04em; color: var(--text); margin-bottom: 16px; line-height: 1;
  }
  .section-sub {
    font-family: var(--body); font-size: 15px; font-weight: 300;
    color: var(--text2); max-width: 480px; line-height: 1.7;
  }

  /* ── Features ── */
  .features-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px;
    background: var(--border); border: 1px solid var(--border);
    border-radius: 4px; overflow: hidden; margin-top: 56px;
  }
  @media (max-width: 768px) { .features-grid { grid-template-columns: 1fr; } }
  @media (min-width: 769px) and (max-width: 1024px) { .features-grid { grid-template-columns: 1fr 1fr; } }
  .feature-card {
    background: var(--surface); padding: 28px 24px;
    transition: background .2s;
  }
  .feature-card:hover { background: var(--surface2); }
  .feature-icon { font-size: 24px; margin-bottom: 14px; }
  .feature-title {
    font-family: var(--display); font-size: 20px; letter-spacing: .04em;
    color: var(--text); margin-bottom: 8px;
  }
  .feature-desc {
    font-family: var(--body); font-size: 13px; font-weight: 300;
    color: var(--text2); line-height: 1.7;
  }
  .feature-tag {
    display: inline-block; margin-top: 12px;
    font-size: 8px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase;
    padding: 3px 8px; border-radius: 2px;
    background: var(--amber-faint); border: 1px solid var(--amber);
    color: var(--amber);
  }

  /* ── How it works ── */
  .steps-row {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px;
    background: var(--border); border: 1px solid var(--border);
    border-radius: 4px; overflow: hidden; margin-top: 56px;
  }
  @media (max-width: 768px) { .steps-row { grid-template-columns: 1fr; } }
  .step-card { background: var(--surface); padding: 32px 28px; position: relative; }
  .step-num {
    font-family: var(--display); font-size: 80px; letter-spacing: -.02em;
    color: var(--border2); line-height: 1; margin-bottom: 16px;
  }
  .step-title {
    font-family: var(--display); font-size: 22px; letter-spacing: .04em;
    color: var(--text); margin-bottom: 10px;
  }
  .step-desc { font-family: var(--body); font-size: 13px; font-weight: 300; color: var(--text2); line-height: 1.7; }
  .step-code {
    display: inline-block; margin-top: 12px;
    font-size: 11px; font-family: var(--mono); font-weight: 700;
    padding: 4px 10px; background: var(--surface2);
    border: 1px solid var(--border2); border-radius: 3px; color: var(--amber);
  }

  /* ── Pricing ── */
  .pricing-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
    margin-top: 56px;
  }
  @media (max-width: 768px) { .pricing-grid { grid-template-columns: 1fr; } }
  .pricing-card {
    background: var(--surface); border: 1px solid var(--border2);
    border-radius: 4px; padding: 32px 28px;
    display: flex; flex-direction: column; gap: 0;
    position: relative; transition: border-color .2s;
  }
  .pricing-card:hover { border-color: var(--border2); }
  .pricing-card.featured {
    border-color: var(--amber);
    box-shadow: 0 0 40px rgba(255,180,0,.08);
  }
  .pricing-badge {
    position: absolute; top: -1px; left: 50%; transform: translateX(-50%);
    font-size: 8px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
    padding: 3px 14px; background: var(--amber); color: #000;
    border-radius: 0 0 4px 4px;
  }
  .pricing-plan {
    font-size: 9px; font-weight: 700; letter-spacing: .15em; text-transform: uppercase;
    color: var(--text3); margin-bottom: 16px;
  }
  .pricing-price {
    font-family: var(--display); font-size: 52px; letter-spacing: -.01em;
    color: var(--text); line-height: 1; margin-bottom: 4px;
  }
  .pricing-price span { font-family: var(--mono); font-size: 14px; font-weight: 400; color: var(--text3); }
  .pricing-period { font-size: 10px; color: var(--text3); margin-bottom: 28px; }
  .pricing-features { list-style: none; display: flex; flex-direction: column; gap: 10px; flex: 1; margin-bottom: 28px; }
  .pricing-features li {
    font-family: var(--body); font-size: 13px; color: var(--text2);
    display: flex; align-items: flex-start; gap: 8px;
  }
  .pricing-features li::before { content: '✓'; color: var(--amber); font-weight: 700; flex-shrink: 0; }
  .pricing-cta {
    width: 100%; padding: 12px; border-radius: 3px;
    font-family: var(--display); font-size: 16px; letter-spacing: .08em;
    cursor: pointer; transition: all .15s; text-align: center; text-decoration: none;
    display: block;
  }
  .pricing-cta.primary { background: var(--amber); color: #000; border: none; }
  .pricing-cta.primary:hover { background: var(--amber-dim); }
  .pricing-cta.ghost { background: transparent; color: var(--text2); border: 1px solid var(--border2); }
  .pricing-cta.ghost:hover { border-color: var(--text2); color: var(--text); }

  /* ── CTA banner ── */
  .cta-banner {
    background: var(--surface); border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
    padding: 80px 24px; text-align: center; position: relative; z-index: 1; overflow: hidden;
  }
  .cta-banner-glow {
    position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
    width: 500px; height: 200px;
    background: radial-gradient(ellipse, #ffb40010 0%, transparent 70%);
    pointer-events: none;
  }
  .cta-banner h2 {
    font-family: var(--display); font-size: clamp(36px, 6vw, 72px);
    letter-spacing: .04em; color: var(--text); margin-bottom: 16px;
    position: relative; z-index: 1;
  }
  .cta-banner p {
    font-family: var(--body); font-size: 15px; color: var(--text2);
    margin-bottom: 32px; position: relative; z-index: 1;
  }

  /* ── Live demo section ── */
  .demo-section { background: var(--surface); border-top: 1px solid var(--border); }
  .demo-section .section { padding-top: 80px; padding-bottom: 80px; }
  .demo-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 2px;
    background: var(--border); border: 1px solid var(--border);
    border-radius: 4px; overflow: hidden; margin-top: 40px;
  }
  @media (max-width: 768px) { .demo-grid { grid-template-columns: 1fr; } }

  /* ── Input panel ── */
  .panel { background: var(--obsidian); padding: 20px; display: flex; flex-direction: column; gap: 14px; min-height: 480px; }
  .panel-title {
    font-size: 9px; font-weight: 700; letter-spacing: .15em; text-transform: uppercase;
    color: var(--text3); display: flex; align-items: center; gap: 8px;
  }
  .panel-title::after { content: ''; flex: 1; height: 1px; background: var(--border2); }
  .panel-title .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--amber); box-shadow: 0 0 8px var(--amber); }

  .lang-grid { display: flex; flex-wrap: wrap; gap: 5px; }
  .lang-chip {
    font-size: 9px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
    padding: 4px 10px; border-radius: 2px; border: 1px solid var(--border2);
    color: var(--text3); cursor: pointer; background: transparent; font-family: var(--mono); transition: all .12s;
  }
  .lang-chip:hover { border-color: var(--amber-dim); color: var(--text); }
  .lang-chip.active { border-color: var(--amber); color: var(--amber); background: var(--amber-faint); }

  textarea {
    width: 100%; background: var(--surface2); border: 1px solid var(--border2); border-radius: 3px;
    color: var(--text); font-family: var(--mono); font-size: 12px; line-height: 1.65;
    padding: 12px 14px; resize: vertical; outline: none; transition: border-color .15s;
  }
  textarea:focus { border-color: var(--amber); }
  textarea::placeholder { color: var(--text3); }
  .code-ta { min-height: 180px; }
  .error-ta { min-height: 60px; }
  .field-meta { display: flex; justify-content: space-between; align-items: center; margin-top: -8px; }
  .field-hint { font-size: 9px; color: var(--text3); letter-spacing: .05em; }
  .char-count { font-size: 9px; color: var(--text3); }

  .fix-btn {
    width: 100%; padding: 13px; font-family: var(--display); font-size: 19px; letter-spacing: .1em;
    background: var(--amber); color: #000; border: none; border-radius: 3px;
    cursor: pointer; transition: all .15s;
  }
  .fix-btn:hover:not(:disabled) { background: var(--amber-dim); transform: translateY(-1px); }
  .fix-btn:disabled { background: var(--surface3); color: var(--text3); cursor: not-allowed; transform: none; }

  .free-note { text-align: center; font-size: 9px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--text3); }
  .free-note strong { color: var(--amber); }

  /* ── Result panel ── */
  .result-panel-wrap { background: var(--obsidian); display: flex; flex-direction: column; min-height: 480px; }
  .loading-wrap { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; }
  .loader-ring { width: 44px; height: 44px; border: 2px solid var(--border2); border-top-color: var(--amber); border-radius: 50%; animation: spin .7s linear infinite; }
  .loader-steps { display: flex; flex-direction: column; gap: 6px; width: 200px; }
  .loader-step { font-size: 10px; color: var(--text3); letter-spacing: .06em; display: flex; align-items: center; gap: 8px; transition: color .3s; }
  .loader-step.active { color: var(--amber); }
  .loader-step.done { color: var(--green); }
  .step-dot { width: 5px; height: 5px; border-radius: 50%; background: currentColor; flex-shrink: 0; }

  .meta-strip { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 10px 14px; background: var(--surface2); border-bottom: 1px solid var(--border2); flex-shrink: 0; }
  .conf-badge { font-size: 10px; font-weight: 700; padding: 3px 10px; border-radius: 2px; letter-spacing: .05em; }
  .conf-high { background: #00e67615; color: var(--green); border: 1px solid #00e67630; }
  .conf-mid  { background: #ffb40015; color: var(--amber); border: 1px solid #ffb40030; }
  .conf-low  { background: #ff3b3b15; color: var(--red);   border: 1px solid #ff3b3b30; }
  .cause-tag { font-size: 9px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; padding: 3px 10px; border-radius: 2px; background: var(--surface3); color: var(--blue); border: 1px solid #4da6ff25; }
  .meta-spacer { flex: 1; }
  .copy-all-btn { font-family: var(--mono); font-size: 9px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; padding: 4px 10px; border-radius: 2px; background: transparent; color: var(--text3); border: 1px solid var(--border2); cursor: pointer; transition: all .12s; }
  .copy-all-btn:hover { border-color: var(--amber); color: var(--amber); }

  .tabs-bar { display: flex; border-bottom: 1px solid var(--border2); background: var(--surface2); flex-shrink: 0; }
  .tab-btn { font-family: var(--mono); font-size: 9px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; padding: 8px 16px; border: none; background: none; color: var(--text3); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; transition: all .12s; }
  .tab-btn:hover { color: var(--text); }
  .tab-btn.active { color: var(--amber); border-bottom-color: var(--amber); }

  .tab-content { flex: 1; overflow-y: auto; padding: 14px; }
  .expl-card { background: var(--surface2); border-left: 3px solid var(--amber); border-radius: 0 3px 3px 0; padding: 12px 14px; font-family: var(--body); font-size: 13px; font-weight: 300; line-height: 1.75; color: #ccc; margin-bottom: 14px; }
  .code-display { background: var(--surface2); border: 1px solid var(--border2); border-radius: 3px; overflow: hidden; }
  .code-display-header { display: flex; justify-content: space-between; align-items: center; padding: 7px 12px; background: var(--surface3); border-bottom: 1px solid var(--border); }
  .code-lang-tag { font-size: 9px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--text3); }
  .copy-snippet { font-family: var(--mono); font-size: 9px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; padding: 3px 8px; border-radius: 2px; background: transparent; color: var(--text3); border: 1px solid var(--border2); cursor: pointer; transition: all .12s; }
  .copy-snippet:hover { border-color: var(--amber); color: var(--amber); }
  .copy-snippet.copied { border-color: var(--green); color: var(--green); }
  .code-display pre { padding: 14px; font-size: 11.5px; line-height: 1.65; overflow-x: auto; color: var(--text); font-family: var(--mono); }

  .diff-line { display: block; }
  .diff-add { color: var(--green); background: #00e67608; }
  .diff-del { color: var(--red);   background: #ff3b3b08; }
  .diff-hdr { color: var(--blue);  font-weight: 700; }
  .diff-ctx { color: var(--text3); }

  .action-row { display: flex; gap: 8px; padding: 12px 14px; border-top: 1px solid var(--border2); background: var(--surface2); flex-shrink: 0; }
  .act-btn { flex: 1; padding: 9px; border-radius: 3px; font-family: var(--mono); font-size: 10px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; cursor: pointer; border: 1px solid var(--border2); transition: all .15s; }
  .act-primary { background: var(--amber); color: #000; border-color: var(--amber); }
  .act-primary:hover { background: var(--amber-dim); }
  .act-secondary { background: transparent; color: var(--text); }
  .act-secondary:hover { border-color: var(--text2); }

  .empty-state { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12px; color: var(--text3); text-align: center; padding: 40px; }
  .empty-icon { font-size: 40px; opacity: .3; }
  .empty-title { font-family: var(--display); font-size: 24px; letter-spacing: .05em; color: var(--border2); }
  .empty-hint { font-size: 10px; letter-spacing: .08em; line-height: 1.8; }
  .err-box { background: #ff3b3b10; border: 1px solid #ff3b3b30; border-radius: 3px; padding: 12px 14px; color: var(--red); font-size: 11px; line-height: 1.6; animation: fadeUp .2s ease; }

  /* ── Footer ── */
  .footer {
    border-top: 1px solid var(--border); padding: 36px 40px;
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px;
    position: relative; z-index: 1;
  }
  .footer-logo { font-family: var(--display); font-size: 20px; letter-spacing: .05em; color: var(--text3); }
  .footer-links { display: flex; gap: 24px; }
  .footer-link { font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--text3); text-decoration: none; cursor: pointer; transition: color .12s; }
  .footer-link:hover { color: var(--amber); }
  .footer-copy { font-size: 9px; color: var(--text3); letter-spacing: .06em; }

  /* ── Toast ── */
  .toast { position: fixed; bottom: 24px; right: 24px; z-index: 999; background: var(--surface2); border: 1px solid var(--green); color: var(--green); font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; padding: 10px 18px; border-radius: 3px; animation: slideIn .2s ease, fadeOut .3s 1.8s ease forwards; pointer-events: none; }

  /* ── Animations ── */
  @keyframes fadeUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; } }
  @keyframes spin { to { transform: rotate(360deg); } }
  @keyframes slideIn { from { transform: translateX(20px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
  @keyframes fadeOut { to { opacity: 0; transform: translateY(4px); } }
`;

const LANGS = [
  { id: "python",     label: "Python" },
  { id: "javascript", label: "JS" },
  { id: "typescript", label: "TS" },
  { id: "rust",       label: "Rust" },
  { id: "go",         label: "Go" },
  { id: "java",       label: "Java" },
  { id: "cpp",        label: "C++" },
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
  null_reference: "Null Reference", type_mismatch: "Type Mismatch",
  off_by_one: "Off-by-One", async_race: "Async / Race",
  scope_error: "Scope Error", logic_error: "Logic Error",
  syntax_error: "Syntax Error", import_error: "Import Error",
  index_error: "Index Error", other: "Other",
};

const FEATURES = [
  { icon: "⚡", title: "Fix in Seconds", desc: "Select broken code, press Ctrl+Shift+F, paste the error. Get back fixed code with explanation in under 3 seconds.", tag: null },
  { icon: "🔍", title: "Deeper Context", desc: "Auto-scans your workspace for related files and sends them to Claude so fixes are accurate — not just the 10 lines you selected.", tag: "v1.3" },
  { icon: "🔀", title: "Diff Preview", desc: "See exactly what changed in VS Code's native diff editor before applying anything. No accidental overwrites.", tag: "v1.1" },
  { icon: "↺",  title: "Try Again",     desc: "Not quite right? Add a note explaining what's still wrong and retry — the AI learns from your feedback.", tag: "v1.1" },
  { icon: "🧪", title: "Test Case",      desc: "Every fix includes a minimal unit test that would have caught the bug. Copy it straight into your test suite.", tag: null },
  { icon: "📊", title: "Confidence Score", desc: "Know how certain Claude is about the fix (0–100%). Low confidence? Review the explanation before applying.", tag: null },
];

const STEPS = [
  { num: "01", title: "Select the broken code", desc: "Highlight the buggy function or snippet in any VS Code file.", code: "Select + Ctrl+Shift+F" },
  { num: "02", title: "Paste the error message", desc: "Drop in the stack trace or describe the bug. Neo Bug Forge scans your workspace for related files automatically.", code: null },
  { num: "03", title: "Apply the fix", desc: "Review the diff, read the explanation, check the confidence score — then apply with one click.", code: "✓ Apply + Git Stage" },
];

const MAX_CODE_LENGTH = 5000;

async function callClaude(code, errorMsg, language) {
  const API_BASE = import.meta.env.VITE_API_URL || "https://api.neobugforge.io";
  const response = await fetch(`${API_BASE}/v1/fix/public`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ broken_code: code, error_message: errorMsg || "", language: language || "" }),
  });
  if (!response.ok) {
    if (response.status === 429) throw new Error("Daily free limit reached (10 fixes/day).");
    const err = await response.json().catch(() => ({}));
    throw new Error(err?.detail || `API error ${response.status}`);
  }
  return response.json();
}

function confClass(n) { return n >= 80 ? "conf-high" : n >= 50 ? "conf-mid" : "conf-low"; }

function parseDiff(diff) {
  return (diff || "").split("\n").map((line, i) => {
    const cls = line.startsWith("+++") || line.startsWith("---") ? "diff-hdr" :
      line.startsWith("+") ? "diff-add" : line.startsWith("-") ? "diff-del" : "diff-ctx";
    return <span key={i} className={`diff-line ${cls}`}>{line + "\n"}</span>;
  });
}

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

export default function NeoBugForgeApp() {
  const [code, setCode]         = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [lang, setLang]         = useState("python");
  const [status, setStatus]     = useState("idle");
  const [result, setResult]     = useState(null);
  const [apiErr, setApiErr]     = useState("");
  const [activeTab, setActiveTab]   = useState("fixed");
  const [toast, setToast]           = useState("");
  const [loaderStep, setLoaderStep] = useState(0);
  const [copiedSnippet, setCopiedSnippet] = useState("");
  const [validationErr, setValidationErr] = useState("");
  const demoRef  = useRef(null);
  const stepTimer = useRef(null);

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
      showToast("Copied!");
      setTimeout(() => setCopiedSnippet(""), 1500);
    });
  }, [showToast]);

  const handleFix = useCallback(async () => {
    setValidationErr("");
    if (!code.trim()) { setValidationErr("Please paste some code first."); return; }
    if (code.length > MAX_CODE_LENGTH) { setValidationErr(`Too long (${code.length} chars, limit ${MAX_CODE_LENGTH}).`); return; }
    setStatus("loading"); setApiErr(""); setResult(null); setActiveTab("fixed");
    try {
      const res = await callClaude(code, errorMsg, lang);
      setResult(res); setStatus("result");
    } catch (e) {
      setApiErr(e.message || "Something went wrong.");
      setStatus("error");
    }
  }, [code, errorMsg, lang]);

  const handleReset = () => { setStatus("idle"); setResult(null); setCode(""); setErrorMsg(""); setApiErr(""); setValidationErr(""); };

  return (
    <>
      <style>{STYLES}</style>

      {/* Announcement bar */}
      <div className="announce-bar">
        ⭐ Leave a review on the VS Code Marketplace — first 50 reviewers get Pro FREE
        <span className="spots">37 spots left</span>
        <a href="https://marketplace.visualstudio.com/items?itemName=neobugforge.neo-bug-forge&ssr=false#review-details" className="announce-cta">Leave Review →</a>
      </div>

      {/* Nav */}
      <nav className="nav">
        <div className="nav-logo">Neo Bug<span>Forge</span></div>
        <div className="nav-links">
          <span className="nav-link" onClick={() => demoRef.current?.scrollIntoView({ behavior: "smooth" })}>Try It</span>
          <a className="nav-link" href="#features">Features</a>
          <a className="nav-link" href="#pricing">Pricing</a>
          <a className="nav-link" href="https://marketplace.visualstudio.com/items?itemName=neobugforge.neo-bug-forge">VS Code</a>
        </div>
        <a className="nav-cta" href="https://app.neobugforge.io/signup">Get Started Free →</a>
      </nav>

      {/* Hero */}
      <section className="hero">
        <div className="hero-grid" />
        <div className="hero-glow" />
        <div className="hero-eyebrow">⚡ Powered by Claude AI · VS Code Extension</div>
        <h1 className="hero-title">
          STOP<br/>
          <span className="accent">DEBUGGING.</span><br/>
          START SHIPPING.
        </h1>
        <p className="hero-sub">
          Select broken code, press Ctrl+Shift+F. Get fixed code, a root cause analysis, a diff, and a test case — in seconds.
        </p>
        <div className="hero-actions">
          <a className="btn-primary" href="https://app.neobugforge.io/signup">Get Started Free</a>
          <a className="btn-secondary" href="https://marketplace.visualstudio.com/items?itemName=neobugforge.neo-bug-forge">Install VS Code Extension</a>
        </div>
        <div className="hero-badges">
          <span className="badge amber">⭐ Leave review — get Pro FREE</span>
          <span className="badge">10 free fixes · no card</span>
          <span className="badge">Claude AI</span>
          <span className="badge">Diff preview</span>
          <span className="badge">Test case included</span>
        </div>

        {/* Demo GIF */}
        <div className="demo-wrap">
          <div className="demo-frame">
            <div className="demo-frame-bar">
              <div className="dot-r" /><div className="dot-y" /><div className="dot-g" />
              <div className="demo-frame-title">Neo Bug Forge — VS Code Extension</div>
            </div>
            <img
              src="https://raw.githubusercontent.com/networkhack52/neo-bug-forge/main/media/demo.gif"
              alt="Neo Bug Forge demo — select code, get fix"
              loading="lazy"
            />
          </div>
        </div>
      </section>

      {/* Stats */}
      <div className="stats-section">
        <div className="stats-bar">
          {[
            { num: 248193, label: "Bugs Fixed" },
            { num: 94,     label: "% Accuracy" },
            { num: 2.1,    label: "Avg Seconds", fmt: n => n.toFixed(1) + "s" },
            { num: 113,    label: "Developers" },
          ].map(({ num, label, fmt }) => (
            <div key={label} className="stat-cell">
              <div className="stat-num">{fmt ? fmt(num) : <AnimCounter target={num} />}</div>
              <div className="stat-label">{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Features */}
      <section id="features">
        <div className="section">
          <div className="section-eyebrow">What you get</div>
          <div className="section-title">Everything you need.<br/>Nothing you don't.</div>
          <div className="section-sub">Built for developers who want fast, accurate fixes — not a chatbot that makes you paste context manually.</div>
          <div className="features-grid">
            {FEATURES.map(f => (
              <div key={f.title} className="feature-card">
                <div className="feature-icon">{f.icon}</div>
                <div className="feature-title">{f.title}</div>
                <div className="feature-desc">{f.desc}</div>
                {f.tag && <span className="feature-tag">New in {f.tag}</span>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section style={{ background: "var(--surface)", borderTop: "1px solid var(--border)", borderBottom: "1px solid var(--border)" }}>
        <div className="section">
          <div className="section-eyebrow">How it works</div>
          <div className="section-title">Three steps.<br/>Zero context switching.</div>
          <div className="steps-row">
            {STEPS.map(s => (
              <div key={s.num} className="step-card">
                <div className="step-num">{s.num}</div>
                <div className="step-title">{s.title}</div>
                <div className="step-desc">{s.desc}</div>
                {s.code && <span className="step-code">{s.code}</span>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing">
        <div className="section">
          <div className="section-eyebrow">Pricing</div>
          <div className="section-title">Start free.<br/>Scale when ready.</div>
          <div className="section-sub">No credit card required to start. Cancel anytime.</div>
          <div className="pricing-grid">
            <div className="pricing-card">
              <div className="pricing-plan">Free</div>
              <div className="pricing-price">$0</div>
              <div className="pricing-period">forever</div>
              <ul className="pricing-features">
                <li>100 fixes per month</li>
                <li>All languages</li>
                <li>Diff preview</li>
                <li>Test case included</li>
                <li>Confidence score</li>
              </ul>
              <a className="pricing-cta ghost" href="https://app.neobugforge.io/signup">Get Started</a>
            </div>
            <div className="pricing-card featured">
              <div className="pricing-badge">Most Popular</div>
              <div className="pricing-plan">Pro</div>
              <div className="pricing-price">$12<span>.99/mo</span></div>
              <div className="pricing-period">billed monthly</div>
              <ul className="pricing-features">
                <li>500 fixes per month</li>
                <li>Deeper Context (auto workspace scan)</li>
                <li>Priority fixes</li>
                <li>All Free features</li>
                <li>Email support</li>
              </ul>
              <a className="pricing-cta primary" href="https://app.neobugforge.io/signup">Start Pro</a>
            </div>
            <div className="pricing-card">
              <div className="pricing-plan">Team</div>
              <div className="pricing-price">$49.99<span>/mo</span></div>
              <div className="pricing-period">billed monthly</div>
              <ul className="pricing-features">
                <li>Unlimited fixes (fair use)</li>
                <li>Up to 10 seats</li>
                <li>All Pro features</li>
                <li>Priority support</li>
                <li>Early access to new features</li>
              </ul>
              <a className="pricing-cta ghost" href="https://app.neobugforge.io/signup">Start Team</a>
            </div>
          </div>
        </div>
      </section>

      {/* Live demo */}
      <div className="demo-section" ref={demoRef}>
        <div className="section">
          <div className="section-eyebrow">Try it live</div>
          <div className="section-title">Paste code. Get fix.</div>
          <div className="section-sub">No account needed — 10 free fixes per day.</div>
          <div className="demo-grid">
            {/* Input */}
            <div className="panel">
              <div className="panel-title"><span className="dot" />Input</div>
              <div>
                <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: ".12em", textTransform: "uppercase", color: "var(--text3)", marginBottom: 7 }}>Language</div>
                <div className="lang-grid">
                  {LANGS.map(l => (
                    <button key={l.id} className={`lang-chip ${lang === l.id ? "active" : ""}`} onClick={() => setLang(l.id)}>{l.label}</button>
                  ))}
                </div>
              </div>
              <div>
                <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: ".12em", textTransform: "uppercase", color: "var(--text3)", marginBottom: 6 }}>Broken Code</div>
                <textarea className="code-ta" placeholder={"def calculate_average(nums):\n    return sum(nums) / len(nums)\n\nresult = calculate_average([])"} value={code} onChange={e => setCode(e.target.value)} onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") handleFix(); }} style={{ borderColor: validationErr && !code.trim() ? "var(--red)" : undefined }} />
                <div className="field-meta">
                  <span className="field-hint">Ctrl+Enter to submit</span>
                  <span className="char-count" style={{ color: code.length > MAX_CODE_LENGTH ? "var(--red)" : "var(--text3)" }}>{code.length}/{MAX_CODE_LENGTH}</span>
                </div>
              </div>
              <div>
                <div style={{ fontSize: 9, fontWeight: 700, letterSpacing: ".12em", textTransform: "uppercase", color: "var(--text3)", marginBottom: 6 }}>Error Message</div>
                <textarea className="error-ta" placeholder="ZeroDivisionError: division by zero" value={errorMsg} onChange={e => setErrorMsg(e.target.value)} onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === "Enter") handleFix(); }} />
              </div>
              {validationErr && <div className="err-box">✗ {validationErr}</div>}
              {status === "error" && <div className="err-box">✗ {apiErr}</div>}
              <button className="fix-btn" onClick={handleFix} disabled={status === "loading" || !code.trim()}>
                {status === "loading" ? "ANALYZING..." : "⚡ FIX MY BUG"}
              </button>
              <div className="free-note"><strong>10 free fixes</strong> · No signup required</div>
            </div>

            {/* Result */}
            <div className="result-panel-wrap">
              {status === "idle" && (
                <div className="empty-state">
                  <div className="empty-icon">⌥</div>
                  <div className="empty-title">Awaiting Input</div>
                  <div className="empty-hint">Paste broken code on the left<br/>and hit ⚡ Fix My Bug</div>
                </div>
              )}
              {status === "loading" && (
                <div className="loading-wrap">
                  <div className="loader-ring" />
                  <div className="loader-steps">
                    {LOADER_STEPS.map((s, i) => (
                      <div key={i} className={`loader-step ${i < loaderStep ? "done" : i === loaderStep ? "active" : ""}`}>
                        <div className="step-dot" />{i < loaderStep ? "✓ " : ""}{s}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {status === "result" && result && (
                <>
                  <div className="meta-strip">
                    <div className={`conf-badge ${confClass(result.confidence)}`}>{result.confidence}% confident</div>
                    <div className="cause-tag">{ROOT_CAUSE_LABELS[result.root_cause] ?? result.root_cause}</div>
                    <div className="meta-spacer" />
                    <button className="copy-all-btn" onClick={() => handleCopy(result.fixed_code, "all")}>{copiedSnippet === "all" ? "✓ Copied" : "⧉ Copy Fix"}</button>
                  </div>
                  <div className="tabs-bar">
                    {[{ id: "fixed", label: "Fixed Code" }, { id: "diff", label: "Diff" }, { id: "test", label: "Test Case" }, { id: "explain", label: "Explanation" }].map(t => (
                      <button key={t.id} className={`tab-btn ${activeTab === t.id ? "active" : ""}`} onClick={() => setActiveTab(t.id)}>{t.label}</button>
                    ))}
                  </div>
                  <div className="tab-content">
                    {activeTab === "explain" && <div className="expl-card">{result.explanation}</div>}
                    {(activeTab === "fixed" || activeTab === "test") && (
                      <div className="code-display">
                        <div className="code-display-header">
                          <span className="code-lang-tag">{lang || "code"}</span>
                          <button className={`copy-snippet ${copiedSnippet === activeTab ? "copied" : ""}`} onClick={() => handleCopy(activeTab === "fixed" ? result.fixed_code : result.test_case, activeTab)}>
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
                          <button className={`copy-snippet ${copiedSnippet === "diff" ? "copied" : ""}`} onClick={() => handleCopy(result.diff, "diff")}>{copiedSnippet === "diff" ? "✓ Copied" : "⧉ Copy"}</button>
                        </div>
                        <pre>{parseDiff(result.diff)}</pre>
                      </div>
                    )}
                  </div>
                  <div className="action-row">
                    <button className="act-btn act-primary" onClick={() => handleCopy(result.fixed_code, "act")}>⧉ Copy Fixed Code</button>
                    <button className="act-btn act-secondary" onClick={handleReset}>↺ New Fix</button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* CTA banner */}
      <div className="cta-banner">
        <div className="cta-banner-glow" />
        <h2>READY TO SHIP FASTER?</h2>
        <p>Join 113 developers already using Neo Bug Forge. Free to start, no credit card required.</p>
        <a className="btn-primary" href="https://app.neobugforge.io/signup">Get Started Free →</a>
      </div>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-logo">Neo Bug Forge</div>
        <div className="footer-links">
          <a className="footer-link" href="https://marketplace.visualstudio.com/items?itemName=neobugforge.neo-bug-forge">VS Code</a>
          <a className="footer-link" href="#pricing">Pricing</a>
          <a className="footer-link" href="https://github.com/networkhack52/neo-bug-forge/issues">Issues</a>
          <a className="footer-link" href="mailto:hello@neobugforge.io">Contact</a>
        </div>
        <div className="footer-copy">Powered by Claude · © 2026 Neo Bug Forge</div>
      </footer>

      {toast && <div className="toast">{toast}</div>}
    </>
  );
}
