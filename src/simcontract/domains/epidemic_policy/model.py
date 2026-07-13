"""Regional SEIR dynamics with policy and allocation effects (spec 7.2)."""
from __future__ import annotations

import copy

REGION_PARAMS = {
    "region_manager_1": {"pop": 900_000, "beta0": 0.32, "base_capacity": 1800},
    "region_manager_2": {"pop": 600_000, "beta0": 0.28, "base_capacity": 1200},
    "region_manager_3": {"pop": 300_000, "beta0": 0.36, "base_capacity": 700},
}

SIGMA = 1.0 / 4.0          # E -> I
GAMMA = 1.0 / 7.0          # I -> R
IFR = 0.008
SEVERE_FRACTION = 0.05
VACCINE_EFFICACY = 0.85
RESTRICTION_MULT = [1.0, 0.8, 0.6, 0.45]
MASK_MULT = [1.0, 0.85, 0.72]
TESTING_BETA_REDUCTION = 0.25
CAPACITY_BOOST = 0.5
DAYS_PER_ROUND = 7
RESTRICTION_COST = 1500.0
ILLNESS_COST = 0.9


def initial_regions() -> dict:
    regions = {}
    for slot, params in REGION_PARAMS.items():
        pop = params["pop"]
        infected = int(pop * 0.001)
        regions[slot] = {
            "S": float(pop - infected), "E": float(infected * 2),
            "I": float(infected), "R": 0.0, "D": 0.0,
            "vaccinated": 0.0,
        }
    return regions


def step_week(*, regions: dict, policy: dict, allocations: dict[str, dict],
              exogenous: dict) -> tuple[dict, dict]:
    """One round = seven daily sub-steps. Returns (regions_next, metrics)."""
    regions = copy.deepcopy(regions)
    restriction = int(policy["restriction"])
    mask = int(policy["mask_level"])
    budget = float(policy["vaccine_budget"])
    total_pop = sum(p["pop"] for p in REGION_PARAMS.values())

    new_infections = 0.0
    new_deaths = 0.0
    overflow_days = 0

    for slot, params in REGION_PARAMS.items():
        r = regions[slot]
        alloc = allocations[slot]
        shock = float(exogenous[f"shock_{slot}"])
        beta = (params["beta0"] * shock
                * RESTRICTION_MULT[restriction] * MASK_MULT[mask]
                * (1.0 - TESTING_BETA_REDUCTION * float(alloc["share_testing"])))
        capacity = params["base_capacity"] * (1.0 + CAPACITY_BOOST * float(alloc["share_capacity"]))
        doses_per_day = (budget * float(alloc["share_vaccination"])
                         * params["pop"] / total_pop)

        pop = params["pop"]
        for _ in range(DAYS_PER_ROUND):
            s, e, i = r["S"], r["E"], r["I"]
            infections = beta * s * i / pop
            incubations = SIGMA * e
            recoveries = GAMMA * i
            deaths = recoveries * IFR / GAMMA * GAMMA  # deaths as share of leaving I
            deaths = i * GAMMA * IFR / max(GAMMA, 1e-9)
            deaths = i * IFR * GAMMA * 7 / 7  # simple: IFR applied to resolution flow
            deaths = GAMMA * i * IFR
            vaccinations = min(doses_per_day * VACCINE_EFFICACY, s)

            r["S"] = max(0.0, s - infections - vaccinations)
            r["E"] = max(0.0, e + infections - incubations)
            r["I"] = max(0.0, i + incubations - recoveries - deaths)
            r["R"] = r["R"] + recoveries + vaccinations
            r["D"] = r["D"] + deaths
            r["vaccinated"] = r["vaccinated"] + vaccinations

            new_infections += infections
            new_deaths += deaths
            if r["I"] * SEVERE_FRACTION > capacity:
                overflow_days += 1

    coverages = [regions[s]["vaccinated"] / REGION_PARAMS[s]["pop"]
                 for s in REGION_PARAMS]
    cumulative_deaths = sum(regions[s]["D"] for s in REGION_PARAMS)
    econ_cost = RESTRICTION_COST * restriction * DAYS_PER_ROUND + ILLNESS_COST * new_infections

    metrics = {
        "new_infections": round(new_infections, 2),
        "cumulative_deaths": round(cumulative_deaths, 2),
        "overflow_days": float(overflow_days),
        "econ_cost": round(econ_cost, 2),
        "vaccination_coverage": round(sum(coverages) / len(coverages), 6),
        "equity_gap": round(max(coverages) - min(coverages), 6),
    }
    return regions, metrics
