# Scenario generation commands (SUMO 1.27.1)

Fully reproducible from these commands; no external dataset, no licensing
question beyond SUMO's own EPL-2.0. One network, two demand configurations
(two `scenario_id` values in the adapter).

```bash
netgenerate --grid --grid.number=3 --grid.length=100 \
  --default.lanenumber=1 --tls.set=B1 -o net.xml

# scenario_id = grid3x3_moderate_v1 (20 vehicles / 60s)
python "$SUMO_HOME/tools/randomTrips.py" -n net.xml -r routes_moderate.rou.xml \
  -e 60 --seed 1 --period 3

# scenario_id = grid3x3_dense_v1 (60 vehicles / 60s)
python "$SUMO_HOME/tools/randomTrips.py" -n net.xml -r routes_dense.rou.xml \
  -e 60 --seed 1 --period 1
```

One interior 4-way signalised junction (`B1`, 4 phases). Not a real city
network -- see `docs/protocols/p2a_sumo_level1_transfer.md` Sec. 5.
