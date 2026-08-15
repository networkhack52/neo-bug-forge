#!/usr/bin/env node
// Attestly copy lint. Run: node copy-lint.mjs   (defaults to marketing pitch + product UI)
// Enforces the Voice & copy rules (PLAYBOOK §10) on customer-facing copy.
// Exits 1 on any error-level hit, so it works as a CI gate or pre-commit hook.
import { readFileSync } from "node:fs";
import { globSync } from "node:fs";

if (typeof globSync !== "function") {
  console.error("copy-lint: needs Node 22+ (built-in fs.globSync). Skipping. Upgrade Node, or swap in fast-glob.");
  process.exit(0);
}

const RULES = [
  // char rules
  { id: "em-dash", re: /[—–]/g, level: "error",
    msg: "Em/en dash. Use a comma, a period, or a colon." },
  { id: "smart-quote", re: /[“”‘’]/g, level: "warn",
    msg: "Curly quote. Fine in prose, breaks in code samples and some meta tags." },

  // hype words: the ones this audience reads as vendor noise
  { id: "hype", re: /\b(game[- ]?chang(er|ing)|revolutionary|seamless(ly)?|effortless(ly)?|supercharge|unlock the power|cutting[- ]edge|world[- ]class|best[- ]in[- ]class|leverage)\b/gi,
    level: "error", msg: "Hype word. Say the concrete thing instead." },

  // filler
  { id: "filler", re: /\b(really|very|just|basically|literally|actually|simply)\b/gi,
    level: "warn", msg: "Filler. Cut it and the sentence gets stronger." },

  // filler openers
  { id: "opener", re: /(^|[.!?]\s+)(In today's|Let me tell you|The truth is|Here's the thing)/gi,
    level: "error", msg: "Throat-clearing opener. Start on the claim." },

  // claims you cannot back yet, pre-launch
  { id: "unbacked-claim", re: /\b(\d{2,3}%\s*(accurate|accuracy)|trusted by|thousands of (teams|companies)|industry[- ]leading)\b/gi,
    level: "error", msg: "Claim you cannot evidence yet. Attestly is pre-launch." },

  // spelled numbers under 10 in marketing copy
  { id: "spelled-number", re: /\b(one|two|three|four|five|six|seven|eight|nine)\s+(questionnaires?|hours?|days?|minutes?|answers?|controls?|policies)\b/gi,
    level: "warn", msg: "Use digits for numbers in marketing copy." },
];

// Skip anything inside code fences or JSX className/style strings.
const strip = (s) =>
  s.replace(/```[\s\S]*?```/g, (m) => " ".repeat(m.length))
   .replace(/`[^`\n]*`/g, (m) => " ".repeat(m.length))
   .replace(/className="[^"]*"/g, (m) => " ".repeat(m.length))
   .replace(/https?:\/\/\S+/g, (m) => " ".repeat(m.length));

// Default scope = the brand-voice surfaces: the marketing pitch + product UI.
// The legal templates (terms/privacy/dpa.html) are intentionally excluded —
// formal, lawyer-owned register where our voice rules don't apply. Pass an
// explicit glob to lint anything else.
const patterns = process.argv.slice(2);
if (patterns.length === 0) patterns.push("marketing/index.html", "frontend/src/**/*.{jsx,js}");
const files = patterns.flatMap((p) =>
  globSync(p, { exclude: (n) => /node_modules|\.next|dist|build/.test(n) })
);

let errors = 0, warns = 0;
for (const file of files) {
  const raw = readFileSync(file, "utf8");
  const text = strip(raw);
  for (const rule of RULES) {
    rule.re.lastIndex = 0;
    let m;
    while ((m = rule.re.exec(text))) {
      const line = raw.slice(0, m.index).split("\n").length;
      const tag = rule.level === "error" ? "ERROR" : "warn ";
      console.log(`${tag} ${file}:${line}  [${rule.id}] "${m[0].trim()}"  ${rule.msg}`);
      rule.level === "error" ? errors++ : warns++;
      if (m[0].length === 0) rule.re.lastIndex++;
    }
  }
}

console.log(`\n${errors} error(s), ${warns} warning(s), ${files.length} file(s) scanned.`);
process.exit(errors > 0 ? 1 : 0);
