# E6 SUMO scenario (reproducible)

Network: `netgenerate --grid --grid.number=3 --grid.length=100
--default.lanenumber=1 --tls.set=B1 -o net.xml` (one signalised junction B1,
4 phases). Same synthetic grid as Paper 2A's SUMO Level-1 (controlled
companion). A public/upstream SUMO scenario is noted in the protocol as the
next external-realism step; the grid is the controlled replication.

Demand:
- routes_moderate.rou.xml: randomTrips.py -n net.xml -e 60 --seed 1 --period 3
- routes_dense.rou.xml:    randomTrips.py -n net.xml -e 120 --seed 1 --period 0.8
