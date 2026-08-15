import pathlib
import sys
import unittest
from dataclasses import replace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import repairqueue.engine as sim
from repairqueue.calibration import baseline, utilisation, yokohama_vessels


class TestSimulate(unittest.TestCase):
    def test_runs_and_is_ordered(self):
        df = sim.simulate(baseline(horizon_years=5.0))
        self.assertGreater(len(df), 0)
        self.assertTrue((df["wait_days"] >= -1e-9).all(), "negative wait")
        self.assertTrue((df["duration_days"] > 0).all(), "non-positive duration")

    def test_duration_identity(self):
        df = sim.simulate(baseline(horizon_years=5.0))
        recomposed = df["wait_days"] + df["transit_days"] + df["service_days"]
        self.assertTrue(
            ((recomposed - df["duration_days"]).abs() < 1e-6).all(),
            "duration must equal wait + transit + service",
        )

    def test_no_vessel_double_booked(self):
        df = sim.simulate(baseline(horizon_years=5.0))
        for vid, g in df.groupby("vessel_id"):
            g = g.sort_values("t_arrive")
            starts = g["t_arrive"] + g["wait_days"] + g["transit_days"]
            ends = starts + g["service_days"]
            # a hull is occupied from assignment to restore
            occ = sorted(zip(g["t_arrive"] + g["wait_days"], ends))
            for (s1, e1), (s2, e2) in zip(occ, occ[1:]):
                self.assertLessEqual(e1 - 1e-6, s2, f"{vid} double-booked")

    def test_more_hulls_never_lengthens_waits(self):
        small = sim.replicate(baseline(vessels=yokohama_vessels(4), horizon_years=6.0), 6)
        big = sim.replicate(baseline(vessels=yokohama_vessels(10), horizon_years=6.0), 6)
        self.assertLess(big["wait_days"].mean(), small["wait_days"].mean())

    def test_priority_helps_senior_tier(self):
        from repairqueue.calibration import rest_of_zone_cables, taiwan_cables
        cables = [
            replace(c, tier=1 if i % 2 == 0 else 3)
            for i, c in enumerate(taiwan_cables())
        ] + rest_of_zone_cables(tier=2)
        df = sim.replicate(baseline(cables=cables, horizon_years=6.0), 8)
        df = df[~df["cable_id"].str.startswith("ROZ")]
        senior = df.loc[df["tier"] == 1, "wait_days"].mean()
        junior = df.loc[df["tier"] == 3, "wait_days"].mean()
        self.assertLess(senior, junior, "seniority must reduce wait")

    def test_baseline_is_stable(self):
        u = utilisation(baseline())
        self.assertLess(u["utilisation"], 1.0, "baseline queue diverges")
        self.assertGreater(u["utilisation"], 0.5, "baseline queue never binds")


if __name__ == "__main__":
    unittest.main()
