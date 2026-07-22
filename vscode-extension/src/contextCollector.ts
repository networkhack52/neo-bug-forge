/**
 * contextCollector.ts  —  Neo Bug Forge v1.2.0
 * ─────────────────────────────────────────────
 * Automatically finds the most relevant workspace files to include
 * as context when the user triggers a bug fix.
 *
 * Priority order:
 *   1. Currently open editors (excluding the source file)
 *   2. Files in the same folder
 *   3. Files that reference a symbol found in the selected code
 *
 * Safety limits:
 *   - Hard timeout: 1500ms — if collection takes longer, returns what it has
 *   - Skips: node_modules, dist, .git, binary files, minified files (>2000 char lines)
 *   - Max file size: 50 KB per file
 *   - Max files: configurable (default 5)
 */

import * as vscode from "vscode";
import * as path   from "path";
import * as fs     from "fs";

import {
  ContextFile,
  MAX_FILE_BYTES,
  extractSymbols,
  shouldSkipPath,
  isLikelyMinified,
  buildContextBlock,
} from "./contextUtils";

// Re-export so existing importers (extension.ts) keep working unchanged.
export { ContextFile, buildContextBlock } from "./contextUtils";

// ─── Constants ────────────────────────────────────────────────────────────────

const TIMEOUT_MS = 1_500;    // abort collection after 1.5 s

// ─── Main export ──────────────────────────────────────────────────────────────

export class ContextCollector {

  /**
   * Collects the most relevant context files for a bug fix.
   * Returns an empty array if context is disabled, workspace is unavailable,
   * or collection times out.
   */
  static async collect(
    document:     vscode.TextDocument,
    selection:    vscode.Selection,
    selectedText: string
  ): Promise<ContextFile[]> {
    const cfg      = vscode.workspace.getConfiguration("neo-bug-forge.context");
    const enabled  = cfg.get<boolean>("enabled", true);
    if (!enabled) return [];

    const maxFiles     = cfg.get<number>("maxFiles", 5);
    const workspaceFolder = vscode.workspace.getWorkspaceFolder(document.uri);
    if (!workspaceFolder) return [];

    const workspaceRoot = workspaceFolder.uri.fsPath;

    // Race collection against timeout so the UI never blocks
    return Promise.race([
      this._collectFiles(document, selectedText, workspaceRoot, maxFiles),
      new Promise<ContextFile[]>(resolve =>
        setTimeout(() => resolve([]), TIMEOUT_MS)
      ),
    ]);
  }

  // ─── Collection pipeline ────────────────────────────────────────────────────

  private static async _collectFiles(
    document:     vscode.TextDocument,
    selectedText: string,
    workspaceRoot: string,
    maxFiles:     number
  ): Promise<ContextFile[]> {
    const results: ContextFile[] = [];
    const seen = new Set<string>([document.uri.fsPath]); // always skip the source file

    // ── 1. Open editors ──────────────────────────────────────────────────────
    for (const group of vscode.window.tabGroups.all) {
      if (results.length >= maxFiles) break;
      for (const tab of group.tabs) {
        if (results.length >= maxFiles) break;
        const input = tab.input as { uri?: vscode.Uri } | undefined;
        if (!input?.uri) continue;
        if (seen.has(input.uri.fsPath)) continue;
        const file = this._readFile(input.uri.fsPath, workspaceRoot, "open editor");
        if (file) { results.push(file); seen.add(input.uri.fsPath); }
      }
    }

    // ── 2. Same folder ───────────────────────────────────────────────────────
    if (results.length < maxFiles) {
      const dir = path.dirname(document.uri.fsPath);
      try {
        const entries = fs.readdirSync(dir);
        for (const entry of entries) {
          if (results.length >= maxFiles) break;
          const full = path.join(dir, entry);
          if (seen.has(full)) continue;
          try {
            if (fs.statSync(full).isDirectory()) continue;
          } catch { continue; }
          const file = this._readFile(full, workspaceRoot, "same folder");
          if (file) { results.push(file); seen.add(full); }
        }
      } catch { /* directory unreadable — skip */ }
    }

    // ── 3. Symbol search ─────────────────────────────────────────────────────
    if (results.length < maxFiles) {
      const symbols = extractSymbols(selectedText);
      if (symbols.length > 0) {
        try {
          const uris = await vscode.workspace.findFiles(
            "**/*.{ts,tsx,js,jsx,py,java,go,rs,cpp,c,cs,rb,php,swift,kt}",
            "{node_modules,dist,build,.git,out,coverage}/**",
            30
          );
          for (const uri of uris) {
            if (results.length >= maxFiles) break;
            if (seen.has(uri.fsPath)) continue;
            try {
              const raw = fs.readFileSync(uri.fsPath, "utf8");
              const matchedSymbol = symbols.find(s => raw.includes(s));
              if (!matchedSymbol) continue;
              const file = this._readFile(uri.fsPath, workspaceRoot, `references '${matchedSymbol}'`);
              if (file) { results.push(file); seen.add(uri.fsPath); }
            } catch { continue; }
          }
        } catch { /* findFiles failed — skip */ }
      }
    }

    return results.slice(0, maxFiles);
  }

  // ─── File reader ────────────────────────────────────────────────────────────

  private static _readFile(
    filePath:      string,
    workspaceRoot: string,
    reason:        string
  ): ContextFile | null {
    try {
      if (shouldSkipPath(filePath)) return null;

      const stat = fs.statSync(filePath);
      if (!stat.isFile() || stat.size > MAX_FILE_BYTES) return null;

      const content = fs.readFileSync(filePath, "utf8");

      // Skip minified files
      if (isLikelyMinified(content)) return null;

      const relativePath = path.relative(workspaceRoot, filePath).replace(/\\/g, "/");
      return { relativePath, content, reason };
    } catch {
      return null;
    }
  }
}
