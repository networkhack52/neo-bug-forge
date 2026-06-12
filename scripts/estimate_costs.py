#!/usr/bin/env python3
"""
scripts/estimate_costs.py
Estimates monthly Anthropic API costs based on usage volume.

Usage:
  python scripts/estimate_costs.py
  python scripts/estimate_costs.py --fixes 50000 --model sonnet
"""

import argparse

# Anthropic pricing (per million tokens) — update if pricing changes
# https://www.anthropic.com/pricing
PRICING = {
    "sonnet": { "input": 3.00,  "output": 15.00, "name": "claude-sonnet-4" },
    "haiku":  { "input": 0.80,  "output": 4.00,  "name": "claude-haiku-4"  },
    "opus":   { "input": 15.00, "output": 75.00, "name": "claude-opus-4"   },
}

# Average tokens per fix request (measured from QA runs)
AVG_INPUT_TOKENS  = 820   # prompt + code + error message
AVG_OUTPUT_TOKENS = 480   # fixed code + explanation + diff + test case

def estimate(monthly_fixes: int, model: str = "sonnet") -> None:
    p = PRICING[model]

    input_tokens  = monthly_fixes * AVG_INPUT_TOKENS
    output_tokens = monthly_fixes * AVG_OUTPUT_TOKENS

    input_cost  = (input_tokens  / 1_000_000) * p["input"]
    output_cost = (output_tokens / 1_000_000) * p["output"]
    total_cost  = input_cost + output_cost
    cost_per_fix = total_cost / monthly_fixes if monthly_fixes else 0

    print(f"\nNeo Bug Forge — Cost Estimator")
    print(f"{'─' * 42}")
    print(f"  Model:          {p['name']}")
    print(f"  Monthly fixes:  {monthly_fixes:,}")
    print(f"  Avg tokens in:  {AVG_INPUT_TOKENS:,} / fix")
    print(f"  Avg tokens out: {AVG_OUTPUT_TOKENS:,} / fix")
    print(f"{'─' * 42}")
    print(f"  Input cost:     ${input_cost:,.2f}")
    print(f"  Output cost:    ${output_cost:,.2f}")
    print(f"  Total/month:    ${total_cost:,.2f}")
    print(f"  Cost per fix:   ${cost_per_fix:.4f}")
    print(f"{'─' * 42}")

    # Break-even analysis at $9/month per user
    revenue_per_user = 9.00
    fixes_per_user   = 200  # average power user
    cost_per_user    = fixes_per_user * cost_per_fix
    margin_per_user  = revenue_per_user - cost_per_user
    margin_pct       = (margin_per_user / revenue_per_user) * 100

    print(f"\n  Pricing sanity check (Developer plan @ $9/mo):")
    print(f"  Fixes per paying user/month: {fixes_per_user}")
    print(f"  API cost per user:           ${cost_per_user:.2f}")
    print(f"  Gross margin per user:       ${margin_per_user:.2f} ({margin_pct:.0f}%)")

    if margin_pct > 60:
        print(f"  → Healthy margin ✓")
    elif margin_pct > 30:
        print(f"  → Acceptable margin — watch usage closely")
    else:
        print(f"  → Thin margin — consider haiku for free tier users")

    print()

    # Recommendations
    if model == "sonnet" and monthly_fixes >= 10_000:
        haiku_p = PRICING["haiku"]
        haiku_cost = ((monthly_fixes * AVG_INPUT_TOKENS / 1_000_000) * haiku_p["input"] +
                      (monthly_fixes * AVG_OUTPUT_TOKENS / 1_000_000) * haiku_p["output"])
        savings = total_cost - haiku_cost
        print(f"  💡 Tip: Using Haiku for free-tier users saves ${savings:,.2f}/mo")
        print(f"          Reserve Sonnet for paying users only.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Neo Bug Forge cost estimator")
    parser.add_argument("--fixes", type=int, default=5000, help="Monthly fix count")
    parser.add_argument("--model", choices=["sonnet", "haiku", "opus"], default="sonnet")
    args = parser.parse_args()

    estimate(args.fixes, args.model)

    # Show comparison across volumes
    print("  Volume comparison (Sonnet):")
    print(f"  {'Fixes/month':<15} {'Total cost':<15} {'Per fix'}")
    print(f"  {'─'*45}")
    p = PRICING["sonnet"]
    for fixes in [1_000, 5_000, 10_000, 50_000, 100_000]:
        ic = (fixes * AVG_INPUT_TOKENS  / 1_000_000) * p["input"]
        oc = (fixes * AVG_OUTPUT_TOKENS / 1_000_000) * p["output"]
        tc = ic + oc
        cpf = tc / fixes
        print(f"  {fixes:>12,}    ${tc:>10,.2f}    ${cpf:.4f}")
    print()
