/**
 * panel.ts  —  Neo Bug Forge Webview Panel
 * ─────────────────────────────────────────
 * v1.1.0 — improved Apply Fix UX:
 *   - "Apply with Diff Preview" opens VS Code native diff editor
 *   - "Try Again" lets user add a note and retry
 *   - Typewriter animation on explanation (streaming feel)
 *   - Git stage option wired through applyFixWithDiff()
 *
 * Message protocol (extension ↔ webview):
 *   webview → extension:  { command: "fix",          payload: { code, error, language } }
 *   webview → extension:  { command: "applyWithDiff", payload: { fixedCode } }
 *   webview → extension:  { command: "copyFix",       payload: { fixedCode } }
 *   webview → extension:  { command: "openSettings" }
 *   webview → extension:  { command: "setApiKey" }
 *   extension → webview:  { command: "prefill",  payload: { code, error, language, fileName } }
 *   extension → webview:  { command: "result",   payload: FixResult }
 *   extension → webview:  { command: "error",    payload: { message } }
 *   extension → webview:  { command: "loading" }
 */

import * as vscode from "vscode";
import * as path   from "path";
import * as fs     from "fs";
import { runBugForge, applyFixWithDiff, trackFixAndPromptReview } from "./extension";

export interface PrefillPayload {
  code:         string;
  error:        string;
  language:     string;
  fileName:     string;
  contextCount?: number;  // number of context files included (shown in UI)
}

export class NeoBugForgePanel {
  public static currentPanel: NeoBugForgePanel | undefined;
  private readonly _panel:   vscode.WebviewPanel;
  private readonly _context: vscode.ExtensionContext;
  private _disposables: vscode.Disposable[] = [];

  // ── Static factory ────────────────────────────────────────────────────────

  public static createOrShow(context: vscode.ExtensionContext) {
    const column = vscode.ViewColumn.Beside;

    if (NeoBugForgePanel.currentPanel) {
      NeoBugForgePanel.currentPanel._panel.reveal(column);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      "bugfixerAI",
      "Neo Bug Forge",
      column,
      {
        enableScripts:          true,
        retainContextWhenHidden: true,
        localResourceRoots: [
          vscode.Uri.file(path.join(context.extensionPath, "media")),
        ],
      }
    );

    NeoBugForgePanel.currentPanel = new NeoBugForgePanel(panel, context);
  }

  // ── Constructor ──────────────────────────────────────────────────────────

  private constructor(panel: vscode.WebviewPanel, context: vscode.ExtensionContext) {
    this._panel   = panel;
    this._context = context;

    this._panel.webview.html = getWebviewContent();

    this._panel.webview.onDidReceiveMessage(
      async (message: { command: string; payload?: unknown }) => {
        switch (message.command) {

          case "fix":
            await this._handleFix(
              message.payload as { code: string; error: string; language: string }
            );
            break;

          case "applyWithDiff": {
            const { fixedCode } = message.payload as { fixedCode: string };
            await applyFixWithDiff(fixedCode);
            break;
          }

          case "copyFix": {
            const { fixedCode } = message.payload as { fixedCode: string };
            await vscode.env.clipboard.writeText(fixedCode);
            vscode.window.showInformationMessage("Neo Bug Forge: Fixed code copied!");
            break;
          }

          case "openSettings":
            vscode.commands.executeCommand(
              "workbench.action.openSettings",
              "neo-bug-forge"
            );
            break;

          case "setApiKey":
            vscode.commands.executeCommand("neo-bug-forge.setApiKey");
            break;

          case "openPromo":
            vscode.env.openExternal(vscode.Uri.parse("https://marketplace.visualstudio.com/items?itemName=neobugforge.neo-bug-forge&ssr=false#review-details"));
            break;

          case "saveTest": {
            const { testCode, language } = message.payload as { testCode: string; language: string };
            const extMap: Record<string, string> = {
              python: ".py", javascript: ".js", typescript: ".ts",
              rust: ".rs", go: "_test.go", java: "Test.java",
              cpp: ".cpp", c: ".c", ruby: ".rb", php: ".php",
            };
            const ext         = extMap[language] || ".txt";
            const defaultName = `test_fix${ext}`;
            const saveUri = await vscode.window.showSaveDialog({
              defaultUri: vscode.Uri.file(defaultName),
              filters: { "Test File": [ext.replace(".", "")] },
              saveLabel: "Save Test File",
            });
            if (saveUri) {
              fs.writeFileSync(saveUri.fsPath, testCode, "utf8");
              vscode.window.showInformationMessage(`Neo Bug Forge: Test saved to ${path.basename(saveUri.fsPath)} ✓`);
            }
            break;
          }
        }
      },
      null,
      this._disposables
    );

    this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
  }

  // ── Public: send a status message to the webview ─────────────────────────

  public sendStatus(status: "scanning" | "idle") {
    this._panel.webview.postMessage({ command: "status", payload: { status } });
  }

  // ── Public: prefill from context menu ────────────────────────────────────

  public prefillAndSubmit(payload: PrefillPayload) {
    setTimeout(() => {
      this._panel.webview.postMessage({ command: "prefill", payload });
    }, 300);
  }

  // ── Private: handle fix request ──────────────────────────────────────────

  private async _handleFix(payload: { code: string; error: string; language: string }) {
    this._panel.webview.postMessage({ command: "loading" });

    try {
      const result = await runBugForge(this._context, payload);
      this._panel.webview.postMessage({ command: "result", payload: result });
      // Track fix count and maybe prompt for a review (fire-and-forget)
      trackFixAndPromptReview(this._context).catch(() => {});
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "An unexpected error occurred.";
      this._panel.webview.postMessage({ command: "error", payload: { message } });
    }
  }

  // ── Dispose ───────────────────────────────────────────────────────────────

  public dispose() {
    NeoBugForgePanel.currentPanel = undefined;
    this._panel.dispose();
    for (const d of this._disposables) { d.dispose(); }
    this._disposables = [];
  }
}

// ─── Webview HTML ─────────────────────────────────────────────────────────────

function getWebviewContent(): string {
  return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Neo Bug Forge</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Syne:wght@400;700;800&display=swap');

  :root {
    --bg:        #0a0a0a;
    --surface:   #111111;
    --border:    #1e1e1e;
    --border2:   #2a2a2a;
    --text:      #e8e8e8;
    --muted:     #555;
    --green:     #00ff88;
    --green-dim: #00cc66;
    --red:       #ff4444;
    --yellow:    #ffcc00;
    --blue:      #4488ff;
    --mono:      'JetBrains Mono', monospace;
    --sans:      'Syne', sans-serif;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: var(--mono);
    font-size: 12px;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* ── Header ── */
  .header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 14px;
    border-bottom: 1px solid var(--border2);
    background: var(--surface);
    flex-shrink: 0;
  }
  .logo { font-family: var(--sans); font-weight: 800; font-size: 13px; letter-spacing: 0.05em; color: var(--green); }
  .logo span { color: var(--text); font-weight: 400; }
  .header-actions { display: flex; gap: 6px; }
  .icon-btn {
    background: none; border: 1px solid var(--border2); color: var(--muted);
    padding: 4px 8px; border-radius: 3px; cursor: pointer;
    font-size: 10px; font-family: var(--mono); transition: all 0.15s;
  }
  .icon-btn:hover { border-color: var(--green); color: var(--green); }

  /* ── Main ── */
  .main {
    flex: 1; overflow-y: auto; padding: 12px 14px;
    display: flex; flex-direction: column; gap: 10px;
  }
  .main::-webkit-scrollbar { width: 4px; }
  .main::-webkit-scrollbar-track { background: var(--bg); }
  .main::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

  /* ── Section labels ── */
  .label {
    font-size: 9px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase;
    color: var(--muted); margin-bottom: 5px; display: flex; align-items: center; gap: 6px;
  }
  .label::after { content: ''; flex: 1; height: 1px; background: var(--border); }

  /* ── Textareas ── */
  textarea {
    width: 100%; background: var(--surface); border: 1px solid var(--border2);
    border-radius: 4px; color: var(--text); font-family: var(--mono);
    font-size: 11.5px; line-height: 1.6; padding: 10px 12px;
    resize: vertical; transition: border-color 0.15s; outline: none;
  }
  textarea:focus { border-color: var(--green); }
  textarea::placeholder { color: var(--muted); }
  #code-input  { min-height: 140px; }
  #error-input { min-height: 54px; }

  /* ── Try Again feedback box ── */
  .retry-box {
    display: none;
    background: var(--surface);
    border: 1px solid #ffcc0040;
    border-radius: 4px;
    padding: 10px 12px;
    animation: fadeIn 0.2s ease;
  }
  .retry-box.visible { display: block; }
  .retry-box .retry-label {
    font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    color: var(--yellow); margin-bottom: 8px;
  }
  #retry-note {
    min-height: 48px; border-color: #ffcc0040; resize: none;
    font-size: 11px; margin-bottom: 8px;
  }
  #retry-note:focus { border-color: var(--yellow); }
  .retry-actions { display: flex; gap: 6px; }
  .btn-retry-go {
    flex: 1; padding: 7px; border-radius: 3px; border: 1px solid var(--yellow);
    background: transparent; color: var(--yellow); font-family: var(--mono);
    font-size: 10px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
    cursor: pointer; transition: all 0.15s;
  }
  .btn-retry-go:hover { background: #ffcc0015; }
  .btn-retry-cancel {
    padding: 7px 12px; border-radius: 3px; border: 1px solid var(--border2);
    background: transparent; color: var(--muted); font-family: var(--mono);
    font-size: 10px; cursor: pointer; transition: all 0.15s;
  }
  .btn-retry-cancel:hover { border-color: var(--muted); color: var(--text); }

  /* ── Language badges ── */
  .lang-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .lang-badge {
    font-size: 9px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
    padding: 2px 7px; border-radius: 2px; background: var(--border2); color: var(--muted);
    cursor: pointer; border: 1px solid transparent; transition: all 0.12s;
  }
  .lang-badge.active, .lang-badge:hover { background: transparent; border-color: var(--green); color: var(--green); }

  /* ── Submit button ── */
  #fix-btn {
    width: 100%; padding: 11px;
    background: var(--green); color: #000; border: none; border-radius: 4px;
    font-family: var(--sans); font-weight: 800; font-size: 12px;
    letter-spacing: 0.08em; text-transform: uppercase;
    cursor: pointer; transition: all 0.15s; flex-shrink: 0;
  }
  #fix-btn:hover { background: var(--green-dim); }
  #fix-btn:disabled { background: var(--border2); color: var(--muted); cursor: not-allowed; }

  /* ── Loading bar ── */
  .loading-bar { display: none; height: 2px; background: var(--border2); border-radius: 1px; overflow: hidden; flex-shrink: 0; }
  .loading-bar.active { display: block; }
  .loading-bar::after {
    content: ''; display: block; height: 100%; width: 40%;
    background: var(--green); animation: slide 1s ease-in-out infinite;
  }
  @keyframes slide { 0% { transform: translateX(-100%); } 100% { transform: translateX(350%); } }

  /* ── Results ── */
  #results { display: none; flex-direction: column; gap: 10px; animation: fadeIn 0.3s ease; }
  #results.visible { display: flex; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; } }

  /* ── Meta row ── */
  .meta-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .confidence-pill { font-size: 10px; font-weight: 700; padding: 3px 9px; border-radius: 2px; letter-spacing: 0.06em; }
  .conf-high { background: #00ff8820; color: var(--green);  border: 1px solid #00ff8840; }
  .conf-mid  { background: #ffcc0020; color: var(--yellow); border: 1px solid #ffcc0040; }
  .conf-low  { background: #ff444420; color: var(--red);    border: 1px solid #ff444440; }
  .root-cause-tag {
    font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    padding: 3px 9px; border-radius: 2px; background: var(--border2);
    color: var(--blue); border: 1px solid #4488ff30;
  }

  /* ── Code block ── */
  .code-block { background: var(--surface); border: 1px solid var(--border2); border-radius: 4px; overflow: hidden; }
  .code-block-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 6px 10px; border-bottom: 1px solid var(--border); background: #161616;
  }
  .code-block-title { font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }
  .code-block pre { padding: 10px 12px; overflow-x: auto; line-height: 1.6; font-size: 11.5px; color: var(--text); }

  /* ── Diff ── */
  .diff-line { display: block; white-space: pre; }
  .diff-add  { color: var(--green);  background: #00ff8808; }
  .diff-del  { color: var(--red);    background: #ff444408; text-decoration: line-through; }
  .diff-ctx  { color: var(--muted); }

  /* ── Explanation (typewriter) ── */
  .explanation {
    background: var(--surface); border: 1px solid var(--border2);
    border-left: 3px solid var(--green); border-radius: 0 4px 4px 0;
    padding: 10px 12px; font-size: 11.5px; line-height: 1.7; color: #ccc;
    min-height: 1.7em;
  }
  .cursor-blink { display: inline-block; width: 2px; height: 1em; background: var(--green); margin-left: 2px; animation: blink 0.7s step-end infinite; vertical-align: text-bottom; }
  @keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }

  /* ── Tabs ── */
  .tabs { display: flex; border-bottom: 1px solid var(--border2); margin-bottom: 0; }
  .tab {
    padding: 6px 12px; font-size: 9px; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: var(--muted); cursor: pointer;
    border-bottom: 2px solid transparent; margin-bottom: -1px; transition: all 0.12s;
  }
  .tab.active { color: var(--green); border-bottom-color: var(--green); }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }

  /* ── Action buttons ── */
  .action-row { display: flex; gap: 7px; flex-wrap: wrap; }
  .action-btn {
    flex: 1; min-width: 80px; padding: 8px; border-radius: 3px; font-family: var(--mono);
    font-size: 10px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
    cursor: pointer; border: 1px solid var(--border2); transition: all 0.15s;
  }
  .btn-apply { background: var(--green); color: #000; border-color: var(--green); }
  .btn-apply:hover { background: var(--green-dim); }
  .btn-copy  { background: transparent; color: var(--text); }
  .btn-copy:hover { border-color: var(--text); }
  .btn-again { background: transparent; color: var(--yellow); border-color: #ffcc0050; }
  .btn-again:hover { border-color: var(--yellow); }
  .btn-reset { background: transparent; color: var(--muted); }
  .btn-reset:hover { border-color: var(--muted); color: var(--text); }

  /* ── Context badge ── */
  .context-badge {
    display: none;
    font-size: 9px; font-weight: 700; letter-spacing: 0.08em;
    padding: 3px 8px; border-radius: 2px;
    background: rgba(68,136,255,.1); border: 1px solid rgba(68,136,255,.3);
    color: var(--blue);
  }

  /* ── Promo banner ── */
  .promo-banner {
    background: linear-gradient(135deg, #1a1a00, #111100);
    border: 1px solid #ffcc0050;
    border-radius: 4px;
    padding: 9px 12px;
    display: flex; align-items: center; gap: 8px;
    flex-shrink: 0;
  }
  .promo-text {
    flex: 1; font-size: 10px; color: var(--yellow); line-height: 1.5;
  }
  .promo-text strong { font-weight: 700; }
  .promo-link {
    font-size: 9px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
    padding: 4px 9px; border-radius: 2px;
    border: 1px solid var(--yellow); color: var(--yellow);
    background: transparent; cursor: pointer;
    font-family: var(--mono); transition: all 0.15s; white-space: nowrap;
  }
  .promo-link:hover { background: #ffcc0015; }
  .promo-close {
    background: none; border: none; color: var(--muted);
    font-size: 12px; cursor: pointer; padding: 0 2px; line-height: 1;
    transition: color 0.15s;
  }
  .promo-close:hover { color: var(--text); }

  /* ── Error box ── */
  .error-box {
    display: none; background: #ff444410; border: 1px solid #ff444440;
    border-radius: 4px; padding: 10px 12px; color: var(--red); font-size: 11px; line-height: 1.6;
  }
  .error-box.visible { display: block; animation: fadeIn 0.2s ease; }
</style>
</head>
<body>

<!-- ── Header ── -->
<div class="header">
  <div class="logo">Neo Bug<span>Forge</span> AI</div>
  <div class="header-actions">
    <button class="icon-btn" onclick="vscodeApi.postMessage({command:'setApiKey'})">⚙ API Key</button>
    <button class="icon-btn" onclick="vscodeApi.postMessage({command:'openSettings'})">Settings</button>
  </div>
</div>

<!-- ── Scrollable main ── -->
<div class="main">

  <!-- Input form -->
  <div id="input-section">
    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:5px;">
      <div class="label" style="margin:0">Broken Code</div>
      <span class="context-badge" id="context-badge"></span>
    </div>
    <div class="lang-row" id="lang-row">
      <span class="label" style="margin:0">Lang:</span>
      <span class="lang-badge active" data-lang="python">Python</span>
      <span class="lang-badge" data-lang="javascript">JS</span>
      <span class="lang-badge" data-lang="typescript">TS</span>
      <span class="lang-badge" data-lang="rust">Rust</span>
      <span class="lang-badge" data-lang="go">Go</span>
      <span class="lang-badge" data-lang="java">Java</span>
      <span class="lang-badge" data-lang="cpp">C++</span>
      <span class="lang-badge" data-lang="">Auto</span>
    </div>
    <textarea id="code-input" placeholder="Paste your broken code here...&#10;&#10;Or select code in the editor and press Cmd+Shift+F"></textarea>
    <div class="label" style="margin-top:4px">Error Message</div>
    <textarea id="error-input" placeholder="Paste the error or describe the bug..."></textarea>
  </div>

  <!-- Error box -->
  <div class="error-box" id="error-box"></div>

  <!-- Loading bar -->
  <div class="loading-bar" id="loading-bar"></div>

  <!-- Results -->
  <div id="results">
    <div class="meta-row">
      <div class="confidence-pill" id="conf-pill"></div>
      <div class="root-cause-tag"  id="root-cause-tag"></div>
    </div>

    <div class="label">Explanation</div>
    <div class="explanation" id="explanation-text"></div>

    <div class="label">Fixed Code</div>
    <div class="tabs">
      <div class="tab active" data-tab="fixed">Fixed</div>
      <div class="tab" data-tab="diff">Diff</div>
      <div class="tab" data-tab="test">Test Case</div>
    </div>
    <div class="code-block">
      <div class="tab-panel active" id="tab-fixed"><pre id="fixed-code-pre"></pre></div>
      <div class="tab-panel"        id="tab-diff" ><pre id="diff-pre"></pre></div>
      <div class="tab-panel"        id="tab-test" >
        <div class="code-block-header">
          <span class="code-block-title">Generated Test</span>
          <button class="icon-btn" id="save-test-btn">💾 Save Test File</button>
        </div>
        <pre id="test-pre"></pre>
      </div>
    </div>

    <div class="action-row">
      <button class="action-btn btn-apply" id="apply-btn">⬆ Apply (Diff Preview)</button>
      <button class="action-btn btn-copy"  id="copy-btn" >⧉ Copy</button>
      <button class="action-btn btn-again" id="again-btn">↺ Try Again</button>
      <button class="action-btn btn-reset" id="reset-btn">✕ New Fix</button>
    </div>

    <!-- Try Again box -->
    <div class="retry-box" id="retry-box">
      <div class="retry-label">⚡ What's still wrong?</div>
      <textarea id="retry-note" placeholder="Optional: describe what the fix got wrong, or leave blank to retry as-is..."></textarea>
      <div class="retry-actions">
        <button class="btn-retry-go" id="retry-go-btn">⟳ Retry Fix</button>
        <button class="btn-retry-cancel" id="retry-cancel-btn">Cancel</button>
      </div>
    </div>
  </div>

</div><!-- /main -->

<!-- ── Promo banner (sticky bottom) ── -->
<div id="promo-wrap" style="padding:10px 14px 0; background:var(--bg); flex-shrink:0;">
  <div class="promo-banner">
    <div class="promo-text">⭐ <strong>Leave a review</strong> and get Pro free — first 50 reviewers. <span id="promo-spots" style="opacity:0.7">37 spots left.</span></div>
    <button class="promo-link" onclick="openPromo()">Review →</button>
    <button class="promo-close" onclick="dismissPromo()" title="Dismiss">✕</button>
  </div>
</div>

<!-- ── Fix button (sticky bottom) ── -->
<div style="padding:8px 14px 10px; background:var(--bg); flex-shrink:0;">
  <button id="fix-btn">⚡ Fix My Bug</button>
</div>

<script>
  const vscodeApi = acquireVsCodeApi();
  let currentFixedCode = '';
  let currentTestCase  = '';  // generated test — kept for Save Test
  let currentCode      = '';  // original code — kept for Try Again
  let currentError     = '';  // original error — kept for Try Again
  let selectedLang     = 'python';

  // ── Language badges ───────────────────────────────────────────────────────
  document.querySelectorAll('.lang-badge').forEach(badge => {
    badge.addEventListener('click', () => {
      document.querySelectorAll('.lang-badge').forEach(b => b.classList.remove('active'));
      badge.classList.add('active');
      selectedLang = badge.dataset.lang || '';
    });
  });

  // ── Tabs ──────────────────────────────────────────────────────────────────
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const targetId = tab.dataset.tab;
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById('tab-' + targetId).classList.add('active');
    });
  });

  // ── Fix button ────────────────────────────────────────────────────────────
  document.getElementById('fix-btn').addEventListener('click', submitFix);
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') submitFix();
  });

  function submitFix() {
    const code  = document.getElementById('code-input').value.trim();
    const error = document.getElementById('error-input').value.trim();
    if (!code) { showError('Please paste some broken code first.'); return; }
    currentCode  = code;
    currentError = error;
    hideError();
    hideResults();
    closeRetryBox();
    vscodeApi.postMessage({ command: 'fix', payload: { code, error, language: selectedLang } });
  }

  // ── Action buttons ────────────────────────────────────────────────────────
  document.getElementById('apply-btn').addEventListener('click', () => {
    vscodeApi.postMessage({ command: 'applyWithDiff', payload: { fixedCode: currentFixedCode } });
  });

  document.getElementById('copy-btn').addEventListener('click', () => {
    vscodeApi.postMessage({ command: 'copyFix', payload: { fixedCode: currentFixedCode } });
  });

  document.getElementById('save-test-btn').addEventListener('click', () => {
    if (!currentTestCase) return;
    vscodeApi.postMessage({ command: 'saveTest', payload: { testCode: currentTestCase, language: selectedLang } });
  });

  document.getElementById('again-btn').addEventListener('click', () => {
    const box = document.getElementById('retry-box');
    box.classList.toggle('visible');
    if (box.classList.contains('visible')) {
      document.getElementById('retry-note').focus();
    }
  });

  document.getElementById('reset-btn').addEventListener('click', resetForm);

  // ── Try Again flow ────────────────────────────────────────────────────────
  document.getElementById('retry-go-btn').addEventListener('click', () => {
    const note = document.getElementById('retry-note').value.trim();

    // Smart retry: pass previous fix attempt as context so Claude sees what was tried
    const retryCode = currentFixedCode
      ? currentCode + '\\n\\n// ─── Previous fix attempt (did not work) ───\\n' + currentFixedCode
      : currentCode;
    const retryError = (currentError ? currentError + '\\n\\n' : '') +
      'The previous fix attempt did not solve the problem.' +
      (note ? ' Specific issue: ' + note : ' Please analyze differently and try a new approach.');

    closeRetryBox();
    hideResults();
    hideError();
    document.getElementById('loading-bar').classList.add('active');
    document.getElementById('fix-btn').disabled = true;
    document.getElementById('fix-btn').textContent = '⟳ Retrying...';
    vscodeApi.postMessage({ command: 'fix', payload: { code: retryCode, error: retryError, language: selectedLang } });
  });

  document.getElementById('retry-cancel-btn').addEventListener('click', closeRetryBox);

  function closeRetryBox() {
    document.getElementById('retry-box').classList.remove('visible');
    document.getElementById('retry-note').value = '';
  }

  // ── Messages from extension ───────────────────────────────────────────────
  window.addEventListener('message', ({ data }) => {
    switch (data.command) {
      case 'status':
        if (data.payload.status === 'scanning') {
          const btn = document.getElementById('fix-btn');
          btn.disabled    = true;
          btn.textContent = '🔍 Scanning workspace...';
          document.getElementById('loading-bar').classList.add('active');
        }
        break;
      case 'loading':  setLoading(true);             break;
      case 'result':   setLoading(false); renderResult(data.payload); break;
      case 'error':    setLoading(false); showError(data.payload.message); break;
      case 'prefill':  prefill(data.payload); break;
    }
  });

  // ── Typewriter animation ──────────────────────────────────────────────────
  let typewriterTimer = null;

  function typewriter(el, text, speed = 12) {
    if (typewriterTimer) { clearInterval(typewriterTimer); typewriterTimer = null; }
    el.textContent = '';
    const cursor = document.createElement('span');
    cursor.className = 'cursor-blink';
    el.appendChild(cursor);
    let i = 0;
    typewriterTimer = setInterval(() => {
      if (i < text.length) {
        cursor.before(text[i++]);
      } else {
        clearInterval(typewriterTimer);
        typewriterTimer = null;
        cursor.remove();
      }
    }, speed);
  }

  // ── Render result ─────────────────────────────────────────────────────────
  function renderResult(r) {
    currentFixedCode = r.fixed_code;

    // Confidence pill
    const pill = document.getElementById('conf-pill');
    pill.textContent = r.confidence + '% confident';
    pill.className   = 'confidence-pill ' +
      (r.confidence >= 80 ? 'conf-high' : r.confidence >= 50 ? 'conf-mid' : 'conf-low');

    // Root cause
    document.getElementById('root-cause-tag').textContent = r.root_cause.replace(/_/g, ' ');

    // Explanation — typewriter effect
    typewriter(document.getElementById('explanation-text'), r.explanation);

    // Fixed code
    document.getElementById('fixed-code-pre').textContent = r.fixed_code;

    // Diff
    const diffPre = document.getElementById('diff-pre');
    diffPre.innerHTML = '';
    r.diff.split('\\n').forEach(line => {
      const span = document.createElement('span');
      span.className = 'diff-line ' +
        (line.startsWith('+') ? 'diff-add' : line.startsWith('-') ? 'diff-del' : 'diff-ctx');
      span.textContent = line;
      diffPre.appendChild(span);
    });

    // Test case
    currentTestCase = r.test_case || '';
    document.getElementById('test-pre').textContent = r.test_case;

    document.getElementById('results').classList.add('visible');

    // Reset tabs to Fixed
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelector('[data-tab="fixed"]').classList.add('active');
    document.getElementById('tab-fixed').classList.add('active');
  }

  // ── Prefill ───────────────────────────────────────────────────────────────
  function prefill({ code, error, language, fileName, contextCount }) {
    document.getElementById('code-input').value  = code;
    document.getElementById('error-input').value = error;

    // Show context badge if files were included
    const badge = document.getElementById('context-badge');
    if (contextCount && contextCount > 0) {
      badge.textContent = '📎 ' + contextCount + ' context file' + (contextCount > 1 ? 's' : '') + ' included';
      badge.style.display = 'inline-block';
    } else {
      badge.style.display = 'none';
    }

    let matched = false;
    document.querySelectorAll('.lang-badge').forEach(b => {
      b.classList.remove('active');
      if (b.dataset.lang === language) { b.classList.add('active'); matched = true; selectedLang = language; }
    });
    if (!matched) {
      document.querySelector('[data-lang=""]').classList.add('active');
      selectedLang = language;
    }
    submitFix();
  }

  // ── Helpers ────────────────────────────────────────────
  function setLoading(active) {
    document.getElementById('loading-bar').classList.toggle('active', active);
    const btn = document.getElementById('fix-btn');
    btn.disabled    = active;
    btn.textContent = active ? '\u27f3 Analyzing...' : '\u26a1 Fix My Bug';
    if (active) hideResults();
  }

  function showError(msg) {
    const box = document.getElementById('error-box');
    box.textContent = '\u2717 ' + msg;
    box.classList.add('visible');
  }
  function hideError()   { document.getElementById('error-box').classList.remove('visible'); }
  function hideResults() { document.getElementById('results').classList.remove('visible'); }

  // ── Promo banner ────────────────────────────────────────────
  function openPromo() {
    vscodeApi.postMessage({ command: 'openPromo' });
  }
  function dismissPromo() {
    const wrap = document.getElementById('promo-wrap');
    if (wrap) wrap.style.display = 'none';
  }

  function resetForm() {
    document.getElementById('code-input').value  = '';
    document.getElementById('error-input').value = '';
    hideResults();
    hideError();
    closeRetryBox();
    currentFixedCode = '';
    currentTestCase  = '';
    currentCode      = '';
    currentError     = '';
    document.getElementById('code-input').focus();
  }
</script>
</body>
</html>`;
}
