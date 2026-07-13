"""SimContract CLI: list domains, run sessions, play interactively, replay, analyze."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from simcontract.analysis import default_registry as analyzer_registry
from simcontract.analysis import write_report
from simcontract.composition import create_registry, domain_assets
from simcontract.contracts import BundleView
from simcontract.engine import (
    BoundedLlmController,
    FreeLlmController,
    HumanController,
    RandomValidController,
    RuleController,
    SessionRunner,
    TopScoreController,
    replay_bundle,
)
from simcontract.evidence import write_bundle
from simcontract.llm import LlmClient


def _build_controllers(adapter, condition_map, personas, weights_for, llm, schema):
    controllers = {}
    for role in adapter.roles:
        for slot in role.slots():
            condition = condition_map.get(slot, condition_map.get("all"))
            if condition is None or condition == "unassigned":
                continue
            persona = personas.get(slot)
            weights = weights_for(role.role, persona)
            if condition == "rule":
                controllers[slot] = RuleController(adapter.default_action_provider, persona)
            elif condition == "random_valid":
                controllers[slot] = RandomValidController()
            elif condition == "top_score":
                controllers[slot] = TopScoreController(weights)
            elif condition == "bounded_llm":
                controllers[slot] = BoundedLlmController(llm, weights, persona)
            elif condition == "free_llm":
                controllers[slot] = FreeLlmController(
                    llm, schema.fields_for(role.role), persona, role.role)
            else:
                raise SystemExit(f"unknown condition {condition!r} for {slot}")
    return controllers


def _parse_kv(spec: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if spec:
        for pair in spec.split(","):
            key, _, value = pair.partition("=")
            out[key.strip()] = value.strip()
    return out


def cmd_domains(_args) -> int:
    registry = create_registry()
    for alias in registry.aliases():
        adapter = registry.create(alias)
        m = adapter.manifest
        print(f"{alias:22s} v{m.domain_version}  roles="
              f"{[f'{r.role}x{r.count}' for r in m.roles]}  scenarios={list(m.scenario_ids)}")
    return 0


def _runner_for(alias: str):
    registry = create_registry()
    adapter = registry.create(alias)
    schema, observation, catalog, weights_for = domain_assets(alias)
    return adapter, schema, observation, catalog, weights_for


def cmd_run(args) -> int:
    adapter, schema, observation, catalog, weights_for = _runner_for(args.domain)
    llm = LlmClient(args.llm_base_url, args.llm_model)
    conditions = _parse_kv(args.controllers) or {"all": "rule"}
    personas = _parse_kv(args.personas)
    controllers = _build_controllers(adapter, conditions, personas, weights_for, llm, schema)

    runner = SessionRunner(adapter, schema, observation, catalog)
    result = runner.run(scenario_id=args.scenario, run_seed=args.seed,
                        rounds=args.rounds, controllers=controllers,
                        personas=personas,
                        on_round=(_print_round if args.verbose else None))
    out = write_bundle(result, args.out)
    manifest = json.loads((out / "manifest.json").read_text())
    print(f"bundle written: {out}")
    print(f"content_hash:   {manifest['content_hash']}")
    return 0


def _print_round(round_no, outcome):
    metrics = ", ".join(f"{k}={v}" for k, v in sorted(outcome.system_metrics.items()))
    print(f"  round {round_no}: {metrics}")


def cmd_play(args) -> int:
    adapter, schema, observation, catalog, weights_for = _runner_for(args.domain)
    role = args.role.rsplit("_", 1)[0]

    def input_fn(slot, fields, view, candidates):
        print(f"\n=== your turn: {slot} ===")
        print(f"observable state: {json.dumps(view, indent=2, default=str)[:800]}")
        values = {}
        for name, rule in fields.items():
            ftype = rule.get("type")
            while True:
                raw = input(f"  {name} ({ftype}"
                            f"{', ' + str(rule.get('min')) + '..' + str(rule.get('max')) if 'min' in rule else ''}"
                            f"{', choices ' + str(rule.get('choices')) if 'choices' in rule else ''}): ").strip()
                try:
                    if ftype == "float":
                        values[name] = float(raw)
                    elif ftype == "int":
                        values[name] = int(raw)
                    elif ftype == "bool":
                        values[name] = raw.lower() in ("1", "true", "y", "yes")
                    else:
                        values[name] = raw
                    break
                except ValueError:
                    print("    invalid, try again")
        return values

    conditions = {"all": "rule"}
    personas: dict[str, str] = {}
    controllers = _build_controllers(adapter, conditions, personas,
                                     weights_for, LlmClient(), schema)
    controllers[args.role] = HumanController(input_fn, schema.fields_for(role), role)

    runner = SessionRunner(adapter, schema, observation, catalog)
    result = runner.run(scenario_id=args.scenario, run_seed=args.seed,
                        rounds=args.rounds, controllers=controllers,
                        personas=personas, on_round=_print_round)
    out = write_bundle(result, args.out)
    print(f"\nsession bundle: {out}")
    return 0


def cmd_replay(args) -> int:
    bundle = BundleView.load(args.bundle)
    alias = bundle.manifest.domain_id
    adapter, schema, observation, catalog, _ = _runner_for(alias)
    report = replay_bundle(bundle, adapter, schema, observation, catalog)
    print(f"rounds compared: {report.rounds_compared}, equal: {report.equal_rounds}")
    print("REPLAY EQUIVALENT" if report.equivalent else "REPLAY MISMATCH")
    for mismatch in report.mismatches[:3]:
        print(json.dumps(mismatch, indent=2))
    return 0 if report.equivalent else 1


def cmd_analyze(args) -> int:
    bundles = [BundleView.load(p) for p in args.bundles]
    registry = analyzer_registry()
    ids = args.analyzers.split(",") if args.analyzers else registry.ids()
    results = [registry.get(a).run(bundles) for a in ids]
    report = write_report(results, args.out)
    print(f"report: {report}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="simcontract")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("domains", help="list registered domains")

    p_run = sub.add_parser("run", help="run a session and write an evidence bundle")
    p_run.add_argument("--domain", required=True)
    p_run.add_argument("--scenario", required=True)
    p_run.add_argument("--rounds", type=int, default=5)
    p_run.add_argument("--seed", type=int, default=73)
    p_run.add_argument("--controllers", help="slot=cond,... or all=cond", default="all=rule")
    p_run.add_argument("--personas", help="slot=persona,...", default="")
    p_run.add_argument("--out", default="results/run")
    p_run.add_argument("--llm-base-url", default=None)
    p_run.add_argument("--llm-model", default=None)
    p_run.add_argument("--verbose", action="store_true")

    p_play = sub.add_parser("play", help="play one role interactively (others rule)")
    p_play.add_argument("--domain", required=True)
    p_play.add_argument("--scenario", required=True)
    p_play.add_argument("--role", required=True, help="role slot, e.g. regulator_1")
    p_play.add_argument("--rounds", type=int, default=5)
    p_play.add_argument("--seed", type=int, default=73)
    p_play.add_argument("--out", default="results/play")

    p_replay = sub.add_parser("replay", help="re-execute a bundle and compare")
    p_replay.add_argument("--bundle", required=True)

    p_an = sub.add_parser("analyze", help="run analyzers over bundles")
    p_an.add_argument("--bundles", nargs="+", required=True)
    p_an.add_argument("--analyzers", default="")
    p_an.add_argument("--out", default="results/analysis")

    args = parser.parse_args(argv)
    return {"domains": cmd_domains, "run": cmd_run, "play": cmd_play,
            "replay": cmd_replay, "analyze": cmd_analyze}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
