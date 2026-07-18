# Superseded: phase 1 vs. phase 3 confirmatory pass

This directory is the first confirmatory matrix run (60/60 runs, all
replay/verify/analyzer gates passed), using `fixed_valid_intervention_A` =
force phase 1 and `_B` = force phase 3.

**Not reported as evidence** because phases 1 and 3 turned out to be a
degenerate pair: both are short, all-restrictive yellow transition phases
in this network's auto-generated `tlLogic` (phase 1 = NS-yellow, phase 3 =
EW-yellow, both 3s duration, both blocking the whole junction when locked
for a full round). Every one of the 10 paired seeds produced bit-identical
`waiting_time` between the two conditions, in both demand configurations
-- not a bug, but not a demonstration of "distinguishable legal
interventions" either, since the two conditions were mechanistically
equivalent in effect.

See `docs/protocols/p2a_sumo_level1_transfer.md` Sec. 10's correction
note. The corrected matrix (phase 2 = EW-priority vs. phase 1 = all-stop,
both distinguishable from `rule`'s phase-0 NS-priority baseline and from
each other) is in `paper2_evidence/p2a_sumo_level1_confirmatory/`.

Kept rather than deleted, matching this project's practice of preserving
superseded findings rather than silently discarding them (cf. A2's
STATE_FIELDS correction).
