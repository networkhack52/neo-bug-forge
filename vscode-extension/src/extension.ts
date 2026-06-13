/**
 * extension.ts  —  Neo Bug Forge for VS Code
 * ─────────────────────────────────────────
 * Entry point. Registers three commands:
 *   1. neo-bug-forge.openPanel      → opens the side panel UI
 *   2. neo-bug-forge.fixSelection   → grabs selected code + prompts for error message,
 *                                 then opens panel pre-filled and auto-submits
 *   3. neo-bug-forge.setApiKey      → quick-input to store key in SecretStorage
 */

import * as vscode from "vscode";
import { NeoBugForgePanel } from "./panel";
import * as https from "https";

// ─── Exported activate / deactivate ──────────────────────────────────────────

export function activate(context: vscode.ExtensionContext) {
  // ── 1. Open Panel ──────────────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("neo-bug-forge.openPanel", () => {
      NeoBugForgePanel.createOrShow(context);
    })
  );

  // ── 2. Fix Selected Code (context menu + keybinding) ──────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("neo-bug-forge.fixSelection", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showWarningMessage("Neo Bug Forge: No active editor.");
        return;
      }

      const selection = editor.selection;
      const selectedText = editor.document.getText(selection);
      if (!selectedText.trim()) {
        vscode.window.showWarningMessage(
          "Neo Bug Forge: Please select some code first."
        );
        return;
      }

      // Ask for the error message inline
      const errorMessage = await vscode.window.showInputBox({
        title: "Neo Bug Forge — What's the error?",
        prompt: "Paste the error message or describe the bug",
        placeHolder: "e.g. TypeError: Cannot read properties of undefined",
        ignoreFocusOut: true,
      });

      if (errorMessage === undefined) {
        return; // user cancelled
      }

      // Open panel and send pre-filled data to it
      NeoBugForgePanel.createOrShow(context);
      NeoBugForgePanel.currentPanel?.prefillAndSubmit({
        code: selectedText,
        error: errorMessage,
        language: editor.document.languageId,
        fileName: editor.document.fileName.split("/").pop() ?? "",
      });
    })
  );

  // ── 3. Set API Key ─────────────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("neo-bug-forge.setApiKey", async () => {
      const key = await vscode.window.showInputBox({
        title: "Neo Bug Forge — Enter your API Key",
        prompt: "Get your key at neobugforge.io. Stored securely in VS Code.",
        placeHolder: "nbf_...",
        password: true,
        ignoreFocusOut: true,
      });

      if (key) {
        if (!key.startsWith("nbf_")) {
          vscode.window.showErrorMessage(
            "Neo Bug Forge: Key must start with nbf_. Get yours at neobugforge.io"
          );
          return;
        }
        await context.secrets.store("neo-bug-forge.apiKey", key);
        vscode.window.showInformationMessage(
          "Neo Bug Forge: API key saved securely ✓"
        );
      }
    })
  );
}

export function deactivate() {
  NeoBugForgePanel.currentPanel?.dispose();
}

// ─── Core fix function (called by the panel via message passing) ──────────────

const API_BASE = "https://api.neobugforge.io";

export async function runBugForge(
  context: vscode.ExtensionContext,
  payload: { code: string; error: string; language: string }
): Promise<{ fixed_code: string; explanation: string; root_cause: string; confidence: number; diff: string; test_case: string }> {

  // Resolve API key from SecretStorage
  let apiKey = await context.secrets.get("neo-bug-forge.apiKey");
  if (!apiKey) {
    throw new Error(
      'No API key found. Run "Neo Bug Forge: Set API Key" to add one.'
    );
  }

  const body = JSON.stringify({
    broken_code:   payload.code,
    error_message: payload.error || "",
    language:      payload.language || "",
  });

  return new Promise((resolve, reject) => {
    const url = new URL(`${API_BASE}/v1/fix`);
    const req = https.request(
      {
        hostname: url.hostname,
        path:     url.pathname,
        method:   "POST",
        headers:  {
          "Content-Type":  "application/json",
          "X-API-Key":     apiKey!,
          "Content-Length": Buffer.byteLength(body),
        },
      },
      (res) => {
        let data = "";
        res.on("data", (chunk) => (data += chunk));
        res.on("end", () => {
          if (res.statusCode === 401) {
            return reject(new Error("Invalid API key. Run \"Neo Bug Forge: Set API Key\" to update it."));
          }
          if (res.statusCode === 402) {
            return reject(new Error("Quota exhausted. Upgrade at neobugforge.io"));
          }
          if (res.statusCode === 429) {
            return reject(new Error("Rate limit hit. Please wait a moment and try again."));
          }
          if (!res.statusCode || res.statusCode >= 400) {
            return reject(new Error(`API error ${res.statusCode}: ${data}`));
          }
          try {
            resolve(JSON.parse(data));
          } catch {
            reject(new Error("Failed to parse API response."));
          }
        });
      }
    );
    req.on("error", (e) => reject(new Error(`Network error: ${e.message}`)));
    req.write(body);
    req.end();
  });
}

