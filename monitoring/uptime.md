# monitoring/uptime.md — Neo Bug Forge Uptime Monitoring

## Better Uptime Setup (free tier)

### Monitor 1 — API Health
- URL:           https://your-api.up.railway.app/health
- Method:        GET
- Check every:   3 minutes
- Alert if:      non-200 for 2 consecutive checks
- Expected body: {"status":"ok","anthropic_configured":true}
- Alert via:     Slack + email

### Monitor 2 — Web App
- URL:           https://neobugforge.io
- Method:        GET
- Check every:   5 minutes
- Alert if:      non-200 for 2 consecutive checks

### Monitor 3 — Public Fix Endpoint (smoke test)
- URL:           https://your-api.up.railway.app/v1/fix/public
- Method:        POST
- Body:          {"broken_code":"x=1/0","error_message":"ZeroDivisionError","language":"python"}
- Check every:   15 minutes
- Expected:      200 with fix_id in response

## Spend Alerts (Anthropic Console)
- Soft limit:  $30/month → email alert
- Hard limit:  $50/month → API stops accepting requests

## Railway Alerts
- CPU > 80% for 5 min → email
- Memory > 80%        → email
- Deploy failed        → Slack

## Weekly Review Checklist
- [ ] Check Railway logs for error spikes
- [ ] Review avg confidence scores (target > 85%)
- [ ] Check avg response time (target < 3s)
- [ ] Review Anthropic spend vs budget
- [ ] Check rate limit hit rate (signals abuse or viral moment)
