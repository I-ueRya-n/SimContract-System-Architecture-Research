# Scenario generation commands (SUMO 1.27.1)

Fully reproducible from these two commands; no external dataset, no
licensing question beyond SUMO's own EPL-2.0.

```bash
netgenerate --grid --grid.number=3 --grid.length=100 \
  --default.lanenumber=1 --tls.set=B1 -o net.xml

python "$SUMO_HOME/tools/randomTrips.py" -n net.xml -r routes.rou.xml \
  -e 60 --seed 1 --period 3
```

One interior 4-way signalised junction (`B1`, 4 phases). Not a real city
network -- see `docs/protocols/p2a_sumo_level1_transfer.md` Sec. 5.
