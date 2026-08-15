"""Submarine cable repair as a rationed queue.

`engine` holds the simulator, `calibration` the Taiwan Strait parameters and
`experiments` the tables the paper turns on.

Note on naming: `engine` exports a function called `simulate`, which is
re-exported below. The module must therefore never be renamed to
`simulate.py` -- the re-export would shadow it and `import
repairqueue.simulate` would resolve to the function rather than the module.
"""

from .calibration import (
    baseline,
    taiwan_cables,
    taiwan_stock,
    utilisation,
    yokohama_vessels,
)
from .engine import Cable, Job, Scenario, Vessel, replicate, simulate

__all__ = [
    "Cable",
    "Vessel",
    "Job",
    "Scenario",
    "simulate",
    "replicate",
    "baseline",
    "taiwan_cables",
    "taiwan_stock",
    "yokohama_vessels",
    "utilisation",
]
