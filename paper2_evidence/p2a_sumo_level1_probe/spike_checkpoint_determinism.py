"""Throwaway technical spike (not part of any protocol yet): can SUMO's
saveState/loadState serve as a serializable checkpoint that SimContract's
pure step(state, actions, ctx) -> Outcome model can wrap, without touching
SUMO's own execution loop semantics?

Three questions:
1. Does continuing live for N seconds equal save-at-T + reload + continue
   for N seconds, bit-identically, on the same metric?
2. Does forcing a specific traffic-light phase at the checkpoint actually
   change the outcome vs. leaving the default program running (so there is
   a real action-to-effect channel)?
3. Is the whole thing deterministic across repeated identical runs?
"""
import libsumo as traci

NET = "/tmp/sumo_probe/net_tls.xml"
ROUTES = "/tmp/sumo_probe/routes2.rou.xml"
TLS = "B1"
SPLIT_T = 30   # seconds into the run where we checkpoint
HORIZON = 30   # seconds to continue after the checkpoint


def start(seed, net=NET, routes=ROUTES, extra=None):
    args = ["sumo", "-n", net, "-r", routes, "--seed", str(seed),
            "--no-step-log", "true", "--no-warnings", "true"]
    if extra:
        args += extra
    traci.start(args)


def waiting_time_metric():
    return sum(traci.vehicle.getWaitingTime(v) for v in traci.vehicle.getIDList())


def run_continuous(seed, total_t):
    start(seed)
    for _ in range(total_t):
        traci.simulationStep()
    m = waiting_time_metric()
    traci.close()
    return m


def run_checkpoint_split(seed, forced_phase=None, trace=False):
    start(seed)
    for _ in range(SPLIT_T):
        traci.simulationStep()
    state_file = "/tmp/sumo_probe/ckpt.sumo"
    traci.simulation.saveState(state_file)
    traci.close()

    traci.start(["sumo", "-n", NET, "-r", ROUTES, "--seed", str(seed),
                 "--no-step-log", "true", "--no-warnings", "true",
                 "--load-state", state_file])
    if forced_phase is not None:
        traci.trafficlight.setPhase(TLS, forced_phase)
        traci.trafficlight.setPhaseDuration(TLS, HORIZON + 1)  # lock it
    trail = []
    for _ in range(HORIZON):
        traci.simulationStep()
        if trace:
            trail.append(waiting_time_metric())
    m = waiting_time_metric()
    traci.close()
    return m, trail


start(1)
num_phases = len(traci.trafficlight.getAllProgramLogics(TLS)[0].phases)
traci.close()
print("num phases:", num_phases)

print("\n=== Q1: continuous vs checkpoint+reload, same everything, per-second trail ===")
start(1)
trail_continuous = []
for i in range(SPLIT_T + HORIZON):
    traci.simulationStep()
    if i >= SPLIT_T:
        trail_continuous.append(waiting_time_metric())
traci.close()
m_checkpoint, trail_checkpoint = run_checkpoint_split(1, forced_phase=None, trace=True)
print(f"continuous_final={trail_continuous[-1]}  checkpoint_reload_final={m_checkpoint}")
first_diff = next((i for i, (a, b) in enumerate(zip(trail_continuous, trail_checkpoint)) if a != b), None)
print(f"first differing second after split: {first_diff} (None = never diverged)")
print(f"continuous_trail[:5]={trail_continuous[:5]}")
print(f"checkpoint_trail[:5]={trail_checkpoint[:5]}")

print("\n=== Q2: does forcing a different TLS phase at the checkpoint change the outcome? ===")
m_default, _ = run_checkpoint_split(1, forced_phase=None)
m_phase0, _ = run_checkpoint_split(1, forced_phase=0)
m_phase2, _ = run_checkpoint_split(1, forced_phase=2)
print(f"default_program={m_default}  forced_phase0={m_phase0}  forced_phase2={m_phase2}  "
      f"differs={len({m_default, m_phase0, m_phase2}) > 1}")

print("\n=== Q3: is checkpoint+reload itself deterministic across repeats? ===")
reps = [run_checkpoint_split(1, forced_phase=None)[0] for _ in range(3)]
print(f"repeats={reps}  all_equal={len(set(reps)) == 1}")

reps_forced = [run_checkpoint_split(1, forced_phase=1)[0] for _ in range(3)]
print(f"repeats_forced_phase1={reps_forced}  all_equal={len(set(reps_forced)) == 1}")
