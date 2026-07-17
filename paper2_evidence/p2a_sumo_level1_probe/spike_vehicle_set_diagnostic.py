import libsumo as traci

NET = "/tmp/sumo_probe/net_tls.xml"
ROUTES = "/tmp/sumo_probe/routes2.rou.xml"
SPLIT_T = 30
HORIZON = 10


def start(seed, extra=None):
    args = ["sumo", "-n", NET, "-r", ROUTES, "--seed", str(seed),
            "--no-step-log", "true", "--no-warnings", "true"]
    if extra:
        args += extra
    traci.start(args)


def vids():
    return sorted(traci.vehicle.getIDList())


# continuous
start(1)
for _ in range(SPLIT_T):
    traci.simulationStep()
traci.simulation.saveState("/tmp/sumo_probe/ckpt2.sumo")
cont_ids_at_split = vids()
cont_trail = []
for _ in range(HORIZON):
    traci.simulationStep()
    cont_trail.append(vids())
traci.close()

# checkpoint reload
start(1, extra=["--load-state", "/tmp/sumo_probe/ckpt2.sumo"])
reload_ids_at_split = vids()
reload_trail = []
for _ in range(HORIZON):
    traci.simulationStep()
    reload_trail.append(vids())
traci.close()

print("ids at split equal:", cont_ids_at_split == reload_ids_at_split)
print("cont at split:", cont_ids_at_split)
print("reload at split:", reload_ids_at_split)
for i in range(HORIZON):
    same = cont_trail[i] == reload_trail[i]
    print(f"t+{i+1}: same_vehicle_set={same}", "" if same else f"  cont={cont_trail[i]} reload={reload_trail[i]}")
