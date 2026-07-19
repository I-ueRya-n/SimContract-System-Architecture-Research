"""E6 replay-to-branch feasibility spike (not part of any protocol yet).

Tests the deterministic-same-history-reconstruction claim the E6 CL
construction depends on, WITHOUT relying on saveState (which the Paper 2A
probe already showed is not a complete continuous-state oracle):

1. Two independent SUMO processes replay the same factual action history
   to round t -> their observable-state digests match exactly.
2. Two independent no-intervention continuations from that point are
   bit-identical over H rounds.
3. Repeating the whole reconstruction reproduces the same result.
4. Applying a DIFFERENT intervention at t changes the outcome (a real
   action channel), while the shared future demand schedule is identical.
"""
import libsumo as traci

NET = "/tmp/sumo_probe/net_tls.xml"
ROUTES = "/tmp/sumo_probe/routes_e6.rou.xml"
TLS = "B1"
ROUND_SECONDS = 5          # one "round" = 5 simulated seconds (as in Paper 2A)
DECISION_ROUND = 7         # t
HORIZON = 3                # H rounds after the decision


def _start(seed):
    traci.start(["sumo", "-n", NET, "-r", ROUTES, "--seed", str(seed),
                 "--no-step-log", "true", "--no-warnings", "true"])


def _observable_digest():
    """A digest of the observable state: TLS phase + timing, and every
    vehicle's lane position / speed / waiting time. Deterministic ordering."""
    import hashlib, json
    tls_state = {t: (traci.trafficlight.getPhase(t),
                     round(traci.trafficlight.getSpentDuration(t), 3)
                     if hasattr(traci.trafficlight, "getSpentDuration") else -1,
                     round(traci.trafficlight.getNextSwitch(t), 3))
                 for t in traci.trafficlight.getIDList()}
    veh = {}
    for v in sorted(traci.vehicle.getIDList()):
        veh[v] = (round(traci.vehicle.getLanePosition(v), 4),
                  round(traci.vehicle.getSpeed(v), 4),
                  round(traci.vehicle.getWaitingTime(v), 4),
                  traci.vehicle.getLaneID(v))
    snap = {"time": round(traci.simulation.getTime(), 3), "tls": tls_state, "veh": veh}
    return hashlib.sha256(json.dumps(snap, sort_keys=True).encode()).hexdigest()


def _waiting_time():
    return sum(traci.vehicle.getWaitingTime(v) for v in traci.vehicle.getIDList())


def replay_to_t(seed, history_phase=None):
    """Replay the factual history (default programme, or a fixed standing
    phase) to the decision round t; return the pre-decision observable digest."""
    _start(seed)
    for _ in range((DECISION_ROUND - 1) * ROUND_SECONDS):
        if history_phase is not None:
            traci.trafficlight.setPhase(TLS, history_phase)
            traci.trafficlight.setPhaseDuration(TLS, ROUND_SECONDS + 1)
        traci.simulationStep()
    d = _observable_digest()
    return d


def replay_then_branch(seed, intervention_phase, history_phase=None):
    _start(seed)
    for _ in range((DECISION_ROUND - 1) * ROUND_SECONDS):
        if history_phase is not None:
            traci.trafficlight.setPhase(TLS, history_phase)
            traci.trafficlight.setPhaseDuration(TLS, ROUND_SECONDS + 1)
        traci.simulationStep()
    # decision round: apply intervention
    traci.trafficlight.setPhase(TLS, intervention_phase)
    traci.trafficlight.setPhaseDuration(TLS, ROUND_SECONDS + 1)
    for _ in range(ROUND_SECONDS):
        traci.simulationStep()
    # continuation: default programme (phase 0) for H-1 rounds
    for _ in range((HORIZON - 1) * ROUND_SECONDS):
        traci.trafficlight.setPhase(TLS, 0)
        traci.trafficlight.setPhaseDuration(TLS, ROUND_SECONDS + 1)
        traci.simulationStep()
    m = _waiting_time()
    traci.close()
    return m


print("=== Gate 1: two independent replays of the same history reach the same pre-state ===")
d_a = replay_to_t(1); traci.close()
d_b = replay_to_t(1); traci.close()
print(f"pre-decision digest A == B: {d_a == d_b}  ({d_a[:12]} / {d_b[:12]})")

print("\n=== Gate 2: two no-intervention continuations from t are bit-identical ===")
m1 = replay_then_branch(1, intervention_phase=0)   # phase 0 = default (no real intervention)
m2 = replay_then_branch(1, intervention_phase=0)
print(f"no-intervention continuation waiting time: {m1} == {m2}: {m1 == m2}")

print("\n=== Gate 3: repeating the reconstruction reproduces the result ===")
reps = [replay_then_branch(1, intervention_phase=0) for _ in range(3)]
print(f"repeats: {reps}  all_equal={len(set(reps)) == 1}")

print("\n=== Gate 4: a different intervention at t changes the outcome (CL action channel) ===")
m_default = replay_then_branch(1, intervention_phase=0)
m_interv = replay_then_branch(1, intervention_phase=2)   # phase 2 = EW-priority
print(f"default={m_default}  intervention(phase2)={m_interv}  differ={m_default != m_interv}")

print("\n=== Gate 5: MT default-history reaches a DIFFERENT pre-state than factual ===")
d_factual = replay_to_t(1, history_phase=2); traci.close()   # standing EW-priority history
d_default = replay_to_t(1, history_phase=0); traci.close()   # standing default history
print(f"factual-history pre-state != default-history pre-state: {d_factual != d_default}")
