#!/usr/bin/env python3
"""Run all experiments and write results to results/.

Usage:  python3 scripts/run_experiments.py [n_replications]
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import pandas as pd  # noqa: E402

from repairqueue import experiments as ex  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "results"
OUT.mkdir(exist_ok=True)

REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 30

TABLES = {
    "e0_stability": lambda: ex.e0_stability(),
    "e1_decomposition": lambda: ex.e1_decomposition(reps=REPS),
    "e2_priority_premium": lambda: ex.e2_priority_premium(reps=REPS),
    "e3_crowding_out": lambda: ex.e3_crowding_out(reps=REPS),
    "e4_redundancy": lambda: ex.e4_redundancy_moral_hazard(reps=REPS),
    "e5_discipline": lambda: ex.e5_discipline_comparison(reps=REPS),
}

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", 30)

if __name__ == "__main__":
    for name, fn in TABLES.items():
        df = fn()
        df.to_csv(OUT / f"{name}.csv", index=False)
        print(f"\n===== {name} " + "=" * max(0, 58 - len(name)))
        print(df.round(3).to_string(index=False))
    print(f"\nwrote {len(TABLES)} tables to {OUT}")
