"""Discrete-event simulation of submarine cable repair as a rationed queue.

The object of study is *restoration duration*, decomposed into

    duration = wait  +  mobilise  +  service

where `wait` is time spent queueing for a vessel that is busy, `mobilise` is
transit from berth to fault site, and `service` is on-site repair work.

The empirical literature treats duration as exogenous and geophysical
(Cariolle 2026). This module makes the opposite assumption testable: vessels
are a finite shared resource allocated by contract seniority, so `wait` is an
economic quantity even when `mobilise` and `service` are physical ones.

No third-party queueing library is used deliberately: the allocation rule is
the object of interest, so it should be legible in the source rather than
hidden in a framework.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field, replace
from typing import Iterable, Literal, Sequence

import numpy as np
import pandas as pd

JobKind = Literal["fault", "planned"]
Discipline = Literal["priority", "fifo", "severity", "social"]


# --------------------------------------------------------------------------
# Primitives
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Cable:
    """A cable system exposed to faults and holding a contractual position.

    tier
        Seniority in the maintenance agreement. 1 = dedicated/priority
        capacity, 2 = ordinary club member, 3 = non-member (spot charter).
        This is the variable the identification strategy turns on.
    has_backup
        Whether traffic reroutes on failure (alternate cable, microwave,
        satellite). Enters the *cost* of an outage, not its duration -- and
        therefore enters the operator's optimal choice of `tier`.
    hazard_per_1000km_yr
        Fault arrival intensity. ICPC reports 150-200 faults/yr across
        ~1.8m km of cable; shallow, trawled, anchored water is far above
        that average and deep water far below.
    """

    cable_id: str
    zone: str
    km: float
    tier: int = 2
    has_backup: bool = True
    hazard_per_1000km_yr: float = 0.11
    mean_depth_m: float = 500.0
    outage_cost_per_day: float = 1.0
    label: str = ""

    @property
    def annual_fault_rate(self) -> float:
        return self.hazard_per_1000km_yr * self.km / 1000.0


@dataclass(frozen=True)
class Vessel:
    """A standby hull. `transit_days_mean` proxies berth-to-zone distance."""

    vessel_id: str
    zone: str
    transit_days_mean: float = 4.0
    # A vessel configured for laying cannot take a repair without refit.
    repair_capable: bool = True


@dataclass
class Job:
    job_id: int
    kind: JobKind
    cable_id: str
    zone: str
    tier: int
    t_arrive: float          # fault occurrence, or scheduled maintenance date
    severity: float          # 1.0 = full break, 0.4 = partial core damage
    service_days: float
    transit_days: float
    earliest_start: float    # planned work cannot be pulled forward
    # filled by the simulator
    t_assigned: float | None = None
    t_start: float | None = None
    t_restore: float | None = None
    vessel_id: str | None = None
    queue_len_on_arrival: int = 0
    open_faults_in_zone: int = 0


@dataclass
class Scenario:
    """A complete parameterisation. Counterfactuals are `replace()` of this."""

    name: str
    cables: Sequence[Cable]
    vessels: Sequence[Vessel]
    horizon_years: float = 10.0
    discipline: Discipline = "priority"

    # service-time distribution: lognormal in days
    service_median_days: float = 9.0
    service_log_sd: float = 0.55
    # a full break needs more work than a partial fibre fault
    severity_service_multiplier: float = 1.8
    # deep water is slower to grapnel and splice
    depth_service_elasticity: float = 0.12

    # mobilisation
    transit_log_sd: float = 0.35
    mobilise_fixed_days: float = 1.0   # spares loading; ACMA KPI is sail within 24h

    # planned maintenance: scheduled vessel-days that pre-empt nothing but
    # occupy hulls. This is the construction/maintenance crowding-out channel.
    planned_jobs_per_vessel_yr: float = 0.0
    planned_job_days: float = 21.0
    planned_is_blocking: bool = True

    # weather / access downtime: a vessel on station but unable to work
    weather_downtime_share: float = 0.15

    seed: int = 0


# --------------------------------------------------------------------------
# Queue discipline
# --------------------------------------------------------------------------
def sort_key(job: Job, discipline: Discipline, now: float) -> tuple:
    """Lower sorts first. This function *is* the allocation mechanism."""
    if discipline == "fifo":
        return (job.t_arrive, job.job_id)
    if discipline == "priority":
        # contract seniority first, arrival order within tier
        return (job.tier, job.t_arrive, job.job_id)
    if discipline == "severity":
        # engineering triage: worst break first, ignore contracts
        return (-job.severity, job.t_arrive, job.job_id)
    if discipline == "social":
        # planner's rule: shortest weighted delay, i.e. serve where the
        # marginal day of outage is most costly. Requires knowing costs,
        # which is precisely what disclosure would reveal.
        return (-job.severity * (0.0 if job.tier == 0 else 1.0), job.t_arrive, job.job_id)
    raise ValueError(discipline)


# --------------------------------------------------------------------------
# Draws
# --------------------------------------------------------------------------
def _draw_faults(sc: Scenario, rng: np.random.Generator) -> list[Job]:
    jobs: list[Job] = []
    jid = 0
    horizon_days = sc.horizon_years * 365.25
    by_id = {c.cable_id: c for c in sc.cables}
    for cable in sc.cables:
        expected = cable.annual_fault_rate * sc.horizon_years
        n = rng.poisson(expected)
        times = np.sort(rng.uniform(0.0, horizon_days, size=n))
        for t in times:
            # ~55% of coded Taiwanese domestic faults are partial core damage
            severity = 1.0 if rng.random() < 0.45 else 0.4
            depth_mult = (cable.mean_depth_m / 500.0) ** sc.depth_service_elasticity
            sev_mult = sc.severity_service_multiplier if severity >= 1.0 else 1.0
            base = sc.service_median_days * sev_mult * depth_mult
            service = float(rng.lognormal(np.log(base), sc.service_log_sd))
            service /= max(1e-6, 1.0 - sc.weather_downtime_share)
            transit = float(
                rng.lognormal(np.log(4.0), sc.transit_log_sd)
            )  # rescaled per-vessel at assignment
            jobs.append(
                Job(
                    job_id=(jid := jid + 1),
                    kind="fault",
                    cable_id=cable.cable_id,
                    zone=cable.zone,
                    tier=cable.tier,
                    t_arrive=float(t),
                    severity=severity,
                    service_days=service,
                    transit_days=transit,
                    earliest_start=float(t),
                )
            )
    _ = by_id
    return jobs


def _draw_planned(sc: Scenario, rng: np.random.Generator) -> list[Job]:
    """Scheduled maintenance and installation work booked on the same hulls."""
    if sc.planned_jobs_per_vessel_yr <= 0:
        return []
    jobs: list[Job] = []
    jid = 10_000_000
    horizon_days = sc.horizon_years * 365.25
    for v in sc.vessels:
        n = rng.poisson(sc.planned_jobs_per_vessel_yr * sc.horizon_years)
        for t in np.sort(rng.uniform(0.0, horizon_days, size=n)):
            jobs.append(
                Job(
                    job_id=(jid := jid + 1),
                    kind="planned",
                    cable_id="PLANNED",
                    zone=v.zone,
                    tier=0 if sc.planned_is_blocking else 3,
                    t_arrive=float(t),
                    severity=0.0,
                    service_days=sc.planned_job_days,
                    transit_days=0.0,
                    earliest_start=float(t),
                )
            )
    return jobs


# --------------------------------------------------------------------------
# The event loop
# --------------------------------------------------------------------------
def simulate(sc: Scenario) -> pd.DataFrame:
    """Run one replication. Returns one row per job."""
    rng = np.random.default_rng(sc.seed)
    jobs = _draw_faults(sc, rng) + _draw_planned(sc, rng)
    jobs.sort(key=lambda j: j.t_arrive)

    zones = sorted({v.zone for v in sc.vessels} | {c.zone for c in sc.cables})
    # free-time heap per zone: (t_free, vessel_id)
    free: dict[str, list[tuple[float, str]]] = {z: [] for z in zones}
    vessel_by_id: dict[str, Vessel] = {}
    for v in sc.vessels:
        if not v.repair_capable:
            continue
        heapq.heappush(free[v.zone], (0.0, v.vessel_id))
        vessel_by_id[v.vessel_id] = v

    pending: dict[str, list[Job]] = {z: [] for z in zones}
    done: list[Job] = []
    idx = 0
    n = len(jobs)
    # event times we must visit: every arrival and every vessel release
    while idx < n or any(pending[z] for z in zones):
        # advance clock to next arrival or next vessel release among zones
        next_arrival = jobs[idx].t_arrive if idx < n else np.inf
        next_release = np.inf
        for z in zones:
            if pending[z] and free[z]:
                next_release = min(next_release, free[z][0][0])
        now = min(next_arrival, next_release)
        if not np.isfinite(now):
            break

        # admit all arrivals at this instant
        while idx < n and jobs[idx].t_arrive <= now + 1e-12:
            j = jobs[idx]
            j.queue_len_on_arrival = len(pending[j.zone])
            j.open_faults_in_zone = sum(
                1 for p in pending[j.zone] if p.kind == "fault"
            )
            pending[j.zone].append(j)
            idx += 1

        # dispatch in every zone that has both a free hull and pending work
        for z in zones:
            while pending[z] and free[z] and free[z][0][0] <= now + 1e-12:
                eligible = [j for j in pending[z] if j.earliest_start <= now + 1e-12]
                if not eligible:
                    break
                eligible.sort(key=lambda j: sort_key(j, sc.discipline, now))
                job = eligible[0]
                t_free, vid = heapq.heappop(free[z])
                vessel = vessel_by_id[vid]
                start_avail = max(now, t_free, job.earliest_start)
                transit = 0.0
                if job.kind == "fault":
                    transit = job.transit_days * (vessel.transit_days_mean / 4.0)
                    transit += sc.mobilise_fixed_days
                job.t_assigned = start_avail
                job.t_start = start_avail + transit
                job.t_restore = job.t_start + job.service_days
                job.vessel_id = vid
                job.transit_days = transit
                heapq.heappush(free[z], (job.t_restore, vid))
                pending[z].remove(job)
                done.append(job)

    return _to_frame(done, sc)


def _to_frame(done: Iterable[Job], sc: Scenario) -> pd.DataFrame:
    cost = {c.cable_id: c.outage_cost_per_day for c in sc.cables}
    backup = {c.cable_id: c.has_backup for c in sc.cables}
    rows = []
    for j in done:
        if j.t_restore is None:
            continue
        wait = j.t_assigned - j.t_arrive
        rows.append(
            {
                "scenario": sc.name,
                "seed": sc.seed,
                "job_id": j.job_id,
                "kind": j.kind,
                "cable_id": j.cable_id,
                "zone": j.zone,
                "tier": j.tier,
                "severity": j.severity,
                "t_arrive": j.t_arrive,
                "wait_days": wait,
                "transit_days": j.transit_days,
                "service_days": j.service_days,
                "duration_days": j.t_restore - j.t_arrive,
                "wait_share": wait / max(1e-9, j.t_restore - j.t_arrive),
                "queue_len_on_arrival": j.queue_len_on_arrival,
                "open_faults_in_zone": j.open_faults_in_zone,
                "has_backup": backup.get(j.cable_id, False),
                "outage_cost": (j.t_restore - j.t_arrive) * cost.get(j.cable_id, 0.0),
                "vessel_id": j.vessel_id,
            }
        )
    return pd.DataFrame(rows)


def replicate(sc: Scenario, n_reps: int = 20) -> pd.DataFrame:
    """Run `n_reps` independent replications and stack them."""
    return pd.concat(
        [simulate(replace(sc, seed=sc.seed + r)) for r in range(n_reps)],
        ignore_index=True,
    )
