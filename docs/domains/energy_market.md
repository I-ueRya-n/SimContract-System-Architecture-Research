# energy_market_v1

Controlled, literature-informed electricity-market testbed (merit-order
uniform-price clearing; see Stoft, *Power System Economics*, for the standard
formulation). **Not** a calibrated forecasting model.

Roles/stages: stage 1 `regulator` (carbon price, price cap, renewable
subsidy); stage 2 `generator` ×3 (bid price, offered capacity; coal/gas/wind
technology parameters); stage 2 `retailer` ×2 (demand bid).

Exogenous per round (sampled once, shared by both branches): AR(1) demand
shock; wind availability draw.

Clearing: offers sorted by effective marginal cost (fuel + carbon −
subsidy for renewables), dispatched to demand under the price cap; uniform
clearing price; unserved demand tracked.

Metrics: `clearing_price`, `total_emissions`, `renewable_share`,
`unserved_demand`, per-technology profit, `consumer_cost`.

Semantic legality: capacity offers bounded by installed capacity ×
availability; bids within cap; regulator instruments within declared ranges
(state-dependent where the cap binds).

Default policies (rule condition + SC-I2 completion): marginal-cost bidding
for generators, forecast-demand bidding for retailers, hold-instruments
regulator. Personas: `decarbonisation_first`, `price_stability` (regulator);
`profit_max`, `market_share` (generators).

Scenarios: `baseline` (stable demand), `tight_supply` (higher demand mean,
lower wind availability).

## Provenance matrix (consolidated spec §7.3)

Every component is classified; equations were implemented independently from
the public formulation, and every exact parameter value is **synthetic**
(pedagogical), not paper-estimated.

| Component | Source / status | SimContract adaptation | Verification |
|---|---|---|---|
| Merit-order dispatch (sort offers by effective marginal cost, dispatch to demand) | literature-derived (standard power-market economics) | discrete single-clearing per round | hand-computed fixture; compliance suite |
| Uniform clearing price (marginal accepted offer) | literature-derived | price cap applied as upper bound | `clearing_price` catalog-valid; monotonicity under cap |
| Effective cost = bid + carbon·intensity − subsidy(renewable) | controlled SimContract mechanism (carbon/subsidy as policy levers) | added to marginal cost before sort | rejection + range tests on policy fields |
| Demand shock (AR(1)) | synthetic stochastic process | fixed-seed, `demand_ar1`/`demand_sigma` per scenario | rerun identity (E2) |
| Wind availability | synthetic draw | uniform on `[wind_min, wind_max]` per scenario | rerun identity (E2) |
| Generator technology params (coal/gas/wind: cap, intensity, cost) | **synthetic** pedagogical values (`model.py:GENERATOR_PARAMS`) | three contrasting techs | documented in `model.py` |
| Carbon price / price cap / subsidy magnitudes | **synthetic** scenario values | `scenarios/*.yaml` | scenario-load test |
| Default (rule) bidding policy | SimContract design (marginal-cost + margin) | domain `DefaultActionProvider` | SC-I2 completion test |

Parameter classification: all exact numeric values are **synthetic**. None are
empirically calibrated or expert-elicited. Citations for the foundational
merit-order formulation are flagged verify-before-camera-ready in the
manuscript bibliography and MUST NOT be treated as validating the parameter
values.
