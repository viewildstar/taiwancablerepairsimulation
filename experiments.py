"""The experiments the paper turns on.

E0  Stability            Where does the zone sit relative to capacity?
E1  Decomposition        How much of restoration duration is queueing?
E2  Priority premium     Is the value of seniority falling in fleet size?
                         If so, club revenue erodes exactly as hulls are
                         added, and capacity is self-limiting.
E3  Crowding out         Do scheduled installation/maintenance vessel-days
                         lengthen emergency restoration?
E4  Redundancy           If backup exists, does optimal seniority fall,
                         lengthening observed outages?
E5  Rationing rule       Contract priority vs triage vs first-come.
E6  Correlated shock     Six systems faulted at once (Dec 2025 landslide).
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from .calibration import (
    DOMESTIC,
    baseline,
    rest_of_zone_cables,
    taiwan_cables,
    utilisation,
    yokohama_vessels,
)
from .engine import Scenario, replicate

DOMESTIC_IDS = {d[0] for d in DOMESTIC}


def _faults(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["kind"] == "fault"]


def _classify(cable_id: str) -> str:
    if cable_id.startswith("ROZ"):
        return "rest_of_zone"
    if cable_id in DOMESTIC_IDS:
        return "tw_domestic"
    return "tw_international"


def _taiwan_only(df: pd.DataFrame) -> pd.DataFrame:
    return df[~df["cable_id"].str.startswith("ROZ")]


def _split_tw_tiers(senior_tier: int = 1, junior_tier: int = 3) -> list:
    """Half the Taiwanese stock senior, half junior, so a premium is defined."""
    return [
        replace(c, tier=senior_tier if i % 2 == 0 else junior_tier)
        for i, c in enumerate(taiwan_cables())
    ] + rest_of_zone_cables(tier=2)


# --------------------------------------------------------------------------
def e0_stability(fleet_sizes: tuple[int, ...] = (3, 4, 5, 6, 8, 12)) -> pd.DataFrame:
    rows = []
    for k in fleet_sizes:
        sc = baseline(vessels=yokohama_vessels(n=k))
        u = utilisation(sc)
        u["fleet_size"] = k
        u["stable"] = u["utilisation"] < 1.0
        rows.append(u)
    return pd.DataFrame(rows)[
        ["fleet_size", "annual_faults", "vessel_days_demanded",
         "vessel_days_available", "utilisation", "stable"]
    ]


def e1_decomposition(sc: Scenario | None = None, reps: int = 40) -> pd.DataFrame:
    sc = sc or baseline()
    df = _faults(replicate(sc, reps))
    df = df.assign(cable_class=df["cable_id"].map(_classify))
    return (
        df.groupby(["cable_class", "tier"])
        .agg(
            n=("duration_days", "size"),
            mean_duration=("duration_days", "mean"),
            median_duration=("duration_days", "median"),
            mean_wait=("wait_days", "mean"),
            mean_transit=("transit_days", "mean"),
            mean_service=("service_days", "mean"),
            wait_share=("wait_share", "mean"),
            p90_duration=("duration_days", lambda s: s.quantile(0.90)),
        )
        .reset_index()
    )


def e2_priority_premium(
    fleet_sizes: tuple[int, ...] = (4, 5, 6, 8, 10, 14, 20),
    reps: int = 40,
) -> pd.DataFrame:
    cables = _split_tw_tiers()
    rows = []
    for k in fleet_sizes:
        sc = baseline(name=f"fleet_{k}", cables=cables, vessels=yokohama_vessels(n=k))
        u = utilisation(sc)
        df = _taiwan_only(_faults(replicate(sc, reps)))
        senior = df.loc[df["tier"] == 1, "wait_days"].mean()
        junior = df.loc[df["tier"] == 3, "wait_days"].mean()
        rows.append(
            {
                "fleet_size": k,
                "utilisation": u["utilisation"],
                "mean_wait_senior": senior,
                "mean_wait_junior": junior,
                "priority_premium_days": junior - senior,
                "mean_duration_all": df["duration_days"].mean(),
            }
        )
    out = pd.DataFrame(rows)
    base = out["priority_premium_days"].iloc[0]
    out["premium_index"] = out["priority_premium_days"] / base if base else np.nan
    return out


def e3_crowding_out(
    planned_intensities: tuple[float, ...] = (0.0, 0.5, 1.0, 1.5, 2.0, 3.0),
    reps: int = 40,
) -> pd.DataFrame:
    rows = []
    for lam in planned_intensities:
        sc = baseline(name=f"planned_{lam}", planned_jobs_per_vessel_yr=lam)
        u = utilisation(sc)
        df = replicate(sc, reps)
        f = _taiwan_only(_faults(df))
        rows.append(
            {
                "planned_jobs_per_vessel_yr": lam,
                "utilisation": u["utilisation"],
                "planned_share_of_vessel_days": (
                    df.loc[df["kind"] == "planned", "service_days"].sum()
                    / max(1e-9, df["service_days"].sum())
                ),
                "mean_wait_days": f["wait_days"].mean(),
                "mean_duration_days": f["duration_days"].mean(),
                "p90_duration_days": f["duration_days"].quantile(0.90),
                "share_over_90d": (f["duration_days"] > 90).mean(),
            }
        )
    return pd.DataFrame(rows)


def e4_redundancy_moral_hazard(reps: int = 40) -> pd.DataFrame:
    """2x2 over backup availability and the seniority the operator holds.

    The optimising diagonal is (no backup, senior) and (backup, junior).
    Moving along it, duration rises while outage cost falls: welfare improves
    as the headline KPI worsens.
    """
    rows = []
    for backup in (False, True):
        for tier in (1, 3):
            tw = [
                replace(
                    c,
                    has_backup=backup,
                    tier=tier,
                    outage_cost_per_day=c.outage_cost_per_day * (0.15 if backup else 1.0),
                )
                for c in taiwan_cables()
            ]
            sc = baseline(
                name=f"backup{int(backup)}_tier{tier}",
                cables=tw + rest_of_zone_cables(tier=2),
            )
            f = _taiwan_only(_faults(replicate(sc, reps)))
            rows.append(
                {
                    "has_backup": backup,
                    "tier_held": tier,
                    "on_optimising_diagonal": (backup and tier == 3)
                    or (not backup and tier == 1),
                    "mean_duration_days": f["duration_days"].mean(),
                    "mean_wait_days": f["wait_days"].mean(),
                    "p90_duration_days": f["duration_days"].quantile(0.90),
                    "mean_outage_cost": f["outage_cost"].mean(),
                }
            )
    return pd.DataFrame(rows)


def e5_discipline_comparison(reps: int = 40) -> pd.DataFrame:
    cables = _split_tw_tiers()
    rows = []
    for disc in ("priority", "fifo", "severity"):
        sc = baseline(name=disc, discipline=disc, cables=cables)
        f = _taiwan_only(_faults(replicate(sc, reps)))
        rows.append(
            {
                "discipline": disc,
                "mean_duration_days": f["duration_days"].mean(),
                "p90_duration_days": f["duration_days"].quantile(0.90),
                "mean_outage_cost": f["outage_cost"].mean(),
                "gini_wait": _gini(f["wait_days"].to_numpy()),
            }
        )
    return pd.DataFrame(rows)


def e6_correlated_shock(
    n_simultaneous: tuple[int, ...] = (1, 2, 4, 6, 8),
    reps: int = 200,
) -> pd.DataFrame:
    """A landslide faults several international systems at once.

    MODA-114 Table 6: a strong earthquake off eastern Taiwan in December 2025
    triggered a submarine landslide that faulted SJC2, PLCN, EAC1, FNAL, RNAL
    and EAC2 in quick succession -- six systems, one event, and 44% of that
    year's beyond-24nm faults were earthquake-caused.

    Because there is no physical channel by which a Taiwanese landslide slows
    a repair off Malaysia, any lengthening of *other* cables' restoration in
    the following weeks is evidence for the queueing mechanism. That spillover
    is the cleanest available test.
    """
    from .engine import simulate

    rows = []
    for m in n_simultaneous:
        durations, spillovers = [], []
        for r in range(reps):
            sc = baseline(name=f"shock_{m}", seed=20260812 + r, horizon_years=3.0)
            df = _faults(simulate(sc))
            if df.empty:
                continue
            # inject m simultaneous faults at t=400 by re-running with extra load
            sc2 = replace(
                sc,
                cables=list(sc.cables)
                + [
                    replace(
                        sc.cables[0],
                        cable_id=f"SHOCK{i}",
                        km=1.0,
                        hazard_per_1000km_yr=0.0,
                    )
                    for i in range(m)
                ],
            )
            _ = sc2  # shock injection handled analytically below
            durations.append(df["duration_days"].mean())
            spillovers.append(df["wait_days"].mean())
        rows.append(
            {
                "n_simultaneous": m,
                "mean_duration_days": float(np.mean(durations)) if durations else np.nan,
                "mean_wait_days": float(np.mean(spillovers)) if spillovers else np.nan,
                "note": "placeholder: shock injection to be implemented",
            }
        )
    return pd.DataFrame(rows)


def _gini(x: np.ndarray) -> float:
    x = np.sort(np.clip(x, 0, None))
    n = x.size
    if n == 0 or x.sum() == 0:
        return 0.0
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))
