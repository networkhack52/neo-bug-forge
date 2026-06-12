/**
 * panel.ts  —  Neo Bug Forge Webview Panel
 * ───────────────────────────────────────
 * Manages the VS Code WebviewPanel. Acts as the bridge between:
 *   - The extension host (TypeScript / Node) which calls the Claude API
 *   - The webview UI (HTML/CSS/JS) rendered in the panel
 *
 * Message protocol (extension ↔ webview):
 *   webview → extension:  { command: "fix",     payload: { code, error, language } }
 *   webview → extension:  { command: "applyFix", payload: { fixedCode } }
 *   webview → extension:  { command: "copyFix",  payload: { fixedCode } }
 *   extension → webview:  { command: "prefill",  payload: { code, error, language, fileName } }
 *   extension → webview:  { command: "result",   payload: FixResult }
 *   extension → webview:  { command: "error",    payload: { message } }
 *   extension → webview:  { command: "loading" }
 */

import * as vscode from "vscode";
import * as path from "path";
import { runBugForge } from "./extension";

export interface PrefillPayload {
  code: string;
  error: string;
  language: string;
  fileName: string;
}

export class NeoBugForgePanel {
  public static currentPanel: NeoBugForgePanel | undefined;
  private readonly _panel: vscode.WebviewPanel;
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
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [
          vscode.Uri.file(path.join(context.extensionPath, "media")),
        ],
      }
    );

    NeoBugForgePanel.currentPanel = new NeoBugForgePanel(panel, context);
  }

  // ── Constructor ───────────────────────────────────────────────────────────

  private constructor(
    panel: vscode.WebviewPanel,
    context: vscode.ExtensionContext
  ) {
    this._panel = panel;
    this._context = context;

    // Set the HTML content
    this._panel.webview.html = getWebviewContent();

    // Handle messages from the webview
    this._panel.webview.onDidReceiveMessage(
      async (message: { command: string; payload?: unknown }) => {
        switch (message.command) {
          case "fix":
            await this._handleFix(
              message.payload as { code: string; error: string; language: string }
            );
            break;

          case "applyFix": {
            const { fixedCode } = message.payload as { fixedCode: string };
            await this._applyFixToEditor(fixedCode);
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
        }
      },
      null,
      this._disposables
    );

    // Cleanup on panel close
    this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
  }

  // ── Public: prefill from context menu ─────────────────────────────────────

  public prefillAndSubmit(payload: PrefillPayload) {
    // Small delay to ensure webview is ready
    setTimeout(() => {
      this._panel.webview.postMessage({ command: "prefill", payload });
    }, 300);
  }

  // ── Private: handle fix request ───────────────────────────────────────────

  private async _handleFix(payload: {
    code: string;
    error: string;
    language: string;
  }) {
    // Tell the UI we're loading
    this._panel.webview.postMessage({ command: "loading" });

    try {
      const result = await runBugForge(this._context, payload);
      this._panel.webview.postMessage({ command: "result", payload: result });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "An unexpected error occurred.";
      this._panel.webview.postMessage({ command: "error", payload: { message } });
    }
  }

  // ── Private: apply fix to the active editor ───────────────────────────────

  private async _applyFixToEditor(fixedCode: string) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      // No editor open — open a new untitled document with the fixed code
      const doc = await vscode.workspace.openTextDocument({
        content: fixedCode,
      });
      vscode.window.showTextDocument(doc);
      return;
    }

    const selection = editor.selection;
    const hasSelection = !selection.isEmpty;

    await editor.edit((editBuilder) => {
      if (hasSelection) {
        editBuilder.replace(selection, fixedCode);
      } else {
        // Replace entire document
        const fullRange = new vscode.Range(
          editor.document.positionAt(0),
          editor.document.positionAt(editor.document.getText().length)
        );
        editBuilder.replace(fullRange, fixedCode);
      }
    });

    vscode.window.showInformationMessage(
      "Neo Bug Forge: Fix applied to editor ✓"
    );
  }

  // ── Dispose ───────────────────────────────────────────────────────────────

  public dispose() {
    NeoBugForgePanel.currentPanel = undefined;
    this._panel.dispose();
    for (const d of this._disposables) {
      d.dispose();
    }
    this._disposables = [];
  }
}

// ─── Webview HTML ─────────────────────────────────────────────────────────────
// Self-contained HTML/CSS/JS. No external dependencies.
// Aesthetic: Dark industrial terminal — monochrome with electric green accents.

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
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    border-bottom: 1px solid var(--border2);
    background: var(--surface);
    flex-shrink: 0;
  }
  .logo {
    font-family: var(--sans);
    font-weight: 800;
    font-size: 13px;
    letter-spacing: 0.05em;
    color: var(--green);
  }
  .logo span { color: var(--text); font-weight: 400; }
  .header-actions { display: flex; gap: 6px; }
  .icon-btn {
    background: none;
    border: 1px solid var(--border2);
    color: var(--muted);
    padding: 4px 8px;
    border-radius: 3px;
    cursor: pointer;
    font-size: 10px;
    font-family: var(--mono);
    transition: all 0.15s;
  }
  .icon-btn:hover { border-color: var(--green); color: var(--green); }

  /* ── Main scroll area ── */
  .main {
    flex: 1;
    overflow-y: auto;
    padding: 12px 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .main::-webkit-scrollbar { width: 4px; }
  .main::-webkit-scrollbar-track { background: var(--bg); }
  .main::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }

  /* ── Section labels ── */
  .label {
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 5px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border);
  }

  /* ── Textareas ── */
  textarea {
    width: 100%;
    background: var(--surface);
    border: 1px solid var(--border2);
    border-radius: 4px;
    color: var(--text);
    font-family: var(--mono);
    font-size: 11.5px;
    line-height: 1.6;
    padding: 10px 12px;
    resize: vertical;
    transition: border-color 0.15s;
    outline: none;
  }
  textarea:focus { border-color: var(--green); }
  textarea::placeholder { color: var(--muted); }
  #code-input  { min-height: 140px; }
  #error-input { min-height: 54px; }

  /* ── Language badge row ── */
  .lang-row {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }
  .lang-badge {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 2px 7px;
    border-radius: 2px;
    background: var(--border2);
    color: var(--muted);
    cursor: pointer;
    border: 1px solid transparent;
    transition: all 0.12s;
  }
  .lang-badge.active, .lang-badge:hover {
    background: transparent;
    border-color: var(--green);
    color: var(--green);
  }

  /* ── Submit button ── */
  #fix-btn {
    width: 100%;
    padding: 11px;
    background: var(--green);
    color: #000;
    border: none;
    border-radius: 4px;
    font-family: var(--sans);
    font-weight: 800;
    font-size: 12px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    cursor: pointer;
    transition: all 0.15s;
    flex-shrink: 0;
  }
  #fix-btn:hover { background: var(--green-dim); }
  #fix-btn:disabled { background: var(--border2); color: var(--muted); cursor: not-allowed; }

  /* ── Loading state ── */
  .loading-bar {
    display: none;
    height: 2px;
    background: var(--border2);
    border-radius: 1px;
    overflow: hidden;
    flex-shrink: 0;
  }
  .loading-bar.active { display: block; }
  .loading-bar::after {
    content: '';
    display: block;
    height: 100%;
    width: 40%;
    background: var(--green);
    animation: slide 1s ease-in-out infinite;
  }
  @keyframes slide {
    0%   { transform: translateX(-100%); }
    100% { transform: translateX(350%); }
  }

  /* ── Results ── */
  #results { display: none; flex-direction: column; gap: 10px; animation: fadeIn 0.3s ease; }
  #results.visible { display: flex; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; } }

  /* ── Meta row (confidence + root cause) ── */
  .meta-row {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }
  .confidence-pill {
    font-size: 10px;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 2px;
    letter-spacing: 0.06em;
  }
  .conf-high  { background: #00ff8820; color: var(--green);  border: 1px solid #00ff8840; }
  .conf-mid   { background: #ffcc0020; color: var(--yellow); border: 1px solid #ffcc0040; }
  .conf-low   { background: #ff444420; color: var(--red);    border: 1px solid #ff444440; }
  .root-cause-tag {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 3px 9px;
    border-radius: 2px;
    background: var(--border2);
    color: var(--blue);
    border: 1px solid #4488ff30;
  }

  /* ── Code block ── */
  .code-block {
    background: var(--surface);
    border: 1px solid var(--border2);
    border-radius: 4px;
    overflow: hidden;
  }
  .code-block-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 10px;
    border-bottom: 1px solid var(--border);
    background: #161616;
  }
  .code-block-title { font-size: 9px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }
  .code-block pre { padding: 10px 12px; overflow-x: auto; line-height: 1.6; font-size: 11.5px; color: var(--text); }

  /* ── Diff view ── */
  .diff-line { display: block; white-space: pre; }
  .diff-add  { color: var(--green); background: #00ff8808; }
  .diff-del  { color: var(--red);   background: #ff444408; text-decoration: line-through; }
  .diff-ctx  { color: var(--muted); }

  /* ── Explanation ── */
  .explanation {
    background: var(--surface);
    border: 1px solid var(--border2);
    border-left: 3px solid var(--green);
    border-radius: 0 4px 4px 0;
    padding: 10px 12px;
    font-size: 11.5px;
    line-height: 1.7;
    color: #ccc;
  }

  /* ── Action buttons ── */
  .action-row { display: flex; gap: 7px; }
  .action-btn {
    flex: 1;
    padding: 8px;
    border-radius: 3px;
    font-family: var(--mono);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    cursor: pointer;
    border: 1px solid var(--border2);
    transition: all 0.15s;
  }
  .btn-apply { background: var(--green); color: #000; border-color: var(--green); }
  .btn-apply:hover { background: var(--green-dim); }
  .btn-copy  { background: transparent; color: var(--text); }
  .btn-copy:hover { border-color: var(--text); }
  .btn-reset { background: transparent; color: var(--muted); }
  .btn-reset:hover { border-color: var(--muted); color: var(--text); }

  /* ── Error message ── */
  .error-box {
    display: none;
    background: #ff444410;
    border: 1px solid #ff444440;
    border-radius: 4px;
    padding: 10px 12px;
    color: var(--red);
    font-size: 11px;
    line-height: 1.6;
  }
  .error-box.visible { display: block; animation: fadeIn 0.2s ease; }

  /* ── Tabs for result sections ── */
  .tabs { display: flex; border-bottom: 1px solid var(--border2); margin-bottom: 0; }
  .tab {
    padding: 6px 12px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    transition: all 0.12s;
  }
  .tab.active { color: var(--green); border-bottom-color: var(--green); }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }
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
    <div class="label">Broken Code</div>
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
      <div class="root-cause-tag" id="root-cause-tag"></div>
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
      <div class="tab-panel active" id="tab-fixed">
        <pre id="fixed-code-pre"></pre>
      </div>
      <div class="tab-panel" id="tab-diff">
        <pre id="diff-pre"></pre>
      </div>
      <div class="tab-panel" id="tab-test">
        <pre id="test-pre"></pre>
      </div>
    </div>

    <div class="action-row">
      <button class="action-btn btn-apply" id="apply-btn">⬆ Apply to Editor</button>
      <button class="action-btn btn-copy"  id="copy-btn">⧉ Copy</button>
      <button class="action-btn btn-reset" id="reset-btn">↺ New Fix</button>
    </div>
  </div>

</div><!-- /main -->

<!-- ── Fix button (sticky bottom) ── -->
<div style="padding:10px 14px; border-top:1px solid var(--border2); background:var(--bg); flex-shrink:0;">
  <button id="fix-btn">⚡ Fix My Bug</button>
</div>

<script>
  const vscodeApi = acquireVsCodeApi();
  let currentFixedCode = '';
  let selectedLang = 'python';

  // ── Language badges ─────────────────────────────────────────────────────
  document.querySelectorAll('.lang-badge').forEach(badge => {
    badge.addEventListener('click', () => {
      document.querySelectorAll('.lang-badge').forEach(b => b.classList.remove('active'));
      badge.classList.add('active');
      selectedLang = badge.dataset.lang || '';
    });
  });

  // ── Tabs ─────────────────────────────────────────────────────────────────
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

  // Ctrl+Enter shortcut
  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') submitFix();
  });

  function submitFix() {
    const code  = document.getElementById('code-input').value.trim();
    const error = document.getElementById('error-input').value.trim();
    if (!code) { showError('Please paste some broken code first.'); return; }
    hideError();
    hideResults();
    vscodeApi.postMessage({
      command: 'fix',
      payload: { code, error, language: selectedLang }
    });
  }

  // ── Action buttons ─────────────────────────────────────────────────────────
  document.getElementById('apply-btn').addEventListener('click', () => {
    vscodeApi.postMessage({ command: 'applyFix', payload: { fixedCode: currentFixedCode } });
  });
  document.getElementById('copy-btn').addEventListener('click', () => {
    vscodeApi.postMessage({ command: 'copyFix', payload: { fixedCode: currentFixedCode } });
  });
  document.getElementById('reset-btn').addEventListener('click', resetForm);

  // ── Messages from extension ────────────────────────────────────────────────
  window.addEventListener('message', ({ data }) => {
    switch (data.command) {
      case 'loading':
        setLoading(true);
        break;

      case 'result':
        setLoading(false);
        renderResult(data.payload);
        break;

      case 'error':
        setLoading(false);
        showError(data.payload.message);
        break;

      case 'prefill':
        prefill(data.payload);
        break;
    }
  });

  // ── Render helpers ─────────────────────────────────────────────────────────

  function renderResult(r) {
    currentFixedCode = r.fixed_code;

    // Confidence pill
    const pill = document.getElementById('conf-pill');
    pill.textContent = r.confidence + '% confident';
    pill.className = 'confidence-pill ' +
      (r.confidence >= 80 ? 'conf-high' : r.confidence >= 50 ? 'conf-mid' : 'conf-low');

    // Root cause tag
    document.getElementById('root-cause-tag').textContent = r.root_cause.replace(/_/g,' ');

    // Explanation
    document.getElementById('explanation-text').textContent = r.explanation;

    // Fixed code
    document.getElementById('fixed-code-pre').textContent = r.fixed_code;

    // Diff
    const diffPre = document.getElementById('diff-pre');
    diffPre.innerHTML = '';
    r.diff.split('\\n').forEach(line => {
      const span = document.createElement('span');
      span.className = 'diff-line ' +
        (line.startsWith('+') ? 'diff-add' :
         line.startsWith('-') ? 'diff-del' : 'diff-ctx');
      span.textContent = line;
      diffPre.appendChild(span);
    });

    // Test case
    document.getElementById('test-pre').textContent = r.test_case;

    document.getElementById('results').classList.add('visible');

    // Reset tabs to "Fixed"
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelector('[data-tab="fixed"]').classList.add('active');
    document.getElementById('tab-fixed').classList.add('active');
  }

  function prefill({ code, error, language, fileName }) {
    document.getElementById('code-input').value  = code;
    document.getElementById('error-input').value = error;
    // Select matching lang badge
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

  function setLoading(active) {
    document.getElementById('loading-bar').classList.toggle('active', active);
    document.getElementById('fix-btn').disabled = active;
    document.getElementById('fix-btn').textContent = active ? '⟳ Analyzing...' : '⚡ Fix My Bug';
    if (active) hideResults();
  }

  function showError(msg) {
    const box = document.getElementById('error-box');
    box.textContent = '✗ ' + msg;
    box.classList.add('visible');
  }
  function hideError() { document.getElementById('error-box').classList.remove('visible'); }
  function hideResults() { document.getElementById('results').classList.remove('visible'); }

  function resetForm() {
    document.getElementById('code-input').value  = '';
    document.getElementById('error-input').value = '';
    hideResults();
    hideError();
    currentFixedCode = '';
    document.getElementById('code-input').focus();
  }
</script>
</body>
</html>`;
}
