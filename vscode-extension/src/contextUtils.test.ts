/**
 * Unit tests for the pure helpers in contextUtils.ts.
 * These need no `vscode` runtime — they run under plain vitest.
 */

import { describe, it, expect } from "vitest";
import {
  isValidApiKey,
  shouldSkipPath,
  isLikelyMinified,
  extractSymbols,
  buildContextBlock,
  MAX_LINE_LENGTH,
  ContextFile,
} from "./contextUtils";

describe("isValidApiKey", () => {
  it("accepts keys with the nbf_ prefix", () => {
    expect(isValidApiKey("nbf_abc123")).toBe(true);
  });

  it("rejects keys without the prefix", () => {
    expect(isValidApiKey("sk_abc123")).toBe(false);
    expect(isValidApiKey("abc")).toBe(false);
  });

  it("rejects empty string", () => {
    expect(isValidApiKey("")).toBe(false);
  });

  it("rejects non-string values", () => {
    expect(isValidApiKey(undefined)).toBe(false);
    expect(isValidApiKey(null)).toBe(false);
    expect(isValidApiKey(12345)).toBe(false);
  });
});

describe("shouldSkipPath", () => {
  it("skips binary/asset extensions", () => {
    expect(shouldSkipPath("/proj/logo.png")).toBe(true);
    expect(shouldSkipPath("/proj/font.woff2")).toBe(true);
    expect(shouldSkipPath("/proj/archive.zip")).toBe(true);
  });

  it("is case-insensitive on extension", () => {
    expect(shouldSkipPath("/proj/IMAGE.PNG")).toBe(true);
  });

  it("skips files inside skip-dirs anywhere in the path", () => {
    expect(shouldSkipPath("/proj/node_modules/foo/index.js")).toBe(true);
    expect(shouldSkipPath("/proj/dist/bundle.js")).toBe(true);
    expect(shouldSkipPath("/proj/.git/config")).toBe(true);
    expect(shouldSkipPath("/proj/__pycache__/mod.py")).toBe(true);
  });

  it("keeps ordinary source files", () => {
    expect(shouldSkipPath("/proj/src/index.ts")).toBe(false);
    expect(shouldSkipPath("/proj/api/main.py")).toBe(false);
  });

  it("does not skip a file merely because a substring resembles a skip-dir", () => {
    // "distribution" contains "dist" but is not the segment "dist".
    expect(shouldSkipPath("/proj/distribution/index.js")).toBe(false);
  });
});

describe("isLikelyMinified", () => {
  it("flags content with an extremely long line", () => {
    expect(isLikelyMinified("a".repeat(MAX_LINE_LENGTH + 1))).toBe(true);
  });

  it("does not flag normal multi-line content", () => {
    const normal = Array.from({ length: 200 }, () => "const x = 1;").join("\n");
    expect(isLikelyMinified(normal)).toBe(false);
  });

  it("does not flag content exactly at the limit", () => {
    expect(isLikelyMinified("a".repeat(MAX_LINE_LENGTH))).toBe(false);
  });
});

describe("extractSymbols", () => {
  it("extracts function and class names", () => {
    const syms = extractSymbols("function fetchUser() {}\nclass UserRepo {}");
    expect(syms).toContain("fetchUser");
    expect(syms).toContain("UserRepo");
  });

  it("extracts python def and go func names", () => {
    expect(extractSymbols("def compute_total():")).toContain("compute_total");
    expect(extractSymbols("func HandleRequest() {}")).toContain("HandleRequest");
  });

  it("extracts const/let/var assignments", () => {
    const syms = extractSymbols("const apiClient = makeClient()");
    expect(syms).toContain("apiClient");
  });

  it("filters out language keywords via the stop list", () => {
    const syms = extractSymbols("if (true) { return null; }");
    expect(syms).not.toContain("if");
    expect(syms).not.toContain("return");
    expect(syms).not.toContain("true");
  });

  it("ignores symbols shorter than 3 characters", () => {
    const syms = extractSymbols("fn ab() {}");
    expect(syms).not.toContain("ab");
  });

  it("returns at most 3 symbols", () => {
    const code = "aaa(); bbb(); ccc(); ddd(); eee();";
    expect(extractSymbols(code).length).toBeLessThanOrEqual(3);
  });

  it("returns an empty array when nothing matches", () => {
    expect(extractSymbols("+++ --- ///")).toEqual([]);
  });
});

describe("buildContextBlock", () => {
  const files: ContextFile[] = [
    { relativePath: "src/user.ts", content: "export const x = 1;\n", reason: "open editor" },
  ];

  it("returns the raw code unchanged when there are no context files", () => {
    expect(buildContextBlock([], "broken code", "a.ts")).toBe("broken code");
  });

  it("includes a header, each file with its reason, and the broken code", () => {
    const block = buildContextBlock(files, "BROKEN", "main.ts");
    expect(block).toContain("=== WORKSPACE CONTEXT ===");
    expect(block).toContain("--- src/user.ts (open editor) ---");
    expect(block).toContain("export const x = 1;");
    expect(block).toContain("=== BROKEN CODE (main.ts) ===");
    expect(block).toContain("BROKEN");
  });

  it("falls back to 'unknown' when no file name is given", () => {
    const block = buildContextBlock(files, "BROKEN", "");
    expect(block).toContain("=== BROKEN CODE (unknown) ===");
  });

  it("reports the correct file count", () => {
    const two: ContextFile[] = [...files, { relativePath: "b.ts", content: "x", reason: "same folder" }];
    expect(buildContextBlock(two, "c", "m.ts")).toContain("following 2 file(s)");
  });
});
