# ADR 0002: Shared exogenous inputs across branches

SC-I1 comparability requires that the authoritative and applied branches consume the
same per-round exogenous inputs. sample_exogenous is called exactly once per round by
the engine; step receives the result in ctx and may not draw further randomness for
either branch. Rationale: otherwise branch divergence conflates interaction effects
with sampling noise.
