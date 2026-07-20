# Contributing

Thanks for your interest in SimContract. It is a research artifact maintained by
a single author; the following terms keep contributions clean for reuse and
citation.

## Scope and discretion

Issues, feature requests, and pull requests are reviewed and accepted at the
maintainer's **sole discretion**. There is no obligation to respond to, accept,
support, or maintain any contribution, and opening a request does not create a
collaboration or support relationship.

## Inbound = outbound licensing

By submitting a contribution (pull request, patch, code, documentation, or other
material), you agree that **your contribution is licensed to the project under
the MIT License** (the project's `LICENSE`), and you affirm that you are
authorized to license it (you are the author of the contribution, or otherwise
have the right to submit it). You retain your copyright; you grant the project
and its users the MIT rights to your contribution.

## Developer Certificate of Origin

Contributions are made under the Developer Certificate of Origin, version 1.1
(<https://developercertificate.org/>). By contributing you certify the DCO for
your contribution. Signing off your commits (`git commit -s`) is encouraged.

## Notices and attribution

- Do not remove or alter existing copyright, license, or attribution notices
  (`LICENSE`, `NOTICE`).
- Add yourself to `AUTHORS.md` in your pull request if you wish to be recorded.

## Reproducibility hygiene

Changes that affect the evidence pipeline must keep the deterministic benchmark
reproducing its canonical content hash and replay result, and must pass the
test suite and `scripts/reproduction_smoke.py`.
