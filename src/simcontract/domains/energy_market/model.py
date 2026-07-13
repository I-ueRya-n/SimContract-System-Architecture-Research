"""Merit-order uniform-price auction clearing (spec 7.1). Pure functions."""
from __future__ import annotations

GENERATOR_PARAMS = {
    "generator_1": {"tech": "coal", "cap": 400.0, "intensity": 0.90, "cost": 45.0},
    "generator_2": {"tech": "gas",  "cap": 300.0, "intensity": 0.45, "cost": 60.0},
    "generator_3": {"tech": "wind", "cap": 250.0, "intensity": 0.00, "cost": 15.0},
}

BASE_DEMAND_CLIP = (100.0, 1200.0)


def clear_market(*, policy: dict, generator_actions: dict[str, dict],
                 retailer_actions: dict[str, dict], exogenous: dict,
                 params: dict[str, dict] | None = None) -> dict[str, float]:
    params = params or GENERATOR_PARAMS
    carbon = float(policy["carbon_price"])
    cap_price = float(policy["price_cap"])
    subsidy = float(policy["renewable_subsidy"])
    wind_avail = float(exogenous["wind_availability"])
    shock = float(exogenous["demand_shock"])

    demand = sum(float(a["demand_bid"]) for a in retailer_actions.values()) + shock
    demand = max(BASE_DEMAND_CLIP[0], min(BASE_DEMAND_CLIP[1], demand))

    offers = []
    for slot, action in generator_actions.items():
        p = params[slot]
        if action.get("maintenance"):
            continue
        quantity = min(float(action["capacity_offered"]), p["cap"])
        if p["tech"] == "wind":
            quantity *= wind_avail
        if quantity <= 0:
            continue
        effective = (float(action["price_bid"]) + carbon * p["intensity"]
                     - (subsidy if p["intensity"] == 0.0 else 0.0))
        effective = max(0.0, min(effective, cap_price))
        offers.append((effective, quantity, slot, p))

    offers.sort(key=lambda t: (t[0], t[2]))
    remaining = demand
    dispatched: dict[str, float] = {}
    clearing_price = 0.0
    for effective, quantity, slot, p in offers:
        if remaining <= 0:
            break
        take = min(quantity, remaining)
        dispatched[slot] = take
        remaining -= take
        clearing_price = effective

    served = demand - max(0.0, remaining)
    emissions = sum(q * params[s]["intensity"] for s, q in dispatched.items())
    renewable = sum(q for s, q in dispatched.items() if params[s]["intensity"] == 0.0)
    profit = 0.0
    for slot, q in dispatched.items():
        p = params[slot]
        unit_margin = (clearing_price - p["cost"] - carbon * p["intensity"]
                       + (subsidy if p["intensity"] == 0.0 else 0.0))
        profit += unit_margin * q

    return {
        "clearing_price": round(clearing_price, 4),
        "total_emissions": round(emissions, 4),
        "renewable_share": round(renewable / served, 4) if served > 0 else 0.0,
        "unserved_energy": round(max(0.0, remaining), 4),
        "consumer_cost": round(clearing_price * served, 4),
        "generator_profit_total": round(profit, 4),
    }
