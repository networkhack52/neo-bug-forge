"""
bug_fixer.py
------------
Enhanced AI-powered bug fixer using Anthropic Claude.
Now with: multi-language support, context awareness, history,
token/cost tracking, retry logic, and model-aware pricing.

Usage:
    python bug_fixer.py                          # interactive mode
    python bug_fixer.py -c code.py -e error.txt  # file mode
    python bug_fixer.py -c "x=1/0" -e "ZeroDivisionError" --language python
"""

import os
import json
import sys
import time
import argparse
import datetime
import re
from pathlib import Path
from typing import Optional

import anthropic


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL      = "claude-sonnet-4-20250514"   # Updated to latest model
MAX_TOKENS = 2048
HISTORY_FILE = Path("bugfix_history.json")
MAX_HISTORY  = 10

# Pricing per million tokens — keyed by model so cost stays accurate
# if you switch models. Update when Anthropic changes pricing.
PRICING = {
    "claude-sonnet-4-20250514":   {"input": 3.00,  "output": 15.00},
    "claude-opus-4-20250514":     {"input": 15.00, "output": 75.00},
    "claude-haiku-4-5-20251001":  {"input": 0.80,  "output": 4.00},
}

# Supported languages and their detection signatures
LANGUAGE_SIGNATURES = {
    "Python":     ["def ",      "import ",     "print(",    "elif ",     "None",    "True",    "False",   "self."],
    "TypeScript": ["interface ","): void",     ": string",  ": number",  ": boolean","<T>",    "as const","readonly "],
    "JavaScript": ["function ", "console.log", "var ",      "const ",    "=>",      "require(","undefined","document."],
    "Java":       ["public class","System.out","void ",     "import java","@Override","extends","implements"],
    "Rust":       ["fn ",       "let mut",     "println!(", "impl ",     "use std", "unwrap(", "Option<", "Result<"],
    "Go":         ["func ",     "fmt.Println", "package ",  ":= ",       "import (","goroutine","chan "],
    "C++":        ["#include",  "std::",       "cout <<",   "int main",  "namespace","template","vector<"],
    "Ruby":       ["def ",      "puts ",       "end\n",     "require '", "attr_",   "do |",    ".each"],
    "PHP":        ["<?php",     "echo ",       "->",        "function ", "$_GET",   "$_POST",  "array("],
    "HTML/CSS":   ["<html",     "<div",        "<body",     "<!DOCTYPE", "margin:", "padding:","display:"],
}


# ---------------------------------------------------------------------------
# History Manager
# ---------------------------------------------------------------------------

def load_history() -> list:
    """Load fix history from disk. Returns empty list if file missing or corrupt."""
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
    return []


def save_to_history(entry: dict):
    """Append an entry to history, keeping only the most recent MAX_HISTORY."""
    history = load_history()
    history.append(entry)
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    try:
        HISTORY_FILE.write_text(
            json.dumps(history, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except OSError as e:
        print(f"⚠  Warning: could not save history — {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Language Detection
# ---------------------------------------------------------------------------

def detect_language(code: str, hint: str = "") -> str:
    """
    Detect programming language from code content.
    If a hint is provided (e.g. from --language flag or file extension),
    it takes priority over auto-detection.
    """
    if hint:
        # Normalise hint — accept "py", "js", "ts" shorthands
        aliases = {
            "py": "Python", "js": "JavaScript", "ts": "TypeScript",
            "rs": "Rust",   "rb": "Ruby",       "cpp": "C++",
        }
        return aliases.get(hint.lower(), hint.capitalize())

    scores = {lang: 0 for lang in LANGUAGE_SIGNATURES}
    for lang, signatures in LANGUAGE_SIGNATURES.items():
        for sig in signatures:
            if sig in code:
                scores[lang] += 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Unknown"


# ---------------------------------------------------------------------------
# Prompt Builder
# ---------------------------------------------------------------------------

def build_prompt(broken_code: str, error_message: str,
                 language: str = "Unknown", context: str = "") -> str:
    context_section = (
        f"\n--- ADDITIONAL CONTEXT ---\n{context}\n"
        if context else ""
    )
    return f"""You are an expert software engineer and debugger specializing in {language}.

A developer has submitted broken code along with its error message.
Your job is to:
1. Analyze the root cause of the bug.
2. Fix the code without changing its original intent.
3. Return ONLY a valid raw JSON object — no markdown, no extra text.

The JSON must contain exactly these keys:
- "fixed_code":  the complete corrected code
- "explanation": concise plain-English explanation of the bug and fix

--- LANGUAGE ---
{language}

--- BROKEN CODE ---
{broken_code}

--- ERROR MESSAGE ---
{error_message}{context_section}

Respond with pure JSON only.
Example: {{"fixed_code": "...", "explanation": "..."}}"""


# ---------------------------------------------------------------------------
# Response Parser
# ---------------------------------------------------------------------------

def parse_response(raw_text: str) -> dict:
    """
    Parse Claude's response as JSON.
    Handles accidental markdown fences and falls back to regex extraction.
    """
    cleaned = raw_text.strip()

    # Strip markdown fences if present
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        end = -1 if lines[-1].strip() == "```" else len(lines)
        cleaned = "\n".join(lines[1:end])

    # Primary parse attempt
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: extract first {...} block using regex
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
            except (json.JSONDecodeError, ValueError) as exc:
                raise ValueError(
                    f"Could not parse JSON from response.\nRaw:\n{raw_text}"
                ) from exc
        else:
            raise ValueError(
                f"Claude returned non-JSON output.\nRaw:\n{raw_text}"
            )

    # Validate required keys
    for key in ("fixed_code", "explanation"):
        if key not in data:
            raise ValueError(f"Response JSON missing required key: '{key}'")

    return data


# ---------------------------------------------------------------------------
# Cost Calculator
# ---------------------------------------------------------------------------

def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """
    Calculate cost in USD using model-specific pricing.
    Falls back to Sonnet pricing if model not in table.
    """
    prices = PRICING.get(model, PRICING["claude-sonnet-4-20250514"])
    # Pricing is per million tokens
    return round(
        (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000,
        6
    )


# ---------------------------------------------------------------------------
# Retry Logic
# ---------------------------------------------------------------------------

def call_with_retry(client: anthropic.Anthropic, prompt: str,
                    max_retries: int = 3) -> anthropic.types.Message:
    """
    Call the Claude API with exponential backoff retry on rate limit errors.
    Retries: attempt 1 → wait 1s, attempt 2 → wait 2s, attempt 3 → raises.
    """
    for attempt in range(max_retries):
        try:
            return client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.RateLimitError:
            if attempt == max_retries - 1:
                raise  # Out of retries — propagate
            wait = 2 ** attempt  # 1s, 2s, 4s
            print(f"  ⏳ Rate limited — retrying in {wait}s... (attempt {attempt + 1}/{max_retries})")
            time.sleep(wait)
        except anthropic.AuthenticationError:
            raise RuntimeError("Authentication failed — check your ANTHROPIC_API_KEY.")
        except anthropic.APIConnectionError:
            raise RuntimeError("Could not reach the Anthropic API. Check your internet connection.")
        except anthropic.APIStatusError as e:
            raise RuntimeError(f"Anthropic API error {e.status_code}: {e.message}")

    raise RuntimeError("Exceeded maximum retries.")  # Should never reach here


# ---------------------------------------------------------------------------
# Main Fix Function
# ---------------------------------------------------------------------------

def fix_bug(broken_code: str, error_message: str,
            context: str = "", language_hint: str = "") -> dict:
    """
    Core function. Sends broken code + error to Claude, returns structured result.

    Returns dict with keys:
        fixed_code, explanation, metadata
            metadata: input_tokens, output_tokens, total_tokens,
                      estimated_cost_usd, language, model, timestamp
    """
    # Validate API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set.\n"
            "Set it with: set ANTHROPIC_API_KEY=sk-ant-your-key   (Windows)\n"
            "             export ANTHROPIC_API_KEY=sk-ant-your-key  (Mac/Linux)"
        )

    language = detect_language(broken_code, hint=language_hint)
    prompt   = build_prompt(broken_code, error_message, language, context)
    client   = anthropic.Anthropic(api_key=api_key)

    message  = call_with_retry(client, prompt)
    result   = parse_response(message.content[0].text)

    usage = message.usage
    result["metadata"] = {
        "model":               MODEL,
        "language":            language,
        "input_tokens":        int(usage.input_tokens),
        "output_tokens":       int(usage.output_tokens),
        "total_tokens":        int(usage.input_tokens + usage.output_tokens),
        "estimated_cost_usd":  calculate_cost(usage.input_tokens, usage.output_tokens, MODEL),
        "timestamp":           datetime.datetime.now().isoformat(),
    }

    return result


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Neo Bug Forge — AI-Powered Bug Fixer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bug_fixer.py                            # interactive mode
  python bug_fixer.py -c broken.py -e error.txt  # file mode
  python bug_fixer.py -c "x=1/0" -e "ZeroDivisionError" --language python
  python bug_fixer.py -c code.js -e err.txt -o result.json
        """
    )
    parser.add_argument("-c", "--code",     help="Path to code file OR code as a string")
    parser.add_argument("-e", "--error",    help="Path to error file OR error message as a string")
    parser.add_argument("-o", "--output",   help="Save full JSON result to this file")
    parser.add_argument("-l", "--language", help="Language hint: python, js, ts, rust, go, java, cpp, ruby")
    parser.add_argument("--context",        help="Extra context: filename, project info, etc.")
    parser.add_argument("--history",        action="store_true", help="Print last 10 fixes and exit")
    args = parser.parse_args()

    # -- Show history and exit
    if args.history:
        history = load_history()
        if not history:
            print("No fix history yet.")
        else:
            print(f"=== Last {len(history)} Fixes ===\n")
            for i, entry in enumerate(reversed(history), 1):
                status = "✅" if entry.get("success") else "❌"
                print(f"  {i}. {status} [{entry['timestamp'][:19]}]  "
                      f"{entry['language']:<12}  "
                      f"${entry['cost']:.5f}  "
                      f"{entry.get('error_snippet','')}")
        return

    print("=== Neo Bug Forge — AI Bug Fixer (Claude Sonnet 4) ===\n")

    # -- Resolve broken code
    if args.code and Path(args.code).exists():
        broken_code = Path(args.code).read_text(encoding="utf-8")
        print(f"📂 Loaded code from: {args.code}")
    elif args.code:
        broken_code = args.code
    else:
        print("Paste your broken code below. Type END on a new line when done:")
        lines = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        broken_code = "\n".join(lines)

    # -- Resolve error message
    if args.error and Path(args.error).exists():
        error_message = Path(args.error).read_text(encoding="utf-8").strip()
        print(f"📂 Loaded error from: {args.error}")
    elif args.error:
        error_message = args.error
    else:
        print("\nEnter the error message (type END when done):")
        lines = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)
        error_message = "\n".join(lines).strip()

    if not broken_code.strip() or not error_message.strip():
        print("❌ Error: both --code and --error are required.", file=sys.stderr)
        sys.exit(1)

    print("\n🔍 Analyzing bug and generating fix...\n")

    success = False
    try:
        result  = fix_bug(broken_code, error_message,
                          context=args.context or "",
                          language_hint=args.language or "")
        success = True

        # -- Display results
        meta = result["metadata"]
        print("✅ FIX SUCCESSFUL!\n")
        print("--- FIXED CODE ---")
        print(result["fixed_code"])
        print("\n--- EXPLANATION ---")
        print(result["explanation"])
        print(f"\n🌐 Language:  {meta['language']}")
        print(f"📊 Tokens:    {meta['total_tokens']:,}  "
              f"({meta['input_tokens']:,} in  /  {meta['output_tokens']:,} out)")
        print(f"💰 Cost:      ${meta['estimated_cost_usd']:.6f} USD")
        print(f"🤖 Model:     {meta['model']}")

        # -- Save to file if requested
        if args.output:
            Path(args.output).write_text(
                json.dumps(result, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            print(f"\n💾 Result saved to: {args.output}")

    except (EnvironmentError, RuntimeError, ValueError) as exc:
        print(f"\n❌ Error: {exc}", file=sys.stderr)

    finally:
        # -- Always save to history (success or failure)
        save_to_history({
            "timestamp":     datetime.datetime.now().isoformat(),
            "language":      detect_language(broken_code, hint=args.language or ""),
            "error_snippet": error_message[:80].replace("\n", " "),
            "success":       success,
            "cost":          result["metadata"]["estimated_cost_usd"] if success else 0.0,
        })


if __name__ == "__main__":
    main()
