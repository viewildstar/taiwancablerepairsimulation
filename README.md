# Repair capacity as an economic constraint

**Redundancy is procurable, restoration is not: queue rationing of submarine
cable repair capacity in the Taiwan Strait.**

A discrete-event simulation and replication package for a paper arguing that
submarine cable outage *duration* is not a physical constant but the output of
a rationing mechanism — and that treating it as exogenous biases the existing
empirical literature in a predictable direction.

## Try it

**[Open the chart simulator](https://viewildstar.github.io/taiwancablerepairsimulation/)** —
click any cable off Taiwan to break it, then watch where the time goes. Every completed
repair stacks a bar: waiting for a ship, sailing to the fault, working on site.

The control worth playing with is **"other countries' faults compete."** Switch it off and
waiting collapses from a third of restoration time to about 1%. Taiwan's hulls are shared
across the whole maintenance region, so most of a Taiwanese cable's downtime is spent behind
a fault off Japan or Vietnam. Switch it back on and drag the fleet slider from 4 ships to 3:
median restoration goes from roughly 25 days to 164, and 83% of it is queueing.

`index.html` is a single file with no build step — vanilla JS, no dependencies. Serve it
anywhere, or enable GitHub Pages on the default branch.

## The claim

When a cable breaks, restoration time decomposes as

```
duration  =  wait  +  mobilise  +  service
```

`mobilise` and `service` are physical: transit from berth, grapnel, splice,
test, weather. `wait` is not. Repair is executed by non-profit cooperative
maintenance clubs (ACMA, MECMA, SEAIOCMA, the Pacific zones) that sell standby
availability through a standing charge and **ration by contract seniority when
faults are concurrent**. Non-members charter on the spot market, where the
queue is measured in years.

So `wait` is an economic quantity. Two consequences follow.

**Empirical.** The leading causal estimates of the growth cost of cable
failures use *repair days* as a continuous treatment intensity, justified on
the grounds that repair duration is geophysical and logistical rather than
policy-driven. If duration is partly contractual seniority, the dose is
correlated with the market structure of the affected country's connectivity,
and the dose–response estimate conflates outage length with position in a
queue. Direction of bias: away from zero, since thin-margin non-member
operators get both slower repairs and worse growth for the same underlying
reason.

**Theoretical.** A club sells priority. The value of priority is
`E[wait | junior] − E[wait | senior]`, which falls toward zero as fleet size
rises. Adding hulls therefore destroys the revenue base that finances hulls.
Observed underinvestment in an ageing repair fleet is the mechanism working,
not failing.

## Why Taiwan

It is the only place on earth where the queue is publicly observable. MODA
publishes a live fault table with fault dates, alternate routes, and an
*expected repair date* per open fault, footnoted as depending on cable-ship
scheduling. Its press releases document the service order directly: in early
2025 one vessel arrived at Kaohsiung on 2 February and was instructed to
repair TM3, then TM2, then Taiwan–Penghu No. 3 in sequence. TM2 broke on 16
February and was restored on 14 March — most of those 26 days spent behind
another cable in the same work order.

Taiwan also owns **no cable ship**. Its entire resilience programme runs on
the redundancy margin — a subsidised fourth Matsu cable, microwave expanded to
12.6 Gbps, 770 non-geostationary satellite terminals — because redundancy is a
domestic capital good you can subsidise into existence and restoration
capacity is a shared, congestible service in someone else's ocean.

## Results

Run `make run` (≈40s at 30 replications). Every table lands in `results/`.

**E0 — the zone runs one hull from instability.** Offered load against server
capacity: 4 hulls give utilisation 0.79, 3 hulls give 1.05 and the queue
diverges. This is why a correlated shock produces a long tail rather than a
blip.

**E1 — duration is mostly waiting, and physics predicts the wrong ranking.**

| Cable class | Tier | Mean duration | Mean wait | Mean service | Wait share |
|---|---|---|---|---|---|
| rest of zone | 2 | 49 d | 25 d | 18 d | 39% |
| Taiwan international | 2 | 51 d | 26 d | 19 d | 39% |
| **Taiwan domestic** | **3** | **328 d** | **309 d** | **13 d** | **68%** |

Taiwanese domestic cables are shallow, short and near shore, so their *service*
time is the shortest in the sample — and their duration is six times longer.
Nothing physical explains that. (For external validity: TDM2's October 2025
partial fault carries a published expected repair date of 30 November 2026.)

**E2 — the priority premium collapses.** Value of seniority in days of avoided
wait, indexed to the baseline fleet:

| Fleet | Utilisation | Premium (days) | Index |
|---|---|---|---|
| 4 | 0.79 | 283.6 | 1.00 |
| 5 | 0.63 | 19.4 | 0.07 |
| 6 | 0.52 | 2.6 | 0.01 |
| 8+ | ≤0.39 | ≈0 | ≈0 |

Two additional hulls destroy 93% of what members are paying for.

**E3 — construction crowds out restoration.** Scheduled installation and
maintenance vessel-days at 20% of fleet time raise mean wait from 154 to 918
days and push the share of faults open beyond 90 days from 0.33 to 0.84.

**E4 — redundancy lengthens outages.** On the optimising diagonal, moving from
(no backup, senior) to (backup, junior) raises mean duration from 27 to 206
days while mean outage cost barely moves (77 → 82). Welfare is flat; the
regulator's headline KPI degrades by 7.5×. Time-to-restore is a poor
performance measure in isolation.

**E5 — contract priority is dominated.** Against first-come-first-served,
seniority-based rationing raises mean duration (163 vs 71 days), mean outage
cost (432 vs 192) and inequality of waiting (Gini 0.80 vs 0.56). The
mechanism that funds the fleet is worse than a queue with no mechanism at all.

## Layout

```
src/repairqueue/
  engine.py        non-preemptive multi-server priority queue; the allocation
                   rule is `sort_key()` and is deliberately legible
  calibration.py   Taiwan parameters, every number source-tagged; `utilisation()`
  experiments.py   E0–E6
data/              hand-coded fault events; see data/README.md for provenance
scripts/           runner
tests/             invariants: duration identity, no double-booked hull,
                   monotonicity in fleet size, queue stability
```

Dependencies: numpy and pandas. The queue is hand-rolled on `heapq` rather than
built on a simulation framework, because the allocation rule is the object of
study and should be readable in the source.

## What this is not

The simulation is a **calibrated illustration of a mechanism**, not an
estimate. Parameters marked `ASSUMPTION` in `calibration.py` — domestic cable
lengths, rest-of-zone fault intensity, outage cost ratios, the tier assignment
itself — carry the results and belong in a sensitivity analysis. In particular:

- **`REST_OF_ZONE_FAULTS_PER_YEAR` does most of the work.** Modelling Taiwan
  in isolation makes the queue non-binding and understates wait by an order of
  magnitude, because Taiwan's hulls serve the whole zone. Taiwan can do
  everything right domestically and still wait. That is the substantive point,
  but it means the result is only as good as the zone-load estimate.
- **Tier is unobserved in the real data.** Priority position is not disclosed
  anywhere. Chunghwa Telecom's 2025 annual report says "resilience" 130 times
  and "repair" 14 times, never mentions a cable ship or a maintenance
  agreement, and expressly withholds resilience capital expenditure as
  commercially sensitive. That unobservability is a finding in its own right —
  restoration speed is a credence attribute of wholesale connectivity — but it
  means the empirical stage must instrument for tier or bound it.
- **E6 is a stub.** The December 2025 landslide that faulted six international
  systems in succession is the cleanest available test, because no physical
  channel connects a Taiwanese landslide to a repair delay off Malaysia. Only
  the ship roster does. Shock injection is not yet implemented.

## Next

1. Implement E6 shock injection and the spillover test.
2. Estimation stage: lognormal AFT on time-to-restore with interval censoring,
   regressing on physics (depth, distance from depot, cause, severity) versus
   allocation (concurrent open faults in zone, owner type, agreement
   membership). If allocation survives the physics controls, duration is not
   exogenous.
3. Extend the panel to Japan — same maintenance zones, same hulls, domestic
   vessels — as the within-club comparison that identifies what a berth is
   worth.

## Licence

Code MIT. Coded data derived from Taiwanese government sources released CC0;
see `data/README.md`.
