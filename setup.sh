#!/bin/bash
# =============================================================================
# Neo Bug Forge — Master Setup Script
# Run this once after unzipping the project.
# Usage: chmod +x setup.sh && ./setup.sh
# =============================================================================

set -e  # Exit on any error

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

PASS=0
FAIL=0

pass() { echo -e "${GREEN}  ✓ $1${NC}"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}  ✗ $1${NC}"; FAIL=$((FAIL+1)); }
info() { echo -e "${BLUE}  → $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠ $1${NC}"; }
header() { echo -e "\n${BOLD}$1${NC}"; echo "$(printf '─%.0s' $(seq 1 50))"; }

clear
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║       Neo Bug Forge — Setup              ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}"
echo ""

# =============================================================================
# STEP 1 — Check prerequisites
# =============================================================================
header "Step 1 — Checking prerequisites"

# Python
if command -v python3 &>/dev/null; then
  PYVER=$(python3 --version 2>&1)
  pass "Python found: $PYVER"
else
  fail "Python 3 not found — install from python.org"
  exit 1
fi

# Node
if command -v node &>/dev/null; then
  NODEVER=$(node --version)
  pass "Node.js found: $NODEVER"
else
  fail "Node.js not found — install from nodejs.org"
  exit 1
fi

# npm
if command -v npm &>/dev/null; then
  NPMVER=$(npm --version)
  pass "npm found: v$NPMVER"
else
  fail "npm not found"
  exit 1
fi

# curl (for verification)
if command -v curl &>/dev/null; then
  pass "curl found"
else
  warn "curl not found — deployment verification will be skipped"
fi

# openssl
if command -v openssl &>/dev/null; then
  pass "openssl found"
else
  warn "openssl not found — generate API_SECRET_KEY manually"
fi

# =============================================================================
# STEP 2 — Environment variables
# =============================================================================
header "Step 2 — Environment setup"

if [ ! -f ".env" ]; then
  cp .env.example .env
  info "Created .env from .env.example"

  # Auto-generate API_SECRET_KEY
  if command -v openssl &>/dev/null; then
    SECRET=$(openssl rand -hex 32)
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "s/your-32-char-random-secret-here/$SECRET/" .env
    else
      sed -i "s/your-32-char-random-secret-here/$SECRET/" .env
    fi
    pass "API_SECRET_KEY auto-generated"
  fi

  echo ""
  warn "ACTION REQUIRED: Open .env and set your ANTHROPIC_API_KEY"
  warn "Get your key at: https://console.anthropic.com"
  echo ""
  read -p "  Press Enter once you've added your API key to .env..."

else
  pass ".env already exists — skipping"
fi

# Validate API key is set
source .env 2>/dev/null || true
if [[ "$ANTHROPIC_API_KEY" == "sk-ant-"* ]]; then
  pass "ANTHROPIC_API_KEY looks valid (starts with sk-ant-)"
elif [ -z "$ANTHROPIC_API_KEY" ] || [[ "$ANTHROPIC_API_KEY" == *"your-key"* ]]; then
  fail "ANTHROPIC_API_KEY not set in .env — add it before running the API"
else
  warn "ANTHROPIC_API_KEY set but format looks unusual — double check"
fi

# =============================================================================
# STEP 3 — Python / API setup
# =============================================================================
header "Step 3 — Python API dependencies"

cd api

# Create virtualenv
if [ ! -d "venv" ]; then
  info "Creating Python virtual environment..."
  python3 -m venv venv
  pass "Virtual environment created"
else
  pass "Virtual environment already exists"
fi

# Activate and install
source venv/bin/activate
info "Installing Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pass "Python dependencies installed"

# Quick import test
python3 -c "import fastapi, anthropic, slowapi; print('  All imports OK')" && pass "All Python imports verified" || fail "Import error — check requirements.txt"

deactivate
cd ..

# =============================================================================
# STEP 4 — React web app setup
# =============================================================================
header "Step 4 — React web app dependencies"

cd web
info "Installing Node dependencies..."
npm install --silent
pass "Node dependencies installed ($(ls node_modules | wc -l | tr -d ' ') packages)"

info "Building web app..."
npm run build --silent
pass "Production build complete → web/dist/"
cd ..

# =============================================================================
# STEP 5 — VS Code extension setup
# =============================================================================
header "Step 5 — VS Code extension dependencies"

cd vscode-extension
info "Installing extension dependencies..."
npm install --silent
pass "Extension dependencies installed"

info "Compiling TypeScript..."
npx tsc -p tsconfig.json --noEmit 2>/dev/null && pass "TypeScript compiled without errors" || warn "TypeScript warnings detected — check src/ files"

cd ..

# =============================================================================
# STEP 6 — Local smoke test
# =============================================================================
header "Step 6 — Local smoke test"

info "Starting API server in background..."
cd api
source venv/bin/activate
uvicorn api:app --host 0.0.0.0 --port 8000 &
API_PID=$!
cd ..

sleep 3  # Wait for server to start

if curl -s http://localhost:8000/health | grep -q '"status":"ok"'; then
  pass "API health check passed"
else
  warn "API health check failed — server may still be starting"
fi

# Stop the test server
kill $API_PID 2>/dev/null || true
wait $API_PID 2>/dev/null || true

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║              Setup Complete              ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${GREEN}$PASS checks passed${NC}   ${RED}$FAIL failed${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
  echo -e "${GREEN}${BOLD}  Everything is ready. Next steps:${NC}"
else
  echo -e "${RED}${BOLD}  Fix the failures above, then run setup.sh again.${NC}"
  echo ""
fi

echo ""
echo -e "${BOLD}  Run locally:${NC}"
echo "  ┌─ API:  cd api && source venv/bin/activate && uvicorn api:app --reload"
echo "  └─ Web:  cd web && npm run dev"
echo ""
echo -e "${BOLD}  Deploy:${NC}"
echo "  ┌─ API:  cd api && railway up"
echo "  ├─ Web:  cd web && vercel --prod"
echo "  └─ Ext:  cd vscode-extension && npm run package && vsce publish"
echo ""
echo -e "${BOLD}  Verify deployment:${NC}"
echo "  └─ bash scripts/verify-deployment.sh https://your-api.up.railway.app"
echo ""
echo -e "${BOLD}  Estimate costs:${NC}"
echo "  └─ python scripts/estimate_costs.py --fixes 10000 --model sonnet"
echo ""
