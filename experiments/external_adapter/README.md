# External-model adapter

Integrates a model that was **not** designed for SimContract, to test whether
the contract is a real boundary rather than a template.

The external model is exempt from the per-role internal layout (ADR 0007). It
must satisfy only the public contract and evidence interfaces; its internals may
differ freely, including via a subprocess or container boundary. Forcing it to
match the controlled domains' internal structure would make the portability
claim circular.

Measure and record:

- integration effort: files changed, lines added, time, exceptions required;
- whether `engine`, generic `evidence`, generic `analysis` needed any change
  (the target is zero);
- which contract obligations were awkward, and why.
