# Neo Bug Forge — VS Code Extension

**Instantly fix code bugs using AI.** Select broken code, press `Ctrl+Shift+F`, paste the error — done.

---

## Installation

1. Open **VS Code**
2. Go to the **Extensions** tab (`Ctrl+Shift+X`)
3. Search for **"Neo Bug Forge"**
4. Click **Install**

---

## Setup

1. Go to **[neobugforge.io](https://neobugforge.io)** and get your free API key (`nbf_...`)
2. Open VS Code Command Palette: `Ctrl+Shift+P`
3. Run: **Neo Bug Forge: Set API Key**
4. Paste your key — stored securely in VS Code's SecretStorage, never in plaintext

---

## Usage

### Method 1: Keyboard Shortcut (fastest)
1. Select broken code in any editor
2. Press `Ctrl+Shift+F` (Windows/Linux) or `Cmd+Shift+F` (Mac)
3. Enter the error message
4. Fix appears instantly

### Method 2: Right-click Menu
1. Select broken code
2. Right-click → **Neo Bug Forge: Fix Selected Code**
3. Enter error message → fix appears

### Method 3: Open Panel manually
1. Command Palette → **Neo Bug Forge: Open Panel**
2. Paste code and error message
3. Click **⚡ Fix My Bug**

---

## What you get back

Every fix includes:

| Field | Description |
|---|---|
| ✅ Fixed code | Clean, corrected version of your code |
| 🧠 Explanation | Plain-English description of what was wrong |
| 📊 Confidence score | How certain the AI is (0–100%) |
| 🏷 Root cause | Category of bug (null reference, type mismatch, etc.) |
| 🔀 Diff | Red/green unified diff showing exactly what changed |
| 🧪 Test case | Unit test that would have caught the bug |

---

## Supported Languages

Python · JavaScript · TypeScript · Java · Rust · Go · C++ · and more (auto-detect)

---

## Beta Offer 🎁

**First 50 reviewers get lifetime Pro free.**
Leave a review on the marketplace and email **hello@neobugforge.io** with your username to claim it.

---

## Pricing

Get your API key at **[neobugforge.io](https://neobugforge.io)**:

| Plan | Fixes/month | Price |
|---|---|---|
| Free | 100 | $0 |
| Pro | 500 | $12/mo |
| Team | Unlimited (fair use) | $49/user/mo |

---

## Security

- Your API key is stored in VS Code's **SecretStorage** — never written to disk in plaintext
- Your code is transmitted over HTTPS and never used to train AI models
- See our [Privacy Policy](https://neobugforge.io/privacy.html)

---

## Links

- 🌐 [neobugforge.io](https://neobugforge.io)
- 🐛 [Report an issue](https://github.com/networkhack52/neo-bug-forge/issues)
- 📧 [hello@neobugforge.io](mailto:hello@neobugforge.io)

---

## License

MIT © 2026 Neo Bug Forge
