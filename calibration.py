"""Taiwan Strait calibration.

Every number here carries a source tag. Where a value is a modelling
assumption rather than an observation it is marked ASSUMPTION and belongs in
the sensitivity analysis, not the headline result.

Sources
-------
MODA-114   Ministry of Digital Affairs, "114年度臺灣海底通訊電纜損害原因分析
           及策進報告", March 2026 (公開版). Released CC0.
MODA-LIVE  MODA, "海纜障礙狀況" live fault table, snapshot 2026-08-11.
ICPC       International Cable Protection Committee, via Insikt Group
           TA-2025-0717: 150-200 faults/yr globally; anchor and fishing gear
           in <200m water dominate; repairs cost USD 1-3m each.
STF        SubTel Forum via TA-2025-0717: ~80 vessels globally dedicated to
           maintaining *and expanding* cable infrastructure; mean restoration
           time 40 days in 2023, rising across 2015-2024.
"""

from __future__ import annotations

from .engine import Cable, Scenario, Vessel

# --------------------------------------------------------------------------
# Fault intensity
# --------------------------------------------------------------------------
# MODA-114: 34 faults inside 24 nautical miles across FY111-114 (9, 11, 7, 7),
# i.e. 8.5/yr against 10 domestic + 15 international systems. Domestic systems
# are short, shallow and trawled; the intensity per 1000 km is therefore very
# high relative to the ICPC global average of roughly 0.11 faults/1000km/yr.
DOMESTIC_HAZARD = 3.2      # ASSUMPTION, back-solved from MODA-114 counts
INTL_INSHORE_HAZARD = 0.35 # ASSUMPTION, back-solved from MODA-114 Table 5
INTL_OFFSHORE_HAZARD = 0.14  # MODA-114 Table 6: 25 events beyond 24nm in FY114

# MODA-114 Table 2 lists 10 domestic systems. Lengths are ASSUMPTIONS on the
# order of the Taiwan-Matsu / Taiwan-Penghu / Penghu-Kinmen distances.
DOMESTIC = [
    ("TM1-D", "Taiwan-Matsu No.1", 240.0, True),
    ("TDM2", "Taiwan-Matsu No.2", 240.0, True),
    ("TM3", "Taiwan-Matsu No.3", 250.0, True),
    ("TP2", "Taiwan-Penghu No.2", 120.0, True),
    ("TP3", "Taiwan-Penghu No.3", 120.0, True),
    ("TK2", "Taiwan-Kinmen No.2", 300.0, True),
    ("PK1", "Penghu-Kinmen No.1", 180.0, True),
    ("PK3", "Penghu-Kinmen No.3", 180.0, True),
    ("LLV1", "Little Liuqiu No.1", 25.0, True),
    ("LLU2", "Little Liuqiu No.2", 25.0, True),
]

# MODA-114 Table 1 lists 15 international systems landing in Taiwan. Only the
# Taiwan-proximate segment is modelled, since MODA reports faults by whether
# they fall inside or outside the 24nm contiguous zone.
INTERNATIONAL = [
    "C2C", "EAC1", "EAC2", "FNAL", "RNAL", "CSCN", "APCN2", "APG",
    "NCP", "PLCN", "TPE", "SJC2", "TSE-1", "FASTER", "APRICOT",
]


def taiwan_cables(
    domestic_tier: int = 2,
    intl_tier: int = 2,
    domestic_backup: bool = True,
) -> list[Cable]:
    """Cable stock around Taiwan as of MODA-114 (15 international, 10 domestic).

    `domestic_tier` and `intl_tier` are the treatment variables. Taiwan holds
    no domestically berthed hull, so no cable here can be tier 1 on the basis
    of a home vessel; tier reflects maintenance-agreement seniority only.
    """
    cables: list[Cable] = []
    for cid, label, km, backup in DOMESTIC:
        cables.append(
            Cable(
                cable_id=cid,
                label=label,
                zone="TW",
                km=km,
                tier=domestic_tier,
                has_backup=backup and domestic_backup,
                hazard_per_1000km_yr=DOMESTIC_HAZARD,
                mean_depth_m=80.0,       # MODA-114: Taiwan Strait is shallow shelf
                outage_cost_per_day=1.0,
            )
        )
    for cid in INTERNATIONAL:
        cables.append(
            Cable(
                cable_id=cid,
                label=cid,
                zone="TW",
                km=900.0,                # ASSUMPTION: Taiwan-proximate segment
                tier=intl_tier,
                has_backup=True,         # MODA-LIVE lists alternate routes for all
                hazard_per_1000km_yr=INTL_INSHORE_HAZARD + INTL_OFFSHORE_HAZARD,
                mean_depth_m=1200.0,
                outage_cost_per_day=4.0,  # ASSUMPTION: higher traffic per system
            )
        )
    return cables


# --------------------------------------------------------------------------
# The rest of the maintenance zone
# --------------------------------------------------------------------------
# CRITICAL. Taiwan does not have its own hull. Chunghwa Telecom belongs to two
# international maintenance ship zones, whose vessels also serve Japan, Korea,
# the Philippines, Vietnam, Malaysia, Singapore and Hong Kong. Taiwan's
# queueing therefore comes overwhelmingly from competition with *other
# countries'* faults, not from its own fault rate.
#
# Modelling Taiwan in isolation makes the queue non-binding and understates
# wait time by roughly an order of magnitude. The zone-level load is the whole
# point: it is why a country can do everything right domestically and still
# wait.
#
# Scale: Insikt/SubTel put the "AustralAsia" region at 36.3% of all publicised
# faults 2015-2024, the most fault-prone region in the world. Vietnam alone
# averages ~15 incidents a year across five systems.
REST_OF_ZONE_FAULTS_PER_YEAR = 45.0  # ASSUMPTION, order-of-magnitude from above

# Repair-capable hulls reachable by the zone serving Taiwan. Cariolle (2026)
# notes that of 77 cable ships only 22 are designed for repair, and SEAIOCMA
# alone covers roughly a third of the world's oceans. This is the zone fleet,
# NOT a Taiwanese asset: Taiwan owns no cable ship. Taiwan's disadvantage is
# expressed through `tier`, not through vessel scarcity.
#
# Calibration rule: pick N so that server utilisation sits in 0.70-0.85. Below
# that the queue never binds; above 1.0 it diverges. That the real system runs
# close to capacity is itself a result -- it is why a correlated shock such as
# the December 2025 landslide, which faulted six international systems in
# quick succession, produces a long tail rather than a blip.
N_ZONE_VESSELS = 4


def rest_of_zone_cables(
    n_systems: int = 30,
    tier: int = 2,
    faults_per_year: float = REST_OF_ZONE_FAULTS_PER_YEAR,
) -> list[Cable]:
    """Synthetic competing demand on the same hulls, outside Taiwan.

    These are not objects of interest; they exist to load the servers. Their
    tier matters a great deal, because it determines where Taiwan sits in the
    queue relative to everyone else.
    """
    km = 1000.0
    hazard = faults_per_year / (n_systems * km / 1000.0)
    return [
        Cable(
            cable_id=f"ROZ{i+1:02d}",
            label=f"rest-of-zone system {i+1}",
            zone="TW",
            km=km,
            tier=tier,
            has_backup=True,
            hazard_per_1000km_yr=hazard,
            mean_depth_m=900.0,
            outage_cost_per_day=0.0,   # not counted in Taiwanese welfare
        )
        for i in range(n_systems)
    ]


def yokohama_vessels(n: int = 2, transit_days_mean: float = 5.0) -> list[Vessel]:
    """Hulls serving Taiwan.

    Taiwan has no domestic cable ship. Chunghwa Telecom belongs to two
    international maintenance ship zones (MODA-114 Part 3), and repairs are
    executed by vessels dispatched from regional bases -- the January 2025
    TPE repair was a Yokohama-based response, and the vessel that repaired
    TM3 and TM2 in early 2025 arrived at Kaohsiung on 2 February 2025 and
    worked the faults in sequence.

    `n` is therefore *effective* standby capacity reachable by Taiwan, not a
    count of Taiwanese assets. It is the central policy lever.
    """
    return [
        Vessel(vessel_id=f"CS{i+1}", zone="TW", transit_days_mean=transit_days_mean)
        for i in range(n)
    ]


def taiwan_stock(
    domestic_tier: int = 3,
    intl_tier: int = 2,
    roz_tier: int = 2,
    domestic_backup: bool = True,
    n_roz: int = 30,
) -> list[Cable]:
    """Full server load: Taiwanese systems plus the rest of the zone.

    Default tiers encode the institutional reading. Taiwan's *domestic*
    cables are the junior claim: they are owned by one national carrier,
    they carry outlying-island traffic that has microwave and satellite
    backup, and MODA's stated forward plan is to seek priority dispatch
    mechanisms it does not yet have. International consortium systems
    landing in Taiwan sit alongside the rest of the zone at tier 2.
    """
    return (
        taiwan_cables(
            domestic_tier=domestic_tier,
            intl_tier=intl_tier,
            domestic_backup=domestic_backup,
        )
        + rest_of_zone_cables(n_systems=n_roz, tier=roz_tier)
    )


def baseline(**kw) -> Scenario:
    """Observed configuration: shared regional hulls, contract priority.

    Calibration target: SubTel Forum reports a mean restoration time of 40
    days in 2023, rising across 2015-2024. Taiwan's own documented cases
    bracket this widely -- the early-2025 TM2 break ran 26 days with most of
    it spent behind TM3 in the same vessel's work order, while TDM2's
    October 2025 partial fault carried an expected repair date thirteen
    months out.
    """
    params = dict(
        name="baseline",
        cables=taiwan_stock(),
        vessels=yokohama_vessels(n=N_ZONE_VESSELS),
        horizon_years=10.0,
        discipline="priority",
        service_median_days=9.0,
        planned_jobs_per_vessel_yr=0.0,
        seed=20260812,
    )
    params.update(kw)
    return Scenario(**params)


def utilisation(sc) -> dict:
    """Offered load / server capacity. Must be < 1 for a stable queue.

    Report this alongside every result. A simulation run above 1.0 is not a
    finding about repair capacity, it is a divergent queue.
    """
    demand_days = 0.0
    for c in sc.cables:
        sev_mult = 0.45 * sc.severity_service_multiplier + 0.55
        depth_mult = (c.mean_depth_m / 500.0) ** sc.depth_service_elasticity
        service = sc.service_median_days * sev_mult * depth_mult
        service /= max(1e-6, 1.0 - sc.weather_downtime_share)
        per_job = service + sc.mobilise_fixed_days + 4.0
        demand_days += c.annual_fault_rate * per_job
    n_rep = sum(1 for v in sc.vessels if v.repair_capable)
    demand_days += n_rep * sc.planned_jobs_per_vessel_yr * sc.planned_job_days
    capacity = n_rep * 365.25
    return {
        "annual_faults": sum(c.annual_fault_rate for c in sc.cables),
        "vessel_days_demanded": demand_days,
        "vessel_days_available": capacity,
        "utilisation": demand_days / capacity if capacity else float("inf"),
        "repair_vessels": n_rep,
    }
