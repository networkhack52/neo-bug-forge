/**
 * extension.ts  —  Neo Bug Forge for VS Code
 * ─────────────────────────────────────────
 * Entry point. Registers commands:
 *   1. neo-bug-forge.openPanel      → opens the side panel UI
 *   2. neo-bug-forge.fixSelection   → grabs selected code + prompts for error,
 *                                     opens panel pre-filled and auto-submits
 *   3. neo-bug-forge.setApiKey      → quick-input to store key in SecretStorage
 *
 * v1.1.0 additions:
 *   - Stores FixContext (uri, selection, full doc) for diff preview
 *   - applyFixWithDiff()  → native VS Code diff editor + Accept/Stage flow
 *   - _gitStage()         → stages file via the built-in git extension
 */

import * as vscode from "vscode";
import * as https  from "https";
import * as crypto from "crypto";
import * as fs     from "fs";
import * as os     from "os";
import * as path   from "path";
import { NeoBugForgePanel } from "./panel";
import { ContextCollector, buildContextBlock, ContextFile } from "./contextCollector";
import { isValidApiKey } from "./contextUtils";
import { NbfCodeActionProvider } from "./diagnosticsProvider";

// ─── Fix context (populated when the user triggers fixSelection) ──────────────

export interface FixContext {
  originalUri:  vscode.Uri;
  selection:    vscode.Selection;
  originalText: string;   // selected text only
  fullDocText:  string;   // whole document at the moment of trigger
}

export let currentFixContext: FixContext | undefined;

// ─── Review prompt ────────────────────────────────────────────────────────────

const REVIEW_URL = "https://marketplace.visualstudio.com/items?itemName=neobugforge.neo-bug-forge&ssr=false#review-details";
const PROMPT_AT  = [3, 10, 25]; // show prompt at these fix counts

export async function trackFixAndPromptReview(context: vscode.ExtensionContext): Promise<void> {
  const count    = (context.globalState.get<number>("fixCount", 0)) + 1;
  const reviewed = context.globalState.get<boolean>("reviewDone", false);

  await context.globalState.update("fixCount", count);
  if (reviewed) return;

  if (!PROMPT_AT.includes(count)) return;

  const choice = await vscode.window.showInformationMessage(
    `Neo Bug Forge just fixed bug #${count} for you 🎉 — enjoying it?`,
    "⭐ Leave a Review",
    "Maybe Later",
    "Don't Ask Again"
  );

  if (choice === "⭐ Leave a Review") {
    vscode.env.openExternal(vscode.Uri.parse(REVIEW_URL));
    await context.globalState.update("reviewDone", true);
  } else if (choice === "Don't Ask Again") {
    await context.globalState.update("reviewDone", true);
  }
}

// ─── Activate ─────────────────────────────────────────────────────────────────

export function activate(context: vscode.ExtensionContext) {

  // ── Welcome prompt on first install ──────────────────────────────────────────
  const hasSeenWelcome = context.globalState.get<boolean>("welcomeShown", false);
  if (!hasSeenWelcome) {
    context.globalState.update("welcomeShown", true);
    // Open built-in walkthrough for proper onboarding
    vscode.commands.executeCommand(
      "workbench.action.openWalkthrough",
      "neobugforge.neo-bug-forge#neo-bug-forge.gettingStarted",
      false
    );
    vscode.window.showInformationMessage(
      "Welcome to Neo Bug Forge! Follow the guide to fix your first bug.",
      "I Have a Key"
    ).then(choice => {
      if (choice === "I Have a Key") {
        vscode.commands.executeCommand("neo-bug-forge.setApiKey");
      }
    });
  }

  // ── Re-engage existing users who never tried it (v1.5.8 nudge) ───────────────
  const nudgeKey  = "nudge158Shown";
  const fixCount  = context.globalState.get<number>("fixCount", 0);
  const nudgeDone = context.globalState.get<boolean>(nudgeKey, false);
  if (!nudgeDone && hasSeenWelcome && fixCount === 0) {
    // Existing user, installed before, never ran a fix — show one-time nudge
    context.globalState.update(nudgeKey, true);
    setTimeout(() => {
      vscode.window.showInformationMessage(
        "⚡ Neo Bug Forge: see AI fix a real bug in 3 seconds — free, no setup needed.",
        "Show me",
        "Not now"
      ).then(choice => {
        if (choice === "Show me") {
          NeoBugForgePanel.createOrShow(context);
          setTimeout(() => {
            NeoBugForgePanel.currentPanel?.prefillAndSubmit({
              code: `def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

# Test
print(calculate_average([10, 20, 30]))
print(calculate_average([]))`,
              error: "ZeroDivisionError: division by zero",
              language: "python",
              fileName: "example.py",
              contextCount: 0,
            });
          }, 800);
        }
      });
    }, 3000); // 3s delay so VS Code finishes loading first
  }

  // -- Contextual error nudge (v1.5.15): fires when user has real errors --
  // Reaches existing installs who never activated, in the moment they need it.
  const nudge1515Key  = "nudge1515Shown";
  const nudge1515Done = context.globalState.get<boolean>(nudge1515Key, false);
  const currentFixCount = context.globalState.get<number>("fixCount", 0);

  if (!nudge1515Done && currentFixCount === 0) {
    let errorNudgeDisposable: vscode.Disposable | undefined;

    const tryShowErrorNudge = async () => {
      if (context.globalState.get<boolean>(nudge1515Key, false)) { return; }

      const editor = vscode.window.activeTextEditor;
      if (!editor) { return; }

      const errors = vscode.languages.getDiagnostics(editor.document.uri)
        .filter(d => d.severity === vscode.DiagnosticSeverity.Error);

      if (errors.length === 0) { return; }

      // Mark shown immediately to prevent double-firing
      await context.globalState.update(nudge1515Key, true);
      errorNudgeDisposable?.dispose();

      const label = errors.length === 1 ? "1 error" : `${errors.length} errors`;
      const choice = await vscode.window.showInformationMessage(
        `Neo Bug Forge: ${label} detected in this file — fix with AI in one click?`,
        "Fix Now",
        "Dismiss"
      );

      if (choice === "Fix Now") {
        vscode.commands.executeCommand(
          "neo-bug-forge.fixDiagnostic",
          editor.document,
          errors[0]
        );
      }
    };

    // Listen for diagnostics changes (catches new errors as they appear)
    errorNudgeDisposable = vscode.languages.onDidChangeDiagnostics(() => {
      tryShowErrorNudge();
    });
    context.subscriptions.push(errorNudgeDisposable);

    // Also check immediately in case errors already exist when VS Code loads
    setTimeout(tryShowErrorNudge, 4000);
  }


  // ── Status bar item — always visible, one click to open panel ───────────────
  const statusBar = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    0
  );
  statusBar.text       = "⚡ Neo Bug Forge";
  statusBar.tooltip    = "Fix bugs with AI — click to try free";
  statusBar.command    = "neo-bug-forge.openPanel";
  statusBar.show();
  context.subscriptions.push(statusBar);

  // ── 0. Inline diagnostics — lightbulb quick fix ──────────────────────────────
  context.subscriptions.push(
    vscode.languages.registerCodeActionsProvider(
      [{ scheme: "file" }, { scheme: "untitled" }],
      new NbfCodeActionProvider(),
      { providedCodeActionKinds: NbfCodeActionProvider.providedCodeActionKinds }
    )
  );

  context.subscriptions.push(
    vscode.commands.registerCommand(
      "neo-bug-forge.fixDiagnostic",
      async (document: vscode.TextDocument, diagnostic: vscode.Diagnostic) => {
        // Make sure the document is open in the editor
        let activeEditor = vscode.window.activeTextEditor;
        if (!activeEditor || activeEditor.document.uri.toString() !== document.uri.toString()) {
          try {
            await vscode.window.showTextDocument(document, { preserveFocus: false });
            activeEditor = vscode.window.activeTextEditor;
          } catch {
            vscode.window.showWarningMessage("Neo Bug Forge: Could not open file.");
            return;
          }
        }
        if (!activeEditor) return;

        // Grab a few lines around the diagnostic for context
        const diagRange  = diagnostic.range;
        const startLine  = Math.max(0, diagRange.start.line - 3);
        const endLine    = Math.min(document.lineCount - 1, diagRange.end.line + 3);
        const contextRange = new vscode.Range(
          startLine, 0,
          endLine, document.lineAt(endLine).text.length
        );
        const selectedText = document.getText(contextRange);

        // Store fix context so diff preview works
        currentFixContext = {
          originalUri:  document.uri,
          selection:    new vscode.Selection(contextRange.start, contextRange.end),
          originalText: selectedText,
          fullDocText:  document.getText(),
        };

        const errorMessage = diagnostic.message;
        const fileName     = path.basename(document.fileName);

        NeoBugForgePanel.createOrShow(context);
        NeoBugForgePanel.currentPanel?.sendStatus("scanning");

        let contextFiles: ContextFile[] = [];
        try {
          contextFiles = await ContextCollector.collect(
            document,
            new vscode.Selection(diagRange.start, diagRange.end),
            selectedText
          );
        } catch { /* ignore */ }

        NeoBugForgePanel.currentPanel?.prefillAndSubmit({
          code:         buildContextBlock(contextFiles, selectedText, fileName),
          error:        errorMessage || "Fix any bugs or issues in this code.",
          language:     document.languageId,
          fileName,
          contextCount: contextFiles.length,
        });
      }
    )
  );

  // ── 1. Open Panel ────────────────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("neo-bug-forge.openPanel", () => {
      NeoBugForgePanel.createOrShow(context);
      // First-time users: auto-run demo so they immediately see AI working
      const fixCount = context.globalState.get<number>("fixCount", 0);
      if (fixCount === 0) {
        setTimeout(() => {
          NeoBugForgePanel.currentPanel?.prefillAndSubmit({
            code: `def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

# Test
print(calculate_average([10, 20, 30]))
print(calculate_average([]))`,
            error: "ZeroDivisionError: division by zero",
            language: "python",
            fileName: "example.py",
            contextCount: 0,
          });
        }, 800);
      }
    })
  );

  // ── 2. Fix Selected Code ─────────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("neo-bug-forge.fixSelection", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showWarningMessage("Neo Bug Forge: No active editor.");
        return;
      }

      const selection    = editor.selection;
      const selectedText = editor.document.getText(selection);
      if (!selectedText.trim()) {
        vscode.window.showWarningMessage("Neo Bug Forge: Please select some code first.");
        return;
      }

      // Snapshot context for diff preview later
      currentFixContext = {
        originalUri:  editor.document.uri,
        selection:    editor.selection,
        originalText: selectedText,
        fullDocText:  editor.document.getText(),
      };

      const errorMessage = await vscode.window.showInputBox({
        title:          "Neo Bug Forge — What's the error? (optional)",
        prompt:         "Paste the error or press Enter to skip",
        placeHolder:    "e.g. TypeError: Cannot read properties of undefined (or leave blank)",
        ignoreFocusOut: true,
      });
      if (errorMessage === undefined) return; // user pressed Escape

      const fileName = path.basename(editor.document.fileName);

      // Open panel immediately so the user sees activity right away
      NeoBugForgePanel.createOrShow(context);

      // Tell the panel we're scanning for context files
      NeoBugForgePanel.currentPanel?.sendStatus("scanning");

      // Collect related workspace files for deeper context (best-effort)
      let contextFiles: ContextFile[] = [];
      try {
        contextFiles = await ContextCollector.collect(
          editor.document,
          editor.selection,
          selectedText
        );
      } catch { /* never block the fix on context failure */ }

      NeoBugForgePanel.currentPanel?.prefillAndSubmit({
        code:         buildContextBlock(contextFiles, selectedText, fileName),
        error:        errorMessage,
        language:     editor.document.languageId,
        fileName:     fileName,
        contextCount: contextFiles.length,
      });
    })
  );

  // ── 3. Set API Key ───────────────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("neo-bug-forge.setApiKey", async () => {
      const key = await vscode.window.showInputBox({
        title:          "Neo Bug Forge — Enter your API Key",
        prompt:         "Get your key at neobugforge.io. Stored securely in VS Code.",
        placeHolder:    "nbf_...",
        password:       true,
        ignoreFocusOut: true,
      });

      if (key) {
        if (!isValidApiKey(key)) {
          vscode.window.showErrorMessage(
            "Neo Bug Forge: Key must start with nbf_. Get yours at neobugforge.io"
          );
          return;
        }
        await context.secrets.store("neo-bug-forge.apiKey", key);
        vscode.window.showInformationMessage("Neo Bug Forge: API key saved securely ✓");
      }
    })
  );

  // ── 4. Explain Code ──────────────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("neo-bug-forge.explainCode", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) { vscode.window.showWarningMessage("Neo Bug Forge: No active editor."); return; }
      const sel  = editor.selection;
      const code = editor.document.getText(sel.isEmpty ? undefined : sel);
      if (!code.trim()) { vscode.window.showWarningMessage("Neo Bug Forge: Select some code to explain."); return; }

      await vscode.window.withProgress(
        { location: vscode.ProgressLocation.Notification, title: "Neo Bug Forge: Explaining…", cancellable: false },
        async () => {
          try {
            const result = await _callReadApi(context, { code, language: editor.document.languageId });
            const ch = vscode.window.createOutputChannel("Neo Bug Forge — Explain");
            ch.clear();
            ch.appendLine("━━━ CODE EXPLANATION ━━━━━━━━━━━━━━━━━━━━━━━\n");
            ch.appendLine(`📝 Summary\n${result.summary}\n`);
            ch.appendLine(`⚙️  What it does\n${result.what_it_does}\n`);
            if (result.potential_issues?.length) {
              ch.appendLine("⚠️  Potential issues");
              result.potential_issues.forEach((issue: string) => ch.appendLine(`   • ${issue}`));
              ch.appendLine("");
            }
            ch.appendLine(`📊 Complexity: ${result.complexity}   🔤 Language: ${result.language}`);
            ch.show(true);
          } catch (e: any) {
            vscode.window.showErrorMessage(`Neo Bug Forge: ${e.message}`);
          }
        }
      );
    })
  );

  // ── 5. Write Test ─────────────────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("neo-bug-forge.writeTest", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) { vscode.window.showWarningMessage("Neo Bug Forge: No active editor."); return; }
      const sel  = editor.selection;
      const code = editor.document.getText(sel.isEmpty ? undefined : sel);
      if (!code.trim()) { vscode.window.showWarningMessage("Neo Bug Forge: Select some code to test."); return; }

      currentFixContext = {
        originalUri:  editor.document.uri,
        selection:    editor.selection,
        originalText: code,
        fullDocText:  editor.document.getText(),
      };

      NeoBugForgePanel.createOrShow(context);
      setTimeout(() => {
        NeoBugForgePanel.currentPanel?.prefillAndSubmit({
          code,
          error:        "Write comprehensive unit tests for this code. Include edge cases and clear test names.",
          language:     editor.document.languageId,
          fileName:     path.basename(editor.document.fileName),
          contextCount: 0,
        });
      }, 600);
    })
  );
}

export function deactivate() {
  NeoBugForgePanel.currentPanel?.dispose();
}

// ─── Apply fix using VS Code's native diff editor ────────────────────────────

export async function applyFixWithDiff(fixedCode: string): Promise<void> {
  if (!currentFixContext) {
    vscode.window.showWarningMessage(
      "Neo Bug Forge: Open a file, select the broken code, and use Ctrl+Shift+F to get a fix."
    );
    return;
  }

  const { originalUri, selection } = currentFixContext;

  let doc: vscode.TextDocument;
  try {
    doc = await vscode.workspace.openTextDocument(originalUri);
  } catch {
    vscode.window.showErrorMessage("Neo Bug Forge: Could not open original file.");
    return;
  }

  // Apply fix directly -- no diff tab, stays in the same editor
  const editor = await vscode.window.showTextDocument(originalUri);
  const success = await editor.edit(editBuilder => {
    const range = selection.isEmpty
      ? new vscode.Range(doc.positionAt(0), doc.positionAt(doc.getText().length))
      : selection;
    editBuilder.replace(range, fixedCode);
  });

  if (!success) {
    vscode.window.showErrorMessage("Neo Bug Forge: Could not apply fix.");
    return;
  }

  await editor.document.save();

  const choice = await vscode.window.showInformationMessage(
    "Neo Bug Forge: Fix applied ✓",
    "Undo",
    "Git Stage"
  );

  if (choice === "Undo") {
    await vscode.commands.executeCommand("undo");
  } else if (choice === "Git Stage") {
    await _gitStage(originalUri);
  }
}


// ─── Git stage helper ─────────────────────────────────────────────────────────

async function _gitStage(uri: vscode.Uri): Promise<void> {
  try {
    const gitExt = vscode.extensions.getExtension("vscode.git");
    if (!gitExt) throw new Error("Git extension not found");

    const api  = gitExt.exports.getAPI(1);
    const repo = api.repositories.find(
      (r: { rootUri: vscode.Uri }) => uri.fsPath.startsWith(r.rootUri.fsPath)
    );
    if (!repo) throw new Error("File is not inside a git repository");

    await repo.add([uri.fsPath]);
    vscode.window.showInformationMessage("Neo Bug Forge: Fix applied and staged ✓");
  } catch (e) {
    vscode.window.showInformationMessage(
      `Neo Bug Forge: Fix applied ✓  (git stage skipped — ${e instanceof Error ? e.message : e})`
    );
  }
}

// ─── Core API call ────────────────────────────────────────────────────────────

export async function runBugForge(
  context: vscode.ExtensionContext,
  payload: { code: string; error: string; language: string }
): Promise<{
  fixed_code:  string;
  explanation: string;
  root_cause:  string;
  confidence:  number;
  diff:        string;
  test_case:   string;
}> {
  const apiKey    = await context.secrets.get("neo-bug-forge.apiKey");
  const installId  = _getOrCreateInstallId(context);

  // ── No API key → use public endpoint (10 free fixes/day) ──────────────────
  if (!apiKey) {
    const result = await _callApi("/v1/fix/public", payload, undefined, installId);
    // After the fix lands, show a gentle conversion prompt (fire-and-forget)
    _promptSignupAfterPublicFix(context).catch(() => {});
    return result;
  }

  // ── Authenticated fix ───────────────────────────────────────────�
  // -- Authenticated fix
  return _callApi("/v1/fix", payload, apiKey, installId);
}

// --- Conversion prompt after anonymous fix ---

async function _promptSignupAfterPublicFix(context: vscode.ExtensionContext): Promise<void> {
  const count = (context.globalState.get<number>("publicFixCount", 0)) + 1;
  await context.globalState.update("publicFixCount", count);

  // Prompt after fix #1, #3, #5
  if (![1, 3, 5].includes(count)) { return; }

  const msg = count === 1
    ? "First fix done! Get a free account for 100 fixes/month."
    : `You've used ${count} free fixes. Sign up for 100/month -- free, no credit card.`;

  const choice = await vscode.window.showInformationMessage(
    msg,
    "Sign Up Free",
    "I Have a Key"
  );

  if (choice === "Sign Up Free") {
    vscode.env.openExternal(vscode.Uri.parse("https://app.neobugforge.io/signup?ref=extension-trial"));
  } else if (choice === "I Have a Key") {
    vscode.commands.executeCommand("neo-bug-forge.setApiKey");
  }
}

// --- Stable install ID (sent as X-Install-Id, lets us count unique users) ---

function _getOrCreateInstallId(context: vscode.ExtensionContext): string {
  const key = "installId";
  let id = context.globalState.get<string>(key);
  if (!id) {
    id = crypto.randomUUID();
    context.globalState.update(key, id);
  }
  return id;
}

// --- Shared HTTP helper ---

function _callApi(
  path: string,
  payload: { code: string; error: string; language: string },
  apiKey: string | undefined,
  installId?: string
): Promise<{
  fixed_code:  string;
  explanation: string;
  root_cause:  string;
  confidence:  number;
  diff:        string;
  test_case:   string;
}> {
  const body = JSON.stringify({
    broken_code:   payload.code,
    error_message: payload.error    || "",
    language:      payload.language || "",
  });

  const headers: Record<string, string | number> = {
    "Content-Type":   "application/json",
    "Content-Length": Buffer.byteLength(body),
  };
  if (apiKey)     { headers["X-API-Key"]    = apiKey; }
  if (installId)  { headers["X-Install-Id"] = installId; }

  return new Promise((resolve, reject) => {
    const req = https.request(
      { hostname: "api.neobugforge.io", path, method: "POST", headers },
      (res) => {
        let data = "";
        res.on("data",  (chunk) => (data += chunk));
        res.on("end",   () => {
          if (res.statusCode === 401) return reject(new Error('Invalid API key. Run "Neo Bug Forge: Set API Key" to update it.'));
          if (res.statusCode === 402) return reject(new Error("Quota exhausted. Upgrade at neobugforge.io"));
          if (res.statusCode === 429) return reject(new Error("Daily free limit reached. Sign up for 100 fixes/month -- free at neobugforge.io"));
          if (!res.statusCode || res.statusCode >= 400) return reject(new Error(`API error ${res.statusCode}: ${data}`));
          try   { resolve(JSON.parse(data)); }
          catch { reject(new Error("Failed to parse API response.")); }
        });
      }
    );
    req.on("error", (e) => reject(new Error(`Network error: ${e.message}`)));
    // 35s timeout -- Render free tier has cold starts up to ~30s on first hit
    req.setTimeout(35_000, () => {
      req.destroy();
      reject(new Error("Request timed out -- the API is waking up. Please try again in a moment."));
    });
    req.write(body);
    req.end();
  });
}

// --- Read API call (explain code) ---

async function _callReadApi(
  context: vscode.ExtensionContext,
  payload: { code: string; language: string }
): Promise<{ summary: string; what_it_does: string; potential_issues: string[]; complexity: string; language: string }> {
  const apiKey    = await context.secrets.get("neo-bug-forge.apiKey");
  const installId = _getOrCreateInstallId(context);
  const apiPath   = "/v1/read/public"; // /v1/read (auth) not yet implemented

  const body = JSON.stringify({ code: payload.code, language: payload.language });
  const headers: Record<string, string | number> = {
    "Content-Type":   "application/json",
    "Content-Length": Buffer.byteLength(body),
  };
  if (apiKey)    { headers["X-API-Key"]    = apiKey; }
  if (installId) { headers["X-Install-Id"] = installId; }

  return new Promise((resolve, reject) => {
    const req = https.request(
      { hostname: "api.neobugforge.io", path: apiPath, method: "POST", headers },
      (res) => {
        let data = "";
        res.on("data",  (chunk) => (data += chunk));
        res.on("end",   () => {
          if (res.statusCode === 429) return reject(new Error("Daily free limit reached. Sign up at neobugforge.io"));
          if (!res.statusCode || res.statusCode >= 400) return reject(new Error(`API error ${res.statusCode}`));
          try   { resolve(JSON.parse(data)); }
          catch { reject(new Error("Failed to parse response.")); }
        });
      }
    );
    req.on("error",  (e) => reject(new Error(`Network error: ${e.message}`)));
    req.setTimeout(35_000, () => {
      req.destroy();
      reject(new Error("Request timed out -- the API is waking up. Please try again."));
    });
    req.write(body);
    req.end();
  });
}
