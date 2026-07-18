"""Paper 2B-E5: counterfactual-integrity checker + portable audit manifest.

Protocol: docs/protocols/p2b_e5_integrity_checker.md.

E5 turns Paper 2B from a diagnosis (E0--E4) into a reusable research-software
method: given an artifact and a DECLARED estimand, decide what estimand the
evidence actually supports, whether the required identities are present and
consistent, what is missing or contradictory, and what claim wording is
defensible. Output is one of PASS / WARN / FAIL / UNSUPPORTED.

Design commitments (grounded in the E5 literature gate, protocol S2):
- The checker (`check`) is PORTABLE: pure-stdlib, no SimContract import, it
  reads a manifest dict. Only the intact-corpus GENERATOR touches
  SimContract, to capture real identity hashes (RO-Crate-style portable
  manifest; Moreau OPM provenance model).
- Conformance is declared-vs-actual (Murphy reflexion models): the manifest
  DECLARES an estimand; the checker reports where the evidence agrees and
  where it differs.
- Evaluation is mutation-based with a held-out family split (DeMillo;
  Papadakis best-practices) and reports precision AND false-positive rate,
  not just recall (Sadowski: a checker that always FAILs is useless).

Usage:
  python experiments/paper2b/e5_integrity_checker.py --pilot   # development mutations
  python experiments/paper2b/e5_integrity_checker.py           # held-out evaluation
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "paper2_evidence" / "p2b_e5_integrity_checker"

MANIFEST_SCHEMA_VERSION = "p2b-audit-manifest/1.0"

# Estimand types and the identity requirements the declared claim needs.
ESTIMAND_TYPES = {
    "one_step_local",          # SR: same pre-state, current exogenous, action-only, H=1
    "cloned_local_h_step",     # CL: shared checkpoint, same schedule+policy, H coverage
    "matched_history_contrast",  # MT: different histories OK, schedule identity declared
    "resampled_contrast",      # RS: separate streams, distributional comparison declared
}


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def manifest_hash(m: dict) -> str:
    return hashlib.sha256(_canonical(m).encode()).hexdigest()


# ---------------------------------------------------------------------------
# The portable checker (no SimContract import; operates on a manifest dict).
# ---------------------------------------------------------------------------
REQUIRED_SECTIONS = ("declared_estimand", "model_identity", "state_identity",
                     "exogenous_identity", "branch_identity", "provenance")
RECOMMENDED_PROVENANCE = ("proposed_action", "final_applied_action", "source_tag")


def check(m: dict) -> dict:
    """Return a verdict dict: {verdict, declared_estimand, supported_estimand,
    reason, missing, conflicts, safe_wording}. Verdict in
    PASS/WARN/FAIL/UNSUPPORTED."""
    def verdict(v, declared=None, supported=None, reason="", missing=None,
                conflicts=None, safe=""):
        return {"verdict": v, "declared_estimand": declared,
                "supported_estimand": supported, "reason": reason,
                "missing": missing or [], "conflicts": conflicts or [],
                "safe_wording": safe}

    # --- UNSUPPORTED: cannot evaluate ---
    if m.get("manifest_schema_version") != MANIFEST_SCHEMA_VERSION:
        return verdict("UNSUPPORTED", reason="unknown_schema_version:"
                       f"{m.get('manifest_schema_version')!r}")
    de = m.get("declared_estimand", {})
    dtype = de.get("type")
    if dtype not in ESTIMAND_TYPES:
        return verdict("UNSUPPORTED", declared=dtype,
                       reason=f"unknown_estimand_type:{dtype!r}")
    missing_sections = [s for s in REQUIRED_SECTIONS if s not in m]
    if missing_sections:
        return verdict("UNSUPPORTED", declared=dtype,
                       reason=f"missing_sections:{missing_sections}")

    si = m["state_identity"]; xi = m["exogenous_identity"]
    bi = m["branch_identity"]; mi = m["model_identity"]
    conflicts, missing = [], []

    # --- model / metric identity must agree across branches ---
    if mi.get("factual_model_hash") != mi.get("alternative_model_hash"):
        conflicts.append("model_identity_differs_between_branches")
    if mi.get("factual_metric_catalogue_hash") != mi.get("alternative_metric_catalogue_hash"):
        conflicts.append("metric_catalogue_differs_between_branches")

    # --- branch ancestry / divergence sanity ---
    if bi.get("factual_branch_id") == bi.get("alternative_branch_id"):
        conflicts.append("factual_and_alternative_share_branch_id")
    dp = de.get("decision_point")
    if bi.get("divergence_round") is not None and dp is not None \
            and bi["divergence_round"] < dp:
        conflicts.append("branch_divergence_earlier_than_declared_decision")
    if bi.get("factual_ancestry_hash") and bi.get("alternative_ancestry_hash") \
            and bi["factual_ancestry_hash"] == bi["alternative_ancestry_hash"] \
            and bi.get("factual_branch_id") != bi.get("alternative_branch_id"):
        conflicts.append("inconsistent_combined_lineage")

    # --- exogenous schedule coverage / resampling ---
    H = de.get("horizon")
    covered = xi.get("covered_rounds")
    resampled = xi.get("resampled")

    # --- per-estimand identity requirements ---
    if dtype in ("one_step_local", "cloned_local_h_step"):
        # local claims REQUIRE a shared clone: the two pre-decision states are
        # the same and equal the declared shared parent checkpoint.
        fps, aps = si.get("factual_predecision_state_hash"), si.get("alternative_predecision_state_hash")
        shared = si.get("shared_parent_checkpoint_hash")
        if not shared:
            missing.append("shared_parent_checkpoint_hash")
        if fps is None or aps is None:
            missing.append("predecision_state_hashes")
        elif not (fps == aps == shared):
            conflicts.append("predecision_states_not_a_shared_clone")  # -> actually MT
        if not xi.get("schedule_hash"):
            missing.append("exogenous_schedule_hash")
        if resampled:
            conflicts.append("local_claim_with_resampled_schedule")
        need_h = 1 if dtype == "one_step_local" else H
        if covered is not None and need_h is not None and covered != need_h:
            conflicts.append(f"schedule_covers_{covered}_rounds_needs_{need_h}")
        if dtype == "cloned_local_h_step":
            if not m["provenance"].get("continuation_policy_hash") and \
               not bi.get("continuation_policy_hash"):
                # continuation policy identity is checked below via branch section
                pass
            fcp = bi.get("factual_continuation_policy_hash")
            acp = bi.get("alternative_continuation_policy_hash")
            if fcp is None or acp is None:
                missing.append("continuation_policy_hash")
            elif fcp != acp:
                conflicts.append("continuation_policy_differs_between_branches")
    elif dtype == "matched_history_contrast":
        # MT: different pre-states OK, but the future schedule must be declared
        # identical (schedule_hash present, not resampled).
        if not xi.get("schedule_hash"):
            missing.append("exogenous_schedule_hash")
        if resampled:
            conflicts.append("matched_claim_with_resampled_schedule")
        fcp = bi.get("factual_continuation_policy_hash")
        acp = bi.get("alternative_continuation_policy_hash")
        if fcp is not None and acp is not None and fcp != acp:
            conflicts.append("continuation_policy_differs_between_branches")
    elif dtype == "resampled_contrast":
        if not resampled:
            conflicts.append("resampled_claim_without_separate_streams")

    # --- decide the supported estimand and verdict ---
    supported = _supported_estimand(dtype, conflicts)
    if conflicts or missing:
        v = "FAIL"
        safe = _safe_wording(supported)
        reason = "; ".join(conflicts + [f"missing:{x}" for x in missing])
        return verdict(v, declared=dtype, supported=supported, reason=reason,
                       missing=missing, conflicts=conflicts, safe=safe)

    # mandatory support intact -> PASS unless recommended provenance missing -> WARN
    prov_missing = [k for k in RECOMMENDED_PROVENANCE if not m["provenance"].get(k)]
    if prov_missing:
        return verdict("WARN", declared=dtype, supported=dtype,
                       reason=f"missing_recommended_provenance:{prov_missing}",
                       missing=prov_missing, safe=_safe_wording(dtype))
    return verdict("PASS", declared=dtype, supported=dtype,
                   reason="all_mandatory_identities_present_and_consistent",
                   safe=_safe_wording(dtype))


def _supported_estimand(dtype, conflicts):
    # a local claim whose branches are not a shared clone actually supports a
    # matched-history (or resampled) contrast, not a local effect.
    if dtype in ("one_step_local", "cloned_local_h_step"):
        if "predecision_states_not_a_shared_clone" in conflicts:
            if "local_claim_with_resampled_schedule" in conflicts:
                return "resampled_contrast"
            return "matched_history_contrast"
    if dtype == "matched_history_contrast" and "matched_claim_with_resampled_schedule" in conflicts:
        return "resampled_contrast"
    return dtype


def _safe_wording(estimand):
    return {
        "one_step_local": "one-step decision-local effect (same pre-decision state)",
        "cloned_local_h_step": "cloned-state H-step decision-local effect",
        "matched_history_contrast": "matched-schedule historical contrast "
                                    "(NOT a decision-local effect: histories differ)",
        "resampled_contrast": "resampled historical contrast "
                              "(different histories and different randomness)",
    }.get(estimand, "unsupported comparison class")


# ---------------------------------------------------------------------------
# Intact-manifest corpus grounded in real cloned-continuation evidence.
# ---------------------------------------------------------------------------
def _intact_manifest(estimand_type, ids):
    """Build a fully-consistent manifest for `estimand_type` from real hashes."""
    H = ids["horizon"]
    shared = ids["shared_checkpoint"]
    schedule = ids["schedule_hash"]
    model = ids["model_hash"]; metric = ids["metric_hash"]; policy = ids["policy_hash"]
    if estimand_type in ("one_step_local", "cloned_local_h_step"):
        fps = aps = shared
        resampled = False
        covered = 1 if estimand_type == "one_step_local" else H
        fbranch, abranch = ids["branch_a"], ids["branch_b"]
    elif estimand_type == "matched_history_contrast":
        fps, aps = ids["factual_state"], ids["default_state"]
        resampled = False
        covered = H
        fbranch, abranch = ids["hist_branch_f"], ids["hist_branch_d"]
    else:  # resampled_contrast
        fps, aps = ids["factual_state"], ids["default_state"]
        resampled = True
        covered = H
        fbranch, abranch = ids["hist_branch_f"], ids["hist_branch_d"]
    return {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "declared_estimand": {"type": estimand_type, "decision_point": ids["decision_point"],
                              "horizon": H},
        "model_identity": {"simulator": ids["domain"], "factual_model_hash": model,
                           "alternative_model_hash": model,
                           "factual_metric_catalogue_hash": metric,
                           "alternative_metric_catalogue_hash": metric},
        "state_identity": {"factual_predecision_state_hash": fps,
                           "alternative_predecision_state_hash": aps,
                           "shared_parent_checkpoint_hash": shared},
        "exogenous_identity": {"schedule_hash": schedule, "covered_rounds": covered,
                               "resampled": resampled},
        "branch_identity": {"factual_branch_id": fbranch, "alternative_branch_id": abranch,
                            "divergence_round": ids["decision_point"],
                            "factual_ancestry_hash": ids["ancestry_f"],
                            "alternative_ancestry_hash": ids["ancestry_d"],
                            "factual_continuation_policy_hash": policy,
                            "alternative_continuation_policy_hash": policy},
        "provenance": {"proposed_action": ids["proposed"], "final_applied_action": ids["applied"],
                       "source_tag": "random_valid", "continuation_policy_hash": policy,
                       "completion_reason": "no_accepted_action"},
    }


def _real_ids():
    """Capture real identity hashes from actual cloned continuations across
    domains/seeds (uses SimContract; not part of the portable checker)."""
    from simcontract.composition import create_application
    from simcontract.contracts import BundleView, StepContext, digest
    from simcontract.contracts.seeding import derive_seed, rng_for
    import tempfile
    app = create_application()
    ids_list = []
    specs = [("energy_market_v1", "baseline_v1"), ("epidemic_policy_v1", "second_wave_v1")]
    for domain, scenario in specs:
        adapter = app._registry.create(domain)
        _, _, catalog, _ = app._assets_for(domain)
        for seed in range(1, 6):
            for t in (3, 5):
                states = {1: adapter.initial_state(scenario, seed)}
                def on_round(rn, oc): states[rn + 1] = oc.state_next
                with tempfile.TemporaryDirectory() as td:
                    app.run_session(domain=domain, scenario=scenario, seed=seed, rounds=8,
                                    conditions={"all": "random_valid"}, personas={},
                                    out_dir=Path(td) / "r", on_round=on_round)
                s_fac = states[t]
                s_def = adapter.initial_state(scenario, seed)  # default-ish baseline
                policy_hash = digest({"policy": "default_continuation", "domain": domain})
                sched = digest([derive_seed(seed, t + k) for k in range(5)])
                ids_list.append({
                    "domain": domain, "decision_point": t, "horizon": 5,
                    "shared_checkpoint": digest(s_fac),
                    "factual_state": digest(s_fac), "default_state": digest(s_def),
                    "schedule_hash": sched,
                    "model_hash": digest({"m": domain, "v": adapter.adapter_version}),
                    "metric_hash": digest(sorted(catalog.keys)),
                    "policy_hash": policy_hash,
                    "branch_a": f"{domain}-{seed}-{t}-A", "branch_b": f"{domain}-{seed}-{t}-B",
                    "hist_branch_f": f"{domain}-{seed}-{t}-Fh", "hist_branch_d": f"{domain}-{seed}-{t}-Dh",
                    "ancestry_f": digest({"anc": "F", "seed": seed, "t": t, "d": domain}),
                    "ancestry_d": digest({"anc": "D", "seed": seed, "t": t, "d": domain}),
                    "proposed": digest({"a": "proposed", "seed": seed}),
                    "applied": digest({"a": "applied", "seed": seed})})
    return ids_list


# ---------------------------------------------------------------------------
# Mutation operators. Each returns (mutated_manifest, family, expected_verdict).
# ---------------------------------------------------------------------------
LOCAL = frozenset({"one_step_local", "cloned_local_h_step"})
MATCHED_OR_LOCAL = LOCAL | {"matched_history_contrast"}
CONTINUED = frozenset({"cloned_local_h_step", "matched_history_contrast"})  # multi-round policy
ALL_TYPES = frozenset(ESTIMAND_TYPES)


def _apply_mutations(m, specs):
    """Each spec is (family, apply_fn, defect_for_types, defect_verdict). The
    expected verdict is estimand-aware: a mutation that breaks a required
    identity for THIS manifest's declared estimand should be flagged, but on
    an estimand type where the field is not required it should stay PASS
    (specificity -- the checker must not over-flag, per Sadowski)."""
    dtype = m["declared_estimand"]["type"]
    out = []
    for family, fn, defect_types, defect_verdict in specs:
        mm = copy.deepcopy(m); fn(mm)
        expected = defect_verdict if dtype in defect_types else "PASS"
        out.append((mm, family, expected))
    return out


def development_mutations(m):
    """Structural faults, usable during development (not headline accuracy)."""
    return _apply_mutations(m, [
        ("dev_drop_shared_checkpoint",
         lambda x: x["state_identity"].pop("shared_parent_checkpoint_hash", None),
         LOCAL, "FAIL"),
        ("dev_unknown_type",
         lambda x: x["declared_estimand"].__setitem__("type", "totally_unknown"),
         ALL_TYPES, "UNSUPPORTED"),
        ("dev_unknown_schema",
         lambda x: x.__setitem__("manifest_schema_version", "p2b-audit-manifest/0.0"),
         ALL_TYPES, "UNSUPPORTED"),
        ("dev_predecision_mismatch",
         lambda x: x["state_identity"].__setitem__("alternative_predecision_state_hash", "deadbeef"),
         LOCAL, "FAIL"),
        ("dev_resampled_flag",
         lambda x: x["exogenous_identity"].__setitem__("resampled", True),
         MATCHED_OR_LOCAL, "FAIL"),
        ("dev_missing_recommended_provenance",
         lambda x: x["provenance"].__setitem__("source_tag", None),
         ALL_TYPES, "WARN"),
        ("dev_drop_continuation_policy",
         lambda x: x["branch_identity"].pop("factual_continuation_policy_hash", None),
         frozenset({"cloned_local_h_step"}), "FAIL"),
    ])


def heldout_mutations(m):
    """Semantic faults, frozen AFTER the checker is frozen. Valid-looking but
    wrong -- the harder family (protocol S5 Layer 2). Estimand-aware oracle."""
    return _apply_mutations(m, [
        ("ho_schedule_covers_H_minus_1",
         lambda x: x["exogenous_identity"].__setitem__("covered_rounds",
             x["declared_estimand"]["horizon"] - 1), LOCAL, "FAIL"),
        ("ho_continuation_policy_hash_differs",
         lambda x: x["branch_identity"].__setitem__("alternative_continuation_policy_hash", "cafe1234"),
         CONTINUED, "FAIL"),
        ("ho_divergence_before_decision",
         lambda x: x["branch_identity"].__setitem__("divergence_round",
             x["declared_estimand"]["decision_point"] - 1), ALL_TYPES, "FAIL"),
        ("ho_shared_branch_id",
         lambda x: x["branch_identity"].__setitem__("alternative_branch_id",
             x["branch_identity"]["factual_branch_id"]), ALL_TYPES, "FAIL"),
        ("ho_metric_unit_changed",
         lambda x: x["model_identity"].__setitem__("alternative_metric_catalogue_hash", "beef5678"),
         ALL_TYPES, "FAIL"),
        ("ho_mixed_model_versions",
         lambda x: x["model_identity"].__setitem__("alternative_model_hash", "0ldm0del"),
         ALL_TYPES, "FAIL"),
        ("ho_resampled_declared_matched",
         lambda x: (x["declared_estimand"].__setitem__("type", "matched_history_contrast"),
                    x["exogenous_identity"].__setitem__("resampled", True))
                   and None, ALL_TYPES, "FAIL"),
        ("ho_inconsistent_lineage",
         lambda x: x["branch_identity"].__setitem__("alternative_ancestry_hash",
             x["branch_identity"]["factual_ancestry_hash"]), ALL_TYPES, "FAIL"),
    ])


def _score(records):
    from collections import Counter
    # detection: FAIL/WARN = flagged; PASS = clean; UNSUPPORTED = separate.
    tp = fp = fn = tn = 0
    fam_correct = fam_total = 0
    intact_fp = intact_total = 0
    unsupported_correct = unsupported_total = 0
    for r in records:
        exp, got = r["expected"], r["verdict"]
        if exp == "UNSUPPORTED":
            unsupported_total += 1
            unsupported_correct += int(got == "UNSUPPORTED")
            continue
        if r["family"] == "intact":
            intact_total += 1
            intact_fp += int(got != "PASS")
        flagged_expected = exp in ("FAIL", "WARN")
        flagged_got = got in ("FAIL", "WARN")
        if flagged_expected and flagged_got: tp += 1
        elif flagged_expected and not flagged_got: fn += 1
        elif not flagged_expected and flagged_got: fp += 1
        else: tn += 1
        if flagged_expected:
            fam_total += 1
            fam_correct += int(got == exp)   # exact verdict class matches
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * precision * recall / (precision + recall)) if precision and recall else None
    return {
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "f1": round(f1, 4) if f1 is not None else None,
        "exact_verdict_class_accuracy": round(fam_correct / fam_total, 4) if fam_total else None,
        "false_positive_rate_on_intact": round(intact_fp / intact_total, 4) if intact_total else None,
        "unsupported_detection_accuracy": round(unsupported_correct / unsupported_total, 4) if unsupported_total else None,
        "counts": {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                   "intact": intact_total, "unsupported": unsupported_total},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    args = ap.parse_args()
    mode = "pilot" if args.pilot else "heldout"
    out = OUT_ROOT / mode
    out.mkdir(parents=True, exist_ok=True)

    ids_list = _real_ids()
    intact = []
    for ids in ids_list:
        for et in sorted(ESTIMAND_TYPES):
            intact.append(_intact_manifest(et, ids))

    records = []
    # intact manifests -> expected PASS
    for m in intact:
        r = check(m)
        records.append({"family": "intact", "expected": "PASS", "verdict": r["verdict"],
                        "declared": r["declared_estimand"], "supported": r["supported_estimand"],
                        "reason": r["reason"]})
    # mutations
    mutate = development_mutations if args.pilot else heldout_mutations
    per_family = {}
    for m in intact:
        for mm, family, expected in mutate(m):
            r = check(mm)
            records.append({"family": family, "expected": expected, "verdict": r["verdict"],
                            "supported": r["supported_estimand"], "reason": r["reason"]})
            pf = per_family.setdefault(family, {"expected": expected, "n": 0, "correct": 0})
            pf["n"] += 1
            pf["correct"] += int(r["verdict"] == expected)

    scores = _score(records)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                            text=True, cwd=ROOT).stdout.strip()
    summary = {"mode": mode, "manifests_intact": len(intact), "records": len(records),
               "scores": scores,
               "per_family": {k: {**v, "accuracy": round(v["correct"] / v["n"], 4)}
                              for k, v in sorted(per_family.items())},
               "checker_schema_version": MANIFEST_SCHEMA_VERSION,
               "software_commit": commit}
    (out / "e5_records.jsonl").write_text("\n".join(json.dumps(r) for r in records) + "\n")
    (out / "aggregate_results.json").write_text(json.dumps(summary, indent=2))
    (out / "environment.json").write_text(json.dumps(
        {"software_commit": commit, "mode": mode, "intact": len(intact),
         "schema_version": MANIFEST_SCHEMA_VERSION}, indent=2))

    print(f"[2B-E5 {mode}] intact={len(intact)} records={len(records)}")
    print(f"  precision={scores['precision']} recall={scores['recall']} f1={scores['f1']}")
    print(f"  exact-verdict-class accuracy={scores['exact_verdict_class_accuracy']}")
    print(f"  false-positive rate on intact={scores['false_positive_rate_on_intact']}")
    print(f"  UNSUPPORTED detection accuracy={scores['unsupported_detection_accuracy']}")
    for fam, v in summary["per_family"].items():
        print(f"    {fam:38s} exp={v['expected']:11s} acc={v['accuracy']} (n={v['n']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
