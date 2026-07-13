"""SimContract CLI: every command is a thin call into the application facade."""
from __future__ import annotations

import argparse
import json
import sys

from simcontract.composition import create_application, create_registry, domain_assets
from simcontract.controllers import HumanController


def _parse_kv(spec: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if spec:
        for pair in spec.split(","):
            key, _, value = pair.partition("=")
            out[key.strip()] = value.strip()
    return out


def _print_round(round_no, outcome):
    metrics = ", ".join(f"{k}={v}" for k, v in sorted(outcome.system_metrics.items()))
    print(f"  round {round_no}: {metrics}")


def cmd_domains(_args) -> int:
    app = create_application()
    for d in app.list_domains():
        print(f"{d['domain_id']:22s} v{d['domain_version']}  roles={d['roles']}  "
              f"scenarios={d['scenarios']}")
    return 0


def cmd_run(args) -> int:
    app = create_application()
    summary = app.run_session(
        domain=args.domain, scenario=args.scenario, seed=args.seed,
        rounds=args.rounds,
        conditions=_parse_kv(args.controllers) or {"all": "rule"},
        personas=_parse_kv(args.personas),
        out_dir=args.out,
        llm_base_url=args.llm_base_url, llm_model=args.llm_model,
        on_round=(_print_round if args.verbose else None),
    )
    print(f"bundle written: {summary['bundle']}")
    print(f"content_hash:   {summary['content_hash']}")
    return 0


def cmd_play(args) -> int:
    app = create_application()
    registry = create_registry()
    adapter = registry.create(args.domain)
    schema, _, _, _ = domain_assets(args.domain)
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

    human = HumanController(input_fn, schema.fields_for(role), role)
    summary = app.run_session(
        domain=args.domain, scenario=args.scenario, seed=args.seed,
        rounds=args.rounds, conditions={"all": "rule"}, personas={},
        out_dir=args.out, extra_controllers={args.role: human},
        on_round=_print_round,
    )
    print(f"\nsession bundle: {summary['bundle']}")
    return 0


def cmd_replay(args) -> int:
    app = create_application()
    report = app.replay_run(args.bundle)
    print(f"rounds compared: {report.rounds_compared}, equal: {report.equal_rounds}")
    print("REPLAY EQUIVALENT" if report.equivalent else "REPLAY MISMATCH")
    for mismatch in report.mismatches[:3]:
        print(json.dumps(mismatch, indent=2))
    return 0 if report.equivalent else 1


def cmd_verify(args) -> int:
    app = create_application()
    verdict = app.verify_bundle(args.bundle)
    print(json.dumps(verdict, indent=2))
    return 0 if verdict["content_hash_ok"] and verdict["files_ok"] else 1


def cmd_analyze(args) -> int:
    app = create_application()
    ids = args.analyzers.split(",") if args.analyzers else None
    report = app.analyse_bundles(args.bundles, ids, args.out)
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

    p_verify = sub.add_parser("verify", help="verify bundle hashes without executing")
    p_verify.add_argument("--bundle", required=True)

    p_an = sub.add_parser("analyze", help="run analyzers over bundles")
    p_an.add_argument("--bundles", nargs="+", required=True)
    p_an.add_argument("--analyzers", default="")
    p_an.add_argument("--out", default="results/analysis")

    args = parser.parse_args(argv)
    return {"domains": cmd_domains, "run": cmd_run, "play": cmd_play,
            "replay": cmd_replay, "verify": cmd_verify,
            "analyze": cmd_analyze}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
