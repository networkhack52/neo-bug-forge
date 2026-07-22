/**
 * contextUtils.ts  —  Neo Bug Forge
 * ─────────────────────────────────────────────
 * Pure, dependency-light helpers extracted from contextCollector.ts and
 * extension.ts so they can be unit-tested WITHOUT importing the `vscode`
 * module (which only exists inside the extension host at runtime).
 *
 * Nothing in this file may import `vscode`.
 */

import * as path from "path";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface ContextFile {
  relativePath: string;
  content:      string;
  reason:       string;   // why it was included (open editor / same folder / symbol)
}

// ─── Constants ────────────────────────────────────────────────────────────────

export const SKIP_DIRS = new Set([
  "node_modules", "dist", "build", ".git", ".next", ".nuxt",
  "out", "coverage", "__pycache__", ".venv", "venv", ".mypy_cache",
  "target", "bin", "obj", ".turbo",
]);

export const SKIP_EXTENSIONS = new Set([
  ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
  ".woff", ".woff2", ".ttf", ".eot", ".otf",
  ".pdf", ".zip", ".tar", ".gz", ".7z",
  ".mp4", ".mp3", ".wav", ".avi", ".mov",
  ".exe", ".dll", ".so", ".dylib", ".class",
  ".pyc", ".pyo", ".lock",
]);

export const MAX_FILE_BYTES  = 50_000;   // 50 KB
export const MAX_LINE_LENGTH = 2_000;    // skip minified files

// ─── API key validation ───────────────────────────────────────────────────────

/** True if the string looks like a Neo Bug Forge API key. */
export function isValidApiKey(key: unknown): boolean {
  return typeof key === "string" && key.startsWith("nbf_");
}

// ─── File filtering predicates ─────────────────────────────────────────────────

/**
 * True if a file should be skipped based on its path alone:
 * a binary/asset extension, or any path segment that is a skip-dir.
 */
export function shouldSkipPath(filePath: string): boolean {
  const ext = path.extname(filePath).toLowerCase();
  if (SKIP_EXTENSIONS.has(ext)) return true;
  const segments = filePath.split(path.sep);
  return segments.some(s => SKIP_DIRS.has(s));
}

/** True if the content looks minified (has an extremely long line). */
export function isLikelyMinified(content: string): boolean {
  return content.split("\n").some(l => l.length > MAX_LINE_LENGTH);
}

// ─── Symbol extractor ──────────────────────────────────────────────────────────
// Pulls function/class names from selected code so we can search for them.

export function extractSymbols(code: string): string[] {
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

// ─── Context formatter ─────────────────────────────────────────────────────────
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
