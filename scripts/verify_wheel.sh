#!/usr/bin/env bash
# Non-editable install smoke test (consolidated spec 5.4): build the wheel,
# install it into a clean venv, and run the CLI from the INSTALLED package so
# that missing package-data (domain YAML) is caught before publication.
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"
venv="$(mktemp -d)/venv"

python3 -m venv "$venv"
"$venv/bin/pip" install -q --upgrade pip >/dev/null
"$venv/bin/pip" install -q "$here"

# run from /tmp so nothing resolves against the source tree
cd /tmp
"$venv/bin/simcontract" domains
"$venv/bin/simcontract" run --domain energy_market_v1 --scenario baseline_v1 \
    --seed 73 --rounds 2 --out "$(mktemp -d)/run"

echo "OK: wheel installs cleanly and the CLI runs from the installed package"
