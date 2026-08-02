"""Attestly — 12-month financial model.

Runnable:  python model.py            (prints tables, writes model_output.csv)

Every assumption is a named constant with a research citation in
assumptions.md. Three scenarios are computed (pessimistic / base / optimistic)
so the plan is honest about the biggest risk from the validation scorecard:
organic, no-budget distribution.

Goal check: does cumulative NET profit reach >= $100,000 within 12 months?
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

OUT = Path(__file__).resolve().parent / "model_output.csv"


@dataclass
class Scenario:
    name: str
    # Net new PAYING customers added each month (organic: SEO + marketplace +
    # content). Ramp reflects a full-time solo founder compounding content.
    new_paid: list[int]
    monthly_churn: float          # logo churn on the paying base
    blended_arpu: float           # $/paying customer/month (tier-mix weighted)
    gross_margin: float           # 1 - (Claude COGS + infra) as % of revenue
    payment_fee: float = 0.03     # Stripe
    fixed_monthly: float = 300.0  # hosting + tools + domain + email (no salary)
    one_time_startup: float = 500.0  # incorporation, logo, listings

    active: list[float] = field(default_factory=list)
    mrr: list[float] = field(default_factory=list)
    revenue: list[float] = field(default_factory=list)
    net: list[float] = field(default_factory=list)
    cum_net: list[float] = field(default_factory=list)

    def run(self) -> "Scenario":
        active = 0.0
        cum = 0.0
        for m in range(12):
            churned = active * self.monthly_churn
            active = active - churned + self.new_paid[m]
            mrr = active * self.blended_arpu
            revenue = mrr  # monthly recognized revenue
            gross_profit = revenue * self.gross_margin
            fees = revenue * self.payment_fee
            fixed = self.fixed_monthly + (self.one_time_startup if m == 0 else 0)
            net = gross_profit - fees - fixed
            cum += net
            self.active.append(active)
            self.mrr.append(mrr)
            self.revenue.append(revenue)
            self.net.append(net)
            self.cum_net.append(cum)
        return self


# --- Assumptions (see assumptions.md for citations) -----------------------
# Blended ARPU from tier mix 55% Starter($99) / 35% Growth($249) / 10% Scale($499)
# = $191.5; discounted to $180 for annual prepay / promos.
BLENDED_ARPU = 180.0
# Claude Haiku COGS: only NET-NEW (drafted) questions cost tokens; reuse is free.
# A drafted answer ~ 3k in + 0.7k out tokens. At Haiku 4.5 (~$1/$5 per M) that's
# < $0.01/answer; even at heavy volume COGS + infra stays < 12% of revenue.
GROSS_MARGIN = 0.88
CHURN = 0.05  # 5%/mo logo churn (self-serve SMB/mid-market norm)

BASE = Scenario(
    name="Base",
    new_paid=[2, 4, 6, 9, 12, 16, 20, 24, 28, 33, 38, 44],
    monthly_churn=CHURN,
    blended_arpu=BLENDED_ARPU,
    gross_margin=GROSS_MARGIN,
)
PESSIMISTIC = Scenario(
    name="Pessimistic",
    new_paid=[1, 2, 3, 4, 6, 8, 10, 12, 14, 16, 18, 20],
    monthly_churn=0.06,
    blended_arpu=150.0,
    gross_margin=0.85,
)
OPTIMISTIC = Scenario(
    name="Optimistic",
    new_paid=[3, 6, 10, 15, 20, 26, 32, 38, 45, 52, 60, 68],
    monthly_churn=0.04,
    blended_arpu=200.0,
    gross_margin=0.90,
)


def print_scenario(s: Scenario) -> None:
    s_ = s.run() if not s.cum_net else s
    print(f"\n=== {s_.name} scenario ===")
    print(f"{'Mo':>3} {'Active':>7} {'MRR':>10} {'Revenue':>10} {'Net':>10} {'Cum Net':>11}")
    for m in range(12):
        print(f"{m+1:>3} {s_.active[m]:>7.0f} {s_.mrr[m]:>10,.0f} "
              f"{s_.revenue[m]:>10,.0f} {s_.net[m]:>10,.0f} {s_.cum_net[m]:>11,.0f}")
    print(f"    Ending MRR : ${s_.mrr[-1]:,.0f}  (ARR ${s_.mrr[-1]*12:,.0f})")
    print(f"    Ending paying customers : {s_.active[-1]:.0f}")
    print(f"    12-mo revenue : ${sum(s_.revenue):,.0f}")
    print(f"    12-mo NET profit : ${s_.cum_net[-1]:,.0f}  "
          f"{'✅ >= $100k' if s_.cum_net[-1] >= 100_000 else '❌ below $100k'}")


def write_csv(scenarios: list[Scenario]) -> None:
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "month", "active_customers", "mrr", "revenue", "net_profit", "cumulative_net"])
        for s in scenarios:
            for m in range(12):
                w.writerow([s.name, m + 1, round(s.active[m]), round(s.mrr[m], 2),
                            round(s.revenue[m], 2), round(s.net[m], 2), round(s.cum_net[m], 2)])


def main() -> None:
    scenarios = [PESSIMISTIC.run(), BASE.run(), OPTIMISTIC.run()]
    for s in scenarios:
        print_scenario(s)
    write_csv(scenarios)
    print(f"\nWrote {OUT}")
    print("\nGoal: >= $100,000 cumulative NET profit within 12 months.")
    print(f"  Base case      : ${BASE.cum_net[-1]:,.0f}")
    print(f"  Break-even MRR needed to clear $100k depends on ramp; see assumptions.md.")


if __name__ == "__main__":
    main()
