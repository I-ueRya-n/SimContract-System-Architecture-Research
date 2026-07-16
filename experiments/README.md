# Experiments

`e1`–`e7` are the shared evidence programme. They are **capabilities of
SimContract**, not the property of any one paper: the artifact paper reports
E1–E7, and the architecture paper's evaluation design is built on E1–E6. They
stay flat and shared for that reason.

New work is grouped by **capability**, never by publication:

| Directory | Capability |
|---|---|
| `ablations/` | Disable an architectural mechanism and measure what breaks. |
| `external_adapter/` | Integrate a model not designed for SimContract; measure integration effort. |
| `controller_study/` | Compare controller conditions (paired seeds, adversarial cases, rationale support). |

Naming these after papers would misrepresent ownership — the same experiment
frequently supports more than one paper.
