# Changelog

## [1.3.3] — 2026-06-22

### Added
- **Review prompt** — after your 3rd fix (and again at 10th and 25th), a notification asks if you'd like to leave a review on the VS Code Marketplace. Selecting "Don't Ask Again" suppresses it permanently.

## [1.3.0] — 2026-06-22

### Added
- **Deeper Context** — automatically scans the workspace for related files (open editors, same folder, symbol references) and includes them with the fix request so Claude has full context
- Context badge shows how many files were included (e.g. "📎 3 context files included")
- "🔍 Scanning workspace..." loading state while context is collected
- New settings: `neo-bug-forge.context.enabled` (on/off) and `neo-bug-forge.context.maxFiles` (1–10)

## [1.2.0] — 2026-06-22 (re-released as 1.3.0)

### Added
- Context collector service (`contextCollector.ts`) with 1.5s timeout and safe fallback

## [1.1.0] — 2026-06-22

### Added
- **Apply with Diff Preview** — opens VS Code's native side-by-side diff editor before applying a fix
- **Try Again** — retry the fix with an optional note explaining what was still wrong
- **Git Stage** — optionally stage the fixed file immediately after applying ("✓ Apply + Git Stage")
- Typewriter animation on the explanation text for a streaming feel
- Fix context (file URI + selection) is now tracked for accurate diff preview

## [1.0.0] — 2026-06-06

### Added
- AI-powered bug fixing via Claude (claude-sonnet-4-20250514)
- Right-click → "Neo Bug Forge: Fix Selected Code" context menu
- Cmd+Shift+F / Ctrl+Shift+F keyboard shortcut
- Side panel with dark terminal UI
- Fixed code, unified diff, test case, and confidence score
- "Apply to Editor" — patches file in place with one click
- Shareable fix links
- Secure API key storage via VS Code SecretStorage
- Language detection badges: Python, JS, TS, Rust, Go, Java, C++, Ruby, PHP
