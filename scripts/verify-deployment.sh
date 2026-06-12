#!/bin/bash
# scripts/verify-deployment.sh
# Run this after deploying to confirm everything is working correctly.
# Usage: ./scripts/verify-deployment.sh https://your-api.up.railway.app

set -e

API_URL=${1:-"http://localhost:8000"}
PASS=0
FAIL=0
WARN=0

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}  ✓ $1${NC}"; PASS=$((PASS+1)); }
fail() { echo -e "${RED}  ✗ $1${NC}"; FAIL=$((FAIL+1)); }
warn() { echo -e "${YELLOW}  ⚠ $1${NC}"; WARN=$((WARN+1)); }

echo ""
echo "Neo Bug Forge — Deployment Verification"
echo "Target: $API_URL"
echo "========================================"

# 1. Health check
echo ""
echo "[ 1/5 ] Health endpoint"
HEALTH=$(curl -s "$API_URL/health")
STATUS=$(echo $HEALTH | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null)
CONFIGURED=$(echo $HEALTH | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('anthropic_configured',''))" 2>/dev/null)

if [ "$STATUS" = "ok" ]; then
  pass "Server is up (status=ok)"
else
  fail "Server returned unexpected status: $STATUS"
fi

if [ "$CONFIGURED" = "True" ]; then
  pass "Anthropic API key is loaded"
else
  fail "Anthropic API key is NOT configured — fix env vars"
fi

# 2. Root endpoint
echo ""
echo "[ 2/5 ] API info endpoint"
ROOT=$(curl -s "$API_URL/")
if echo "$ROOT" | grep -q "Neo Bug Forge"; then
  pass "Root endpoint responding correctly"
else
  fail "Root endpoint returned unexpected response"
fi

# 3. Public fix endpoint
echo ""
echo "[ 3/5 ] Public fix endpoint (one real request)"
FIX_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/v1/fix/public" \
  -H "Content-Type: application/json" \
  -d '{"broken_code":"def f(x):\n    return x[10]","error_message":"IndexError: list index out of range","language":"python"}')

HTTP_CODE=$(echo "$FIX_RESPONSE" | tail -1)
BODY=$(echo "$FIX_RESPONSE" | head -1)

if [ "$HTTP_CODE" = "200" ]; then
  pass "Fix endpoint returned 200"
  FIX_ID=$(echo $BODY | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('fix_id',''))" 2>/dev/null)
  CONFIDENCE=$(echo $BODY | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('confidence',0))" 2>/dev/null)
  pass "Fix ID: $FIX_ID, Confidence: $CONFIDENCE%"
  if [ "$CONFIDENCE" -ge 70 ] 2>/dev/null; then
    pass "Confidence score is acceptable (≥70%)"
  else
    warn "Low confidence score: $CONFIDENCE%"
  fi
else
  fail "Fix endpoint returned $HTTP_CODE (expected 200)"
  echo "    Response: $BODY"
fi

# 4. Fix retrieval
echo ""
echo "[ 4/5 ] Fix retrieval endpoint"
if [ -n "$FIX_ID" ]; then
  RETRIEVE=$(curl -s -w "\n%{http_code}" "$API_URL/v1/fix/$FIX_ID")
  RCODE=$(echo "$RETRIEVE" | tail -1)
  if [ "$RCODE" = "200" ]; then
    pass "Fix retrieval working (GET /v1/fix/$FIX_ID → 200)"
  else
    fail "Fix retrieval returned $RCODE"
  fi
else
  warn "Skipping retrieval test (no fix_id from previous step)"
fi

# 5. Rate limiting
echo ""
echo "[ 5/5 ] Rate limiter (public endpoint) — sending 11 requests"
RATE_LIMIT_HIT=false
for i in $(seq 1 11); do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/v1/fix/public" \
    -H "Content-Type: application/json" \
    -d '{"broken_code":"x=1","error_message":"test"}')
  if [ "$CODE" = "429" ]; then
    RATE_LIMIT_HIT=true
    pass "Rate limit enforced at request $i (got 429)"
    break
  fi
done

if [ "$RATE_LIMIT_HIT" = false ]; then
  fail "Rate limiter NOT working — 11 requests all succeeded"
fi

# Summary
echo ""
echo "========================================"
echo -e "Results: ${GREEN}$PASS passed${NC}  ${RED}$FAIL failed${NC}  ${YELLOW}$WARN warnings${NC}"
echo ""

if [ $FAIL -gt 0 ]; then
  echo -e "${RED}✗ Deployment has issues — do not go live yet${NC}"
  exit 1
elif [ $WARN -gt 0 ]; then
  echo -e "${YELLOW}⚠ Deployment OK with warnings — review before going live${NC}"
  exit 0
else
  echo -e "${GREEN}✓ All checks passed — Neo Bug Forge is ready to ship!${NC}"
  exit 0
fi
