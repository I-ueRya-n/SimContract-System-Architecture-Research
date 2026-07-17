"""Paper 2A phase-level overhead decomposition (RQ2A.5).

Protocol: docs/protocols/p2a_phase_overhead.md. Method: controlled
instrumentation, not staged feature disabling. Every phase is measured by
wrapping the real, unmodified production objects (observation policy,
controllers, adapter, evidence sink) in timing proxies that record
time.perf_counter() around each delegated call and then call straight
through -- no argument, return value, or control flow is altered. This is
verified, not assumed: the feasibility probe checks an instrumented run
produces the identical content hash to an uninstrumented run of the same
configuration.

Usage:
  python experiments/overhead/phase_overhead.py --probe   # feasibility probe
  python experiments/overhead/phase_overhead.py            # confirmatory
"""
from __future__ import annotations

import argparse
import contextlib
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

import simcontract.engine.session as session_mod
import simcontract.evidence.bundle_writer as writer_mod
from simcontract.composition import create_application
from simcontract.engine.session import SessionRunner
from simcontract.evidence import BundleEvidenceWriter

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "paper2_evidence" / "overhead"
DOMAINS = ["energy_market_v1", "epidemic_policy_v1"]
CONDITIONS = ["rule", "random_valid", "top_score"]
SEEDS = range(1, 31)
ROUNDS = 6

PHASES = ["candidate_generation", "observation", "controller", "validation_syntactic",
         "validation_semantic", "resolution", "evidence_collection", "hashing"]


class Clock:
    """Accumulates elapsed time per phase for one run."""
    def __init__(self):
        self.totals = {p: 0.0 for p in PHASES}
        self.calls = {p: 0 for p in PHASES}

    @contextlib.contextmanager
    def time(self, phase: str):
        t0 = time.perf_counter()
        yield
        self.totals[phase] += time.perf_counter() - t0
        self.calls[phase] += 1


class TimingObservation:
    def __init__(self, real, clock: Clock):
        self._real, self._clock = real, clock

    def view(self, state, role):
        with self._clock.time("observation"):
            return self._real.view(state, role)

    def __getattr__(self, name):
        return getattr(self._real, name)


class TimingController:
    def __init__(self, real, clock: Clock):
        self._real, self._clock = real, clock

    @property
    def condition(self):
        return self._real.condition

    def act(self, view, slot, candidates, previews, ctx):
        with self._clock.time("controller"):
            return self._real.act(view, slot, candidates, previews, ctx)

    def __getattr__(self, name):
        return getattr(self._real, name)


class TimingAdapter:
    def __init__(self, real, clock: Clock):
        self._real, self._clock = real, clock

    def validate_semantic(self, state, action):
        with self._clock.time("validation_semantic"):
            return self._real.validate_semantic(state, action)

    def step(self, state, actions, ctx):
        with self._clock.time("resolution"):
            return self._real.step(state, actions, ctx)

    def __getattr__(self, name):
        return getattr(self._real, name)


class TimingSink:
    """Wraps the real BundleEvidenceWriter. Hashing is separated from the
    rest of finalise() by timing content_hash_of() via a module-level patch
    active only for the duration of this sink's finalise() call."""

    def __init__(self, out_dir, clock: Clock):
        self._real = BundleEvidenceWriter(out_dir)
        self._clock = clock
        self._finalise_wall = 0.0

    def record_round(self, record):
        with self._clock.time("evidence_collection"):
            self._real.record_round(record)

    def record_decision(self, record):
        with self._clock.time("evidence_collection"):
            self._real.record_decision(record)

    def record_event(self, record):
        with self._clock.time("evidence_collection"):
            self._real.record_event(record)

    def record_invocation(self, record):
        with self._clock.time("evidence_collection"):
            self._real.record_invocation(record)

    def finalise(self, manifest, extra=None):
        real_hash_fn = writer_mod.content_hash_of

        def timed_hash(*a, **kw):
            with self._clock.time("hashing"):
                return real_hash_fn(*a, **kw)

        writer_mod.content_hash_of = timed_hash
        t0 = time.perf_counter()
        try:
            self._real.finalise(manifest, extra)
        finally:
            self._finalise_wall = time.perf_counter() - t0
            writer_mod.content_hash_of = real_hash_fn

    @property
    def path(self):
        return self._real.path

    @property
    def content_hash(self):
        return self._real.content_hash


@contextlib.contextmanager
def timed_validate_intake(clock: Clock):
    real = session_mod.validate_intake

    def wrapped(*a, **kw):
        with clock.time("validation_syntactic"):
            return real(*a, **kw)

    session_mod.validate_intake = wrapped
    try:
        yield
    finally:
        session_mod.validate_intake = real


@contextlib.contextmanager
def timed_candidates_and_previews(clock: Clock):
    """action_space() + preview() per candidate -- discovered by the
    feasibility probe to be a first-class, non-negligible phase that
    precedes both the controller's decision and engine-tier validation."""
    real = session_mod.candidates_and_previews

    def wrapped(*a, **kw):
        with clock.time("candidate_generation"):
            return real(*a, **kw)

    session_mod.candidates_and_previews = wrapped
    try:
        yield
    finally:
        session_mod.candidates_and_previews = real


def instrumented_run(app, domain, scenario, condition, seed, rounds, out_dir):
    """Runs one session with every phase timed. Uses the exact same
    production adapter/schema/observation/catalog/controllers construction
    as Application.run_session; only wraps them in timing proxies at the
    SessionRunner boundary."""
    adapter = app._registry.create(domain)
    schema, observation, catalog, weights_for = app._assets_for(domain)
    controllers = app.build_controllers(adapter, schema, weights_for,
                                        {"all": condition}, {})
    clock = Clock()
    wrapped_controllers = {s: TimingController(c, clock) for s, c in controllers.items()}
    sink = TimingSink(out_dir, clock)
    runner = SessionRunner(TimingAdapter(adapter, clock), schema,
                           TimingObservation(observation, clock), catalog,
                           sink=sink)
    t0 = time.perf_counter()
    with timed_validate_intake(clock), timed_candidates_and_previews(clock):
        runner.run(scenario_id=scenario, run_seed=seed, rounds=rounds,
                   controllers=wrapped_controllers, personas={})
    wall = time.perf_counter() - t0
    return wall, clock, sink._real.content_hash, out_dir


def run_feasibility_probe() -> bool:
    app = create_application()
    tmp = OUT_ROOT / "_probe"
    tmp.mkdir(parents=True, exist_ok=True)
    domain, scenario, condition, seed = "energy_market_v1", "baseline_v1", "rule", 1

    # Warm-up (discarded): interpreter/import/OS-cache effects are
    # non-negligible at this workload's ~30ms scale and would otherwise
    # confound the instrumentation-tax comparison below (an early version
    # of this probe measured a spurious *negative* tax purely from the
    # uninstrumented call happening first, i.e. cold).
    app.run_session(domain=domain, scenario=scenario, seed=seed, rounds=ROUNDS,
                    conditions={"all": condition}, personas={}, out_dir=tmp / "warmup")

    # 1. semantic transparency: instrumented vs uninstrumented content hash
    t0 = time.perf_counter()
    uninstrumented = app.run_session(domain=domain, scenario=scenario, seed=seed,
                                     rounds=ROUNDS, conditions={"all": condition},
                                     personas={}, out_dir=tmp / "plain")
    uninstrumented_wall = time.perf_counter() - t0
    wall1, clock1, hash1, _ = instrumented_run(app, domain, scenario, condition,
                                               seed, ROUNDS, tmp / "inst1")
    transparent = uninstrumented["content_hash"] == hash1
    print(f"  [probe] semantic transparency (hash match): {transparent}")

    # 2. reconciliation: measured phases + residual == wall clock (residual
    # is defined as the remainder, so check it is a small, sane fraction)
    measured = sum(clock1.totals.values())
    residual = wall1 - measured
    residual_frac = residual / wall1 if wall1 > 0 else 0.0
    reconciles = 0.0 <= residual_frac < 0.9
    print(f"  [probe] wall={wall1:.4f}s measured={measured:.4f}s "
          f"residual={residual:.4f}s ({residual_frac:.1%}) reconciles={reconciles}")
    instrumentation_tax = wall1 - uninstrumented_wall
    print(f"  [probe] uninstrumented_wall={uninstrumented_wall:.4f}s "
          f"instrumented_wall={wall1:.4f}s "
          f"instrumentation_tax={instrumentation_tax:.4f}s "
          f"({instrumentation_tax/uninstrumented_wall:.1%} of uninstrumented time)")

    # 3. stability: repeat, compare phase totals
    wall2, clock2, hash2, _ = instrumented_run(app, domain, scenario, condition,
                                               seed, ROUNDS, tmp / "inst2")
    same_hash_repeat = hash1 == hash2
    ratio = (sum(clock2.totals.values()) / measured) if measured > 0 else 1.0
    stable = 0.2 < ratio < 5.0  # generous bound; a probe on 6 rounds is fast/noisy
    print(f"  [probe] repeat hash match={same_hash_repeat} "
          f"phase-total ratio={ratio:.2f} stable={stable}")

    ok = transparent and reconciles and same_hash_repeat and stable
    print(f"  [probe] {'PASS' if ok else 'FAIL'}")
    return ok


def _timed_plain(app, domain, scenario, condition, seed, rounds, out_dir) -> float:
    """Mirrors instrumented_run()'s exact object construction (registry.create,
    _assets_for, build_controllers, a bare BundleEvidenceWriter, SessionRunner)
    with no timing proxies. Deliberately does NOT call Application.run_session:
    an earlier version did, and produced a robust ~-6 to -8ms *negative* tax
    even after counterbalancing order. Root cause found by inspection, not
    statistics: run_session() unconditionally calls self._llm_factory(...) ->
    LlmClient.from_env(), which reads environment variables, even for the
    non-LLM `rule` condition -- a real, fixed cost instrumented_run() never
    pays (it does not construct an llm client at all). That made the two
    sides do different amounts of non-timing work, not just differ by the
    timing proxies. Building both sides from the same construction path
    removes the confound."""
    adapter = app._registry.create(domain)
    schema, observation, catalog, weights_for = app._assets_for(domain)
    controllers = app.build_controllers(adapter, schema, weights_for,
                                        {"all": condition}, {})
    sink = BundleEvidenceWriter(out_dir)
    runner = SessionRunner(adapter, schema, observation, catalog, sink=sink)
    t0 = time.perf_counter()
    runner.run(scenario_id=scenario, run_seed=seed, rounds=rounds,
              controllers=controllers, personas={})
    return time.perf_counter() - t0


def run_instrumentation_tax_subsample(app, out_dir: Path) -> dict:
    """Per protocol S5a: a single instrumented-vs-uninstrumented comparison
    is noise-dominated at this workload's ~30ms scale (probe finding, S4a).
    A first version of this subsample always ran the uninstrumented call
    before the instrumented one within each pair, each preceded by only a
    local warm-up call; the result was a suspiciously consistent *negative*
    tax (19/20 pairs, median -8ms) -- a genuine order confound, not noise:
    the instrumented call, always running later in the loop, benefited from
    a monotonic warm-up trend (allocator arenas, OS file cache) that one
    local warm-up call does not fully cancel. Fixed by counterbalancing:
    order alternates every pair, and the reported difference is always
    (instrumented - uninstrumented) regardless of which ran first."""
    domain, scenario, condition, seed = "energy_market_v1", "baseline_v1", "rule", 1
    diffs = []
    for i in range(20):
        import shutil
        inst_first = (i % 2 == 0)
        if inst_first:
            _timed_plain(app, domain, scenario, condition, seed, ROUNDS,
                        out_dir / f"warmup_a_{i}")
            t_inst, _, _, _ = instrumented_run(app, domain, scenario, condition, seed,
                                               ROUNDS, out_dir / f"a_{i}")
            _timed_plain(app, domain, scenario, condition, seed, ROUNDS,
                        out_dir / f"warmup_b_{i}")
            t_plain = _timed_plain(app, domain, scenario, condition, seed, ROUNDS,
                                   out_dir / f"b_{i}")
        else:
            _timed_plain(app, domain, scenario, condition, seed, ROUNDS,
                        out_dir / f"warmup_a_{i}")
            t_plain = _timed_plain(app, domain, scenario, condition, seed, ROUNDS,
                                   out_dir / f"a_{i}")
            _timed_plain(app, domain, scenario, condition, seed, ROUNDS,
                        out_dir / f"warmup_b_{i}")
            t_inst, _, _, _ = instrumented_run(app, domain, scenario, condition, seed,
                                               ROUNDS, out_dir / f"b_{i}")
        diffs.append(t_inst - t_plain)
        for d in ("warmup_a", "a", "warmup_b", "b"):
            shutil.rmtree(out_dir / f"{d}_{i}", ignore_errors=True)

    med, sd = statistics.median(diffs), statistics.pstdev(diffs)
    return {
        "pairs": len(diffs), "order": "counterbalanced (alternating per pair)",
        "median_diff_s": med, "mean_diff_s": statistics.fmean(diffs),
        "min_diff_s": min(diffs), "max_diff_s": max(diffs),
        "stdev_s": sd, "all_diffs_s": diffs,
        "interpretation": (f"not confidently distinguishable from zero at this "
                          f"workload scale (median {med*1000:.2f}ms, "
                          f"stdev {sd*1000:.2f}ms)" if abs(med) < sd else
                          f"measurable: {med*1000:.2f}ms median tax"),
    }


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    args = ap.parse_args()

    if args.probe:
        return 0 if run_feasibility_probe() else 1

    app = create_application()
    out = OUT_ROOT / "confirmatory"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for domain in DOMAINS:
        adapter = app._registry.create(domain)
        for scenario in adapter.manifest.scenario_ids:
            for condition in CONDITIONS:
                for seed in SEEDS:
                    run_dir = out / f"{domain}-{scenario}-{condition}-{seed}"
                    wall, clock, content_hash, _ = instrumented_run(
                        app, domain, scenario, condition, seed, ROUNDS, run_dir)
                    measured = sum(clock.totals.values())
                    bundle_bytes = sum(f.stat().st_size for f in run_dir.rglob("*") if f.is_file())
                    trace_bytes = sum((run_dir / n).stat().st_size for n in
                                      ("decisions.jsonl", "fallback_events.jsonl",
                                       "llm_invocations.jsonl") if (run_dir / n).exists())
                    row = {"domain": domain, "scenario": scenario, "condition": condition,
                          "seed": seed, "wall_s": wall, "measured_s": measured,
                          "residual_s": wall - measured, "bundle_bytes": bundle_bytes,
                          "trace_bytes": trace_bytes, "content_hash": content_hash[:16]}
                    for p in PHASES:
                        row[f"t_{p}_s"] = clock.totals[p]
                    rows.append(row)
                    import shutil
                    shutil.rmtree(run_dir)

    # replay/verify support, measured separately, on a sample of fresh bundles
    replay_rows = []
    with_replay_dir = out / "_replay_sample"
    with_replay_dir.mkdir(exist_ok=True)
    for domain in DOMAINS:
        adapter = app._registry.create(domain)
        scenario = adapter.manifest.scenario_ids[0]
        bundle_dir = with_replay_dir / domain
        app.run_session(domain=domain, scenario=scenario, seed=73, rounds=ROUNDS,
                        conditions={"all": "rule"}, personas={}, out_dir=bundle_dir)
        t0 = time.perf_counter(); app.verify_bundle(bundle_dir); t_verify = time.perf_counter() - t0
        t0 = time.perf_counter(); app.replay_run(bundle_dir); t_replay = time.perf_counter() - t0
        replay_rows.append({"domain": domain, "verify_s": t_verify, "replay_s": t_replay})
        import shutil
        shutil.rmtree(bundle_dir)

    tax_dir = out / "_tax_subsample"
    tax_dir.mkdir(exist_ok=True)
    tax = run_instrumentation_tax_subsample(app, tax_dir)
    (out / "instrumentation_tax.json").write_text(json.dumps(tax, indent=2))
    print(f"  instrumentation_tax: median={tax['median_diff_s']*1000:.3f}ms "
          f"({tax['interpretation']})")

    import csv
    with open(out / "per_run.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with open(out / "replay_verify.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(replay_rows[0].keys()))
        w.writeheader()
        for r in replay_rows:
            w.writerow(r)

    def agg_domain(domain: str) -> dict:
        subset = [r for r in rows if r["domain"] == domain]
        wall_vals = [r["wall_s"] for r in subset]
        result = {"records": len(subset),
                  "wall_s": {"median": statistics.median(wall_vals),
                            "p95": percentile(wall_vals, 0.95),
                            "max": max(wall_vals)},
                  "bundle_bytes": {"median": statistics.median(r["bundle_bytes"] for r in subset)},
                  "trace_bytes": {"median": statistics.median(r["trace_bytes"] for r in subset)},
                  "phases": {}}
        total_median = statistics.median(wall_vals)
        for p in PHASES + ["residual"]:
            key = f"t_{p}_s" if p != "residual" else "residual_s"
            vals = [r[key] for r in subset]
            result["phases"][p] = {
                "median_s": statistics.median(vals), "p95_s": percentile(vals, 0.95),
                "max_s": max(vals),
                "pct_of_total": (statistics.median(vals) / total_median * 100
                                if total_median > 0 else 0.0)}
        return result

    agg = {"by_domain": {d: agg_domain(d) for d in DOMAINS},
          "replay_verify": replay_rows,
          "records": len(rows)}
    (out / "aggregate_results.json").write_text(json.dumps(agg, indent=2))
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                            text=True, cwd=ROOT).stdout.strip()
    (out / "environment.json").write_text(json.dumps(
        {"software_commit": commit, "python": sys.version.split()[0]}, indent=2))

    print(f"[overhead] records={len(rows)}")
    for d, a in agg["by_domain"].items():
        print(f"  {d}: wall_median={a['wall_s']['median']*1000:.2f}ms "
              f"bundle_median={a['bundle_bytes']['median']:.0f}B")
        for p, v in a["phases"].items():
            print(f"    {p:22s} median={v['median_s']*1000:7.3f}ms pct={v['pct_of_total']:5.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
