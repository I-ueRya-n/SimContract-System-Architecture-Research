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
lower wind availability). Provenance: equations implemented independently
from the public textbook formulation; parameters chosen for pedagogical
contrast, documented in `defaults.py`.
