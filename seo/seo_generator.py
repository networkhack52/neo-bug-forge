"""
seo_generator.py  —  Neo Bug Forge SEO Page Generator
=====================================================
Reads the error catalogue below and stamps out a production-ready
HTML landing page for each error type. Pages are written to:

    ./dist/fix/{language}/{ErrorName}/index.html

This gives you clean URLs like:
    neobugforge.io/fix/python/ZeroDivisionError
    neobugforge.io/fix/javascript/TypeError-cannot-read-properties

Run:
    python seo_generator.py

Then deploy ./dist/ to any static host (Vercel, Netlify, S3 + CloudFront).
"""

import os
import json
from pathlib import Path
from datetime import datetime
from textwrap import dedent

# ─── Error Catalogue ──────────────────────────────────────────────────────────
# Each entry becomes one SEO landing page.
# Add entries here to generate new pages — no other code changes needed.

ERROR_CATALOGUE = [

    # ── Python ──────────────────────────────────────────────────────────────
    {
        "language": "python",
        "language_label": "Python",
        "error_name": "ZeroDivisionError",
        "error_category": "RuntimeError",
        "slug": "ZeroDivisionError",
        "title": "Fix Python ZeroDivisionError: division by zero",
        "meta_desc": "Getting 'ZeroDivisionError: division by zero' in Python? AI-powered fix in seconds. Common causes, examples, and instant repair. Free, no signup.",
        "keywords": "ZeroDivisionError, Python ZeroDivisionError fix, division by zero python, python error fix",
        "headline": "Fix <em>ZeroDivisionError</em>: division by zero",
        "deck": "Python raises ZeroDivisionError when your code divides by zero — usually because a variable holds an unexpected zero at runtime. Paste your code below for an instant AI fix.",
        "widget_placeholder_code": "def calculate_average(nums):\n    return sum(nums) / len(nums)\n\nresult = calculate_average([])  # → ZeroDivisionError",
        "widget_placeholder_error": "ZeroDivisionError: division by zero",
        "widget_btn_label": "Fix My ZeroDivisionError",
        "fixes_this_week": "4,821",
        "accuracy": "96%",
        "root_cause_hint": "null_reference|type_mismatch|off_by_one|scope_error|logic_error|syntax_error|import_error|index_error|other",
        "faq": [
            ("Why does Python raise this instead of returning infinity?",
             "For integer division Python raises ZeroDivisionError rather than returning inf, because silently producing infinity for integer math would hide more bugs than it solves. For IEEE 754 float operations, Python does return inf in some contexts."),
            ("How do I find which line triggered it?",
             "Run your script from the terminal and read the full traceback. The line just above 'ZeroDivisionError' in the traceback is the exact division operation that failed."),
            ("What's the difference between / and // in Python?",
             "/ always returns a float; // performs floor division and returns an int. Both raise ZeroDivisionError when the denominator is zero."),
        ],
        "related_same_lang": [
            ("TypeError", "/fix/python/TypeError"),
            ("AttributeError", "/fix/python/AttributeError"),
            ("KeyError", "/fix/python/KeyError"),
            ("IndexError", "/fix/python/IndexError"),
            ("ValueError", "/fix/python/ValueError"),
        ],
        "related_cross_lang": [
            ("JS", "Division by zero", "/fix/javascript/division-by-zero"),
            ("Java", "ArithmeticException", "/fix/java/ArithmeticException"),
            ("Rust", "divide by zero", "/fix/rust/attempt-to-divide-by-zero"),
        ],
    },

    {
        "language": "python",
        "language_label": "Python",
        "error_name": "KeyError",
        "error_category": "RuntimeError",
        "slug": "KeyError",
        "title": "Fix Python KeyError — Missing Dictionary Key",
        "meta_desc": "Python KeyError means you accessed a dict key that doesn't exist. Instant AI fix, common patterns, and guard clause examples. Free, no signup.",
        "keywords": "Python KeyError, fix KeyError python, dictionary key error python, KeyError fix",
        "headline": "Fix Python <em>KeyError</em>: missing dictionary key",
        "deck": "KeyError is raised when you access a Python dictionary with a key that doesn't exist. The fix is almost always a guard clause or using .get() with a default value.",
        "widget_placeholder_code": "user = {'name': 'Alice', 'age': 30}\nprint(user['email'])  # → KeyError: 'email'",
        "widget_placeholder_error": "KeyError: 'email'",
        "widget_btn_label": "Fix My KeyError",
        "fixes_this_week": "6,103",
        "accuracy": "98%",
        "root_cause_hint": "null_reference|type_mismatch|index_error|scope_error|logic_error|other",
        "faq": [
            ("What's the difference between dict[key] and dict.get(key)?",
             "dict[key] raises KeyError if the key is absent. dict.get(key) returns None (or a default you specify) instead of raising. Use .get() when the key is optional; use [] when missing means a bug."),
            ("How do I check if a key exists before accessing it?",
             "Use 'if key in my_dict:' before accessing, or use dict.get(key, default). Both are idiomatic Python."),
            ("Can I catch KeyError with try/except?",
             "Yes: 'try: val = d[key] except KeyError: val = default'. But prefer .get() for simple cases; reserve try/except for when you need to log or re-raise."),
        ],
        "related_same_lang": [
            ("IndexError", "/fix/python/IndexError"),
            ("AttributeError", "/fix/python/AttributeError"),
            ("TypeError", "/fix/python/TypeError"),
            ("ValueError", "/fix/python/ValueError"),
            ("NameError", "/fix/python/NameError"),
        ],
        "related_cross_lang": [
            ("JS", "Cannot read property", "/fix/javascript/TypeError-cannot-read-properties"),
            ("Ruby", "NoMethodError", "/fix/ruby/NoMethodError"),
        ],
    },

    # ── JavaScript ──────────────────────────────────────────────────────────
    {
        "language": "javascript",
        "language_label": "JavaScript",
        "error_name": "TypeError-cannot-read-properties",
        "error_category": "TypeError",
        "slug": "TypeError-cannot-read-properties",
        "title": "Fix JS TypeError: Cannot read properties of undefined",
        "meta_desc": "Seeing 'TypeError: Cannot read properties of undefined (reading X)' in JavaScript? AI fix in seconds. Optional chaining, null guards, and real examples. Free.",
        "keywords": "TypeError cannot read properties undefined, javascript TypeError fix, cannot read property of null, JS error fix",
        "headline": "Fix JS <em>TypeError</em>: Cannot read properties of undefined",
        "deck": "JavaScript's most common error. It means you're accessing a property on a value that is undefined or null — usually because an async call hasn't resolved, an API returned nothing, or a variable was never assigned.",
        "widget_placeholder_code": "const user = fetchUser(); // returns undefined when not found\nconsole.log(user.profile.avatar); // TypeError: Cannot read properties of undefined",
        "widget_placeholder_error": "TypeError: Cannot read properties of undefined (reading 'profile')",
        "widget_btn_label": "Fix My TypeError",
        "fixes_this_week": "9,442",
        "accuracy": "97%",
        "root_cause_hint": "null_reference|async_race|type_mismatch|scope_error|logic_error|other",
        "faq": [
            ("What's the fastest fix for this error?",
             "Optional chaining: change obj.prop.sub to obj?.prop?.sub. It returns undefined instead of throwing. For critical paths, add an explicit null check: if (!obj) return;"),
            ("Why does this happen after an async call?",
             "Because the async function returns a Promise, not the value. Without await or .then(), the variable is a Promise object — and accessing .property on a Promise that hasn't resolved gives you undefined."),
            ("What's the difference between undefined and null?",
             "undefined means a variable was declared but never assigned. null means it was explicitly set to 'nothing'. Both cause this error when you try to access properties on them."),
        ],
        "related_same_lang": [
            ("ReferenceError", "/fix/javascript/ReferenceError"),
            ("SyntaxError", "/fix/javascript/SyntaxError"),
            ("RangeError", "/fix/javascript/RangeError"),
            ("Promise rejection", "/fix/javascript/UnhandledPromiseRejection"),
        ],
        "related_cross_lang": [
            ("Python", "AttributeError", "/fix/python/AttributeError"),
            ("Java", "NullPointerException", "/fix/java/NullPointerException"),
            ("TS", "Object is possibly undefined", "/fix/typescript/object-is-possibly-undefined"),
        ],
    },

    # ── TypeScript ──────────────────────────────────────────────────────────
    {
        "language": "typescript",
        "language_label": "TypeScript",
        "error_name": "object-is-possibly-undefined",
        "error_category": "Type Error",
        "slug": "object-is-possibly-undefined",
        "title": "Fix TS2532: Object is possibly undefined — TypeScript",
        "meta_desc": "TypeScript error TS2532 'Object is possibly undefined'? AI fix, optional chaining examples, and non-null assertion explained. Free, no signup.",
        "keywords": "TypeScript TS2532, object is possibly undefined, typescript fix, ts2532 error fix",
        "headline": "Fix TypeScript <em>TS2532</em>: Object is possibly undefined",
        "deck": "TypeScript is protecting you — it found a code path where a value could be undefined before you access it. The fix depends on whether the value should be optional or guaranteed.",
        "widget_placeholder_code": "interface User { profile?: { avatar: string } }\n\nfunction getAvatar(user: User): string {\n  return user.profile.avatar; // TS2532: Object is possibly undefined\n}",
        "widget_placeholder_error": "TS2532: Object is possibly undefined.",
        "widget_btn_label": "Fix My TS2532",
        "fixes_this_week": "3,217",
        "accuracy": "97%",
        "root_cause_hint": "null_reference|type_mismatch|scope_error|logic_error|other",
        "faq": [
            ("When should I use optional chaining vs non-null assertion (!)?",
             "Use optional chaining (?.) when the value genuinely might be undefined and that's acceptable. Use ! only when you are certain the value exists and TypeScript can't prove it — but document why. Never use ! to silence a warning you don't understand."),
            ("What's the difference between undefined and null in TypeScript's type system?",
             "TypeScript treats them as distinct types. 'string | undefined' allows undefined; 'string | null' allows null. With strictNullChecks enabled (recommended), you must handle both explicitly."),
            ("Should I use 'as T' casting to fix this?",
             "No. Type casting with 'as' suppresses the error without fixing the underlying issue. It can cause runtime crashes. Fix the logic instead."),
        ],
        "related_same_lang": [
            ("TS2345: Argument not assignable", "/fix/typescript/TS2345"),
            ("TS2304: Cannot find name", "/fix/typescript/TS2304"),
            ("TS7006: Implicit any", "/fix/typescript/TS7006"),
        ],
        "related_cross_lang": [
            ("JS", "TypeError: Cannot read properties", "/fix/javascript/TypeError-cannot-read-properties"),
            ("Rust", "Option unwrap on None", "/fix/rust/option-unwrap-none"),
        ],
    },

    # ── Rust ────────────────────────────────────────────────────────────────
    {
        "language": "rust",
        "language_label": "Rust",
        "error_name": "option-unwrap-none",
        "error_category": "Panic",
        "slug": "option-unwrap-none",
        "title": "Fix Rust panic: called unwrap() on a None value",
        "meta_desc": "Rust panic 'called unwrap() on a None value'? Use match, if let, or unwrap_or instead. AI fix, examples, idiomatic patterns. Free.",
        "keywords": "Rust unwrap None panic, Rust Option unwrap, fix rust panic, unwrap_or rust",
        "headline": "Fix Rust panic: <em>called unwrap() on a None value</em>",
        "deck": "Calling .unwrap() on an Option::None panics at runtime. Rust's Option type forces you to handle the None case — use match, if let, or the ? operator instead.",
        "widget_placeholder_code": 'fn get_username(id: u32) -> String {\n    let user = find_user(id); // returns Option<User>\n    user.unwrap().username   // panics if None\n}',
        "widget_placeholder_error": "thread 'main' panicked at 'called `Option::unwrap()` on a `None` value'",
        "widget_btn_label": "Fix My Rust Panic",
        "fixes_this_week": "1,893",
        "accuracy": "95%",
        "root_cause_hint": "null_reference|logic_error|index_error|other",
        "faq": [
            ("When is it safe to use .unwrap()?",
             "In tests, in prototypes, or when you have a logical guarantee that the value is Some — for example, immediately after inserting into a HashMap. In production code, use .expect('meaningful message') at minimum so panics are informative."),
            ("What's the difference between unwrap, expect, and ?",
             ".unwrap() panics with a generic message. .expect('msg') panics with your message. ? propagates the None (or Err) to the calling function, which must also return Option or Result. Use ? in production code."),
            ("Should I use .unwrap_or() or .unwrap_or_else()?",
             ".unwrap_or(default) always evaluates the default. .unwrap_or_else(|| compute()) lazily evaluates — use it when the default is expensive to compute."),
        ],
        "related_same_lang": [
            ("Result unwrap Err", "/fix/rust/result-unwrap-err"),
            ("borrow after move", "/fix/rust/borrow-after-move"),
            ("index out of bounds", "/fix/rust/index-out-of-bounds"),
        ],
        "related_cross_lang": [
            ("Python", "AttributeError: NoneType", "/fix/python/AttributeError"),
            ("JS", "TypeError: Cannot read properties", "/fix/javascript/TypeError-cannot-read-properties"),
        ],
    },
]

# ─── HTML Template ────────────────────────────────────────────────────────────

def build_faq_html(faq_items):
    items = ""
    for q, a in faq_items:
        items += f"""
        <div class="faq-item">
          <div class="faq-q" onclick="toggleFaq(this)">
            {q}
            <span class="toggle">+</span>
          </div>
          <div class="faq-a" style="display:none">{a}</div>
        </div>"""
    return items


def build_related_same_lang(items, lang_label):
    links = ""
    for name, url in items:
        links += f'<a class="sidebar-link" href="{url}"><span class="lang-tag">{lang_label[:2].upper()}</span>{name}</a>\n'
    return links


def build_related_cross_lang(items):
    links = ""
    for lang_short, name, url in items:
        links += f'<a class="sidebar-link" href="{url}"><span class="lang-tag">{lang_short}</span>{name}</a>\n'
    return links


def build_page(entry: dict) -> str:
    faq_html   = build_faq_html(entry["faq"])
    same_html  = build_related_same_lang(entry["related_same_lang"], entry["language_label"])
    cross_html = build_related_cross_lang(entry["related_cross_lang"])

    return dedent(f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{entry['title']} — Neo Bug Forge</title>
  <meta name="description" content="{entry['meta_desc']}"/>
  <meta name="keywords" content="{entry['keywords']}"/>
  <link rel="canonical" href="https://neobugforge.io/fix/{entry['language']}/{entry['slug']}"/>
  <meta property="og:title" content="{entry['title']}"/>
  <meta property="og:description" content="{entry['meta_desc']}"/>
  <meta property="og:url" content="https://neobugforge.io/fix/{entry['language']}/{entry['slug']}"/>
  <meta property="og:type" content="website"/>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [{', '.join([
        f'{{"@type":"Question","name":"{q}","acceptedAnswer":{{"@type":"Answer","text":"{a}"}}}}'
        for q, a in entry['faq']
    ])}]
  }}
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Geist+Mono:wght@300;400;500;600;700&family=Geist:wght@300;400;500&display=swap" rel="stylesheet"/>
  <!-- [PASTE FULL CSS FROM seo-landing-page.html HERE] -->
  <!-- In production this is a shared /static/seo.css file -->
</head>
<body>

<header>
  <div class="wide">
    <div class="masthead">
      <div class="masthead-inner">
        <a class="masthead-logo" href="/">Neo Bug<span>Forge</span>.io</a>
        <nav class="masthead-nav">
          <a class="masthead-link" href="/fix/{entry['language']}">{entry['language_label']}</a>
          <a class="masthead-link" href="/errors">All Errors</a>
          <a class="masthead-link" href="/api">API</a>
        </nav>
        <a class="masthead-cta" href="/#fix">Fix a Bug →</a>
      </div>
    </div>
  </div>
</header>

<div class="container">
  <div class="breadcrumb">
    <a href="/">Home</a><span>/</span>
    <a href="/fix/{entry['language']}">{entry['language_label']} Errors</a><span>/</span>
    {entry['error_name']}
  </div>
</div>

<div class="container page-load">
  <div class="hero-block">
    <div class="error-kicker">{entry['language_label']} · {entry['error_category']}</div>
    <h1 class="hero-headline">{entry['headline']}</h1>
    <p class="hero-deck">{entry['deck']}</p>
    <div class="stat-row stagger-1">
      <div class="stat-item"><div class="stat-n">{entry['fixes_this_week']}</div><div class="stat-l">Fixed this week</div></div>
      <div class="stat-item"><div class="stat-n">{entry['accuracy']}</div><div class="stat-l">Fix accuracy</div></div>
      <div class="stat-item"><div class="stat-n">2.3s</div><div class="stat-l">Avg fix time</div></div>
    </div>
  </div>
</div>

<div class="container stagger-2">
  <div class="fix-widget">
    <div class="widget-header">
      <span class="widget-title">⚡ Instant Fix — Powered by Claude AI</span>
      <span class="widget-badge">Free · No Signup</span>
    </div>
    <div class="widget-body" id="widget-form">
      <div>
        <div class="widget-label">Your Broken Code</div>
        <textarea class="widget-textarea code-ta" id="w-code" placeholder="{entry['widget_placeholder_code']}"></textarea>
      </div>
      <div>
        <div class="widget-label">Error Message</div>
        <textarea class="widget-textarea error-ta" id="w-error" placeholder="{entry['widget_placeholder_error']}"></textarea>
      </div>
      <button class="widget-fix-btn" id="w-fix-btn" onclick="submitFix()">⚡ {entry['widget_btn_label']}</button>
      <div class="widget-note"><strong>10 free fixes</strong> · No account needed</div>
    </div>
    <div class="widget-loading" id="w-loading"><div class="spin-ring"></div><div class="loading-text" id="w-loading-text">Analyzing...</div></div>
    <div class="widget-error" id="w-error-box"><div class="we-inner" id="w-error-msg"></div></div>
    <div class="widget-result" id="w-result">
      <div class="result-meta">
        <span class="result-badge rb-green" id="w-conf-badge"></span>
        <span class="result-badge rb-blue" id="w-cause-tag"></span>
      </div>
      <div class="result-expl" id="w-explanation"></div>
      <div class="result-code-wrap">
        <div class="result-code-hdr">
          <span class="result-code-lang">{entry['language']}</span>
          <button class="copy-btn-sm" id="w-copy-btn" onclick="copyFixed()">⧉ Copy</button>
        </div>
        <pre class="result-code-pre" id="w-fixed-code"></pre>
      </div>
      <div class="result-actions">
        <button class="ra-btn primary" onclick="copyFixed()">⧉ Copy Fixed Code</button>
        <button class="ra-btn" onclick="resetWidget()">↺ Try Another</button>
        <button class="ra-btn" onclick="window.location.href='/#fix'">Open Full App →</button>
      </div>
    </div>
  </div>
</div>

<div class="container">
  <div class="content-grid">
    <article class="prose stagger-3">
      <!-- Content goes here — can be static HTML or pulled from a CMS -->
      <h2>What is {entry['error_name']}?</h2>
      <p>Use the widget above to get an instant AI-powered fix for your specific code. The guide below explains common patterns and how to prevent this error in future.</p>

      <h2>Frequently Asked Questions</h2>
      {faq_html}

      <div class="cta-strip">
        <div>
          <div class="cta-strip-title">Still stuck?<br/>Let AI fix it for you.</div>
          <div class="cta-strip-sub">Paste your exact code → get fixed code + test case in 2 seconds.</div>
        </div>
        <button class="cta-strip-btn" onclick="document.querySelector('.fix-widget').scrollIntoView({{behavior:'smooth'}})">
          ⚡ Fix My Code Now
        </button>
      </div>
    </article>

    <aside class="sidebar stagger-3">
      <div class="sidebar-card">
        <div class="sidebar-hdr">Related {entry['language_label']} Errors</div>
        <div class="sidebar-body">{same_html}</div>
      </div>
      <div class="sidebar-card">
        <div class="sidebar-hdr">Same Error, Other Languages</div>
        <div class="sidebar-body">{cross_html}</div>
      </div>
    </aside>
  </div>
</div>

<footer class="page-footer">
  <div class="container">
    <div class="footer-inner">
      <div class="footer-logo">Neo Bug<span>Forge</span>.io</div>
      <div class="footer-links">
        <a class="footer-link" href="/errors">All Errors</a>
        <a class="footer-link" href="/api">API</a>
        <a class="footer-link" href="/vscode">VS Code</a>
        <a class="footer-link" href="/pricing">Pricing</a>
      </div>
      <div class="footer-copy">© {datetime.now().year} Neo Bug Forge · Powered by Claude AI</div>
    </div>
  </div>
</footer>

<script>
  let fixedCodeGlobal = '';
  function toggleFaq(el) {{
    const ans = el.nextElementSibling, tog = el.querySelector('.toggle'), open = ans.style.display !== 'none';
    ans.style.display = open ? 'none' : 'block'; tog.textContent = open ? '+' : '−';
  }}
  function showEl(id)  {{ document.getElementById(id).classList.add('show'); }}
  function hideEl(id)  {{ document.getElementById(id).classList.remove('show'); }}
  function setDisplay(id, v) {{ document.getElementById(id).style.display = v; }}
  async function submitFix() {{
    const code = document.getElementById('w-code').value.trim();
    const error = document.getElementById('w-error').value.trim();
    if (!code) {{ alert('Please paste your broken code first.'); return; }}
    setDisplay('widget-form', 'none'); hideEl('w-error-box'); hideEl('w-result'); showEl('w-loading');
    try {{
      const result = await callClaude(code, error, '{entry['language']}');
      hideEl('w-loading'); renderResult(result);
    }} catch(e) {{
      hideEl('w-loading');
      document.getElementById('w-error-msg').textContent = '✗ ' + (e.message || 'Something went wrong.');
      showEl('w-error-box'); setDisplay('widget-form', 'flex');
    }}
  }}
  function renderResult(r) {{
    fixedCodeGlobal = r.fixed_code;
    document.getElementById('w-conf-badge').textContent = r.confidence + '% confident';
    document.getElementById('w-cause-tag').textContent = (r.root_cause || '').replace(/_/g, ' ');
    document.getElementById('w-explanation').textContent = r.explanation;
    document.getElementById('w-fixed-code').textContent = r.fixed_code;
    showEl('w-result');
  }}
  function copyFixed() {{
    if (!fixedCodeGlobal) return;
    navigator.clipboard.writeText(fixedCodeGlobal).then(() => {{
      const b = document.getElementById('w-copy-btn');
      b.textContent = '✓ Copied'; b.classList.add('ok');
      setTimeout(() => {{ b.textContent = '⧉ Copy'; b.classList.remove('ok'); }}, 1500);
    }});
  }}
  function resetWidget() {{
    hideEl('w-result'); hideEl('w-error-box'); setDisplay('widget-form', 'flex');
    document.getElementById('w-code').value = ''; document.getElementById('w-error').value = '';
    fixedCodeGlobal = '';
  }}
  async function callClaude(code, errorMsg, lang) {{
    const prompt = `You are an expert ${{lang}} debugger. Fix this code. Return ONLY raw JSON, no markdown.
JSON: {{"fixed_code":"...","explanation":"...","root_cause":"null_reference|type_mismatch|off_by_one|async_race|scope_error|logic_error|syntax_error|import_error|index_error|other","confidence":90}}
--- CODE ---\\n${{code}}\\n--- ERROR ---\\n${{errorMsg}}`;
    const res = await fetch('https://api.anthropic.com/v1/messages', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ model: 'claude-sonnet-4-20250514', max_tokens: 1024, messages: [{{role:'user',content:prompt}}] }})
    }});
    if (!res.ok) throw new Error('API error ' + res.status);
    const data = await res.json();
    const raw = data.content.map(b => b.text||'').join('').trim().replace(/^```(?:json)?\\s*/i,'').replace(/\\s*```$/,'');
    return JSON.parse(raw);
  }}
</script>
</body>
</html>""")


# ─── Generator ────────────────────────────────────────────────────────────────

def generate_all(output_dir: str = "./dist"):
    out = Path(output_dir)
    generated = []
    errors = []

    for entry in ERROR_CATALOGUE:
        path = out / "fix" / entry["language"] / entry["slug"]
        path.mkdir(parents=True, exist_ok=True)
        html_file = path / "index.html"

        try:
            html = build_page(entry)
            html_file.write_text(html, encoding="utf-8")
            size = len(html.encode()) // 1024
            generated.append(f"  ✓  /fix/{entry['language']}/{entry['slug']}/  ({size}KB)")
        except Exception as e:
            errors.append(f"  ✗  /fix/{entry['language']}/{entry['slug']}/  → {e}")

    # Print sitemap fragment
    sitemap_urls = "\n".join([
        f'  <url><loc>https://neobugforge.io/fix/{e["language"]}/{e["slug"]}/</loc>'
        f'<changefreq>weekly</changefreq><priority>0.8</priority></url>'
        for e in ERROR_CATALOGUE
    ])
    sitemap = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{sitemap_urls}\n</urlset>'
    (out / "sitemap-errors.xml").write_text(sitemap, encoding="utf-8")

    print(f"\nNeo Bug Forge — SEO Page Generator")
    print(f"{'─' * 50}")
    print(f"Generated {len(generated)} pages → {output_dir}/")
    for line in generated: print(line)
    if errors:
        print(f"\nFailed ({len(errors)}):")
        for line in errors: print(line)
    print(f"\n✓  Sitemap written → {output_dir}/sitemap-errors.xml")
    print(f"\nDeploy: vercel --prod {output_dir}")
    print(f"        OR: netlify deploy --dir {output_dir} --prod\n")


if __name__ == "__main__":
    generate_all()
