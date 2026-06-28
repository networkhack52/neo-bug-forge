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

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ContextFile {
  relativePath: string;
  content:      string;
  reason:       string;   // why it was included (open editor / same folder / symbol)
}

// ─── Constants ────────────────────────────────────────────────────────────────

const SKIP_DIRS = new Set([
  "node_modules", "dist", "build", ".git", ".next", ".nuxt",
  "out", "coverage", "__pycache__", ".venv", "venv", ".mypy_cache",
  "target", "bin", "obj", ".turbo",
]);

const SKIP_EXTENSIONS = new Set([
  ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
  ".woff", ".woff2", ".ttf", ".eot", ".otf",
  ".pdf", ".zip", ".tar", ".gz", ".7z",
  ".mp4", ".mp3", ".wav", ".avi", ".mov",
  ".exe", ".dll", ".so", ".dylib", ".class",
  ".pyc", ".pyo", ".lock",
]);

const MAX_FILE_BYTES    = 50_000;   // 50 KB
const MAX_LINE_LENGTH   = 2_000;    // skip minified files
const TIMEOUT_MS        = 1_500;    // abort collection after 1.5 s

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
      const symbols = this._extractSymbols(selectedText, document.languageId);
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
      const ext = path.extname(filePath).toLowerCase();
      if (SKIP_EXTENSIONS.has(ext)) return null;

      // Skip any path segment that's a skip-dir
      const segments = filePath.split(path.sep);
      if (segments.some(s => SKIP_DIRS.has(s))) return null;

      const stat = fs.statSync(filePath);
      if (!stat.isFile() || stat.size > MAX_FILE_BYTES) return null;

      const content = fs.readFileSync(filePath, "utf8");

      // Skip minified files
      if (content.split("\n").some(l => l.length > MAX_LINE_LENGTH)) return null;

      const relativePath = path.relative(workspaceRoot, filePath).replace(/\\/g, "/");
      return { relativePath, content, reason };
    } catch {
      return null;
    }
  }

  // ─── Symbol extractor ────────────────────────────────────────────────────────
  // Pulls function/class names from selected code so we can search for them.

  private static _extractSymbols(code: string, _lang: string): string[] {
    const found = new Set<string>();
    const STOP  = new Set(["if","for","while","switch","return","const","let","var","import","export","from","class","function","async","await","true","false","null","undefined","new","this","super","extends","implements","interface","type","enum"]);

    const patterns = [
      /(?:function|class|def|func)\s+([A-Za-z_]\w+)/g,
      /(?:const|let|var)\s+([A-Za-z_]\w+)\s*=/g,
      /([A-Za-z_][A-Za-z0-9_]+)\s*\(/g,
    ];

    for (const rx of patterns) {
      let m: RegExpExecArray | null;
      while ((m = rx.exec(code)) !== null) {
        const sym = m[1];
        if (sym && sym.length >= 3 && !STOP.has(sym)) {
          found.add(sym);
        }
      }
    }

    return [...found].slice(0, 3); // search at most 3 symbols to stay fast
  }
}

// ─── Context formatter ────────────────────────────────────────────────────────
// Builds the context block that gets prepended to the broken_code field.

export function buildContextBlock(
  contextFiles: ContextFile[],
  brokenCode:   string,
  fileName:     string
): string {
  if (contextFiles.length === 0) return brokenCode;

  const lines: string[] = [
    "=== WORKSPACE CONTEXT ===",
    `The following ${contextFiles.length} file(s) are related to the broken code.`,
    "Use them to understand dependencies, types, and interfaces.",
    "",
  ];

  for (const f of contextFiles) {
    lines.push(`--- ${f.relativePath} (${f.reason}) ---`);
    lines.push(f.content.trimEnd());
    lines.push("");
  }

  lines.push(`=== BROKEN CODE (${fileName || "unknown"}) ===`);
  lines.push(brokenCode);

  return lines.join("\n");
}
