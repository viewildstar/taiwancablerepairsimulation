# Data provenance and licensing

Two hand-coded event files. Neither contains any proprietary data, so a
replication package can be deposited publicly.

## `taiwan_faults.csv` (37 rows)

Coded from:

- **MODA-114** — Ministry of Digital Affairs, *114年度臺灣海底通訊電纜損害原因
  分析及策進報告*, public version, March 2026. Tables 4 (domestic, inside
  24nm), 5 (international, inside 24nm), 6 (beyond 24nm). **Month precision
  only** — see `date_precision`.
- **MODA-LIVE** — MODA "海纜障礙狀況" live fault table, snapshot 2026-08-11.
  Day precision, and uniquely includes an *expected repair date* per open
  fault, with a footnote attributing the estimate to cable-ship scheduling and
  sea conditions.
- MODA press releases and Chunghwa Telecom fault notices for day-level
  timestamps on the early-2025 sequence.

Licensing: the MODA site is marked **CC0, no rights reserved**; the cable map
layer is CC BY-SA 4.0 from TeleGeography. Redistribution is permitted.

### Known limitations
- FY111–113 exist only as **annual counts by cause** (MODA-114 Table 8:
  9, 11, 7, 7 faults inside 24nm). There is no earlier edition of the report —
  the FY114 report is the first, and MODA was only established 2022-08-27.
  Event-level detail before 2025 must be reconstructed from press releases.
- Restoration dates are sparse. Many events have a fault date and an expected
  repair date but no confirmed restoration. **Build interval censoring into
  the likelihood**; do not drop these rows.
- `severity` uses MODA's own distinction between partial core-fibre damage
  (部分芯線受損) and full break (斷纜). Use it; don't proxy it.

## `global_faults.csv` (33 rows)

Coded from Insikt Group / Recorded Future **TA-2025-0717** Appendix A,
"Publicly Reported Submarine Cable Damages (2024–2025)". Retained because the
appendix uniquely reports *intermediate* timestamps — vessel arrival, repair
start, restoration — plus a **stated cause of delay** where one was given.
That delay taxonomy (congestion, permitting, vessel mechanical failure,
physical access, conflict-zone refusal) is the comparison material for the
Taiwanese case.

Two worked examples of the wait/work decomposition:

| Cable | Fault | Vessel arrives | Restored | Days waiting | Days working |
|---|---|---|---|---|---|
| C-Lion1 | 2025-01-26 | 2025-03-10 | 2025-03-14 | 43 | 4 |
| Sweden–Latvia | 2025-01-26 | — (work starts 02-19) | 2025-02-28 | 24 | 9 |

Recorded Future's report is a third-party publication. Only dates and coded
facts are recorded here, not text: facts are not copyrightable, the expression
is. Cite the report; do not quote it at length.

## Not used

**GeoCable / OceanIQ** (Global Marine Group) is the industry fault database,
covering ~6,500 historical faults. It is *not* used, for two reasons: its
advertised fields are grid-aggregated fault **rates** (faults per km per year,
depth statistics, boundary attribution) with no restoration-duration variable,
and it is subscription-licensed, which would break the replication package.
The academic route to it is co-authorship rather than licensing — see Yeo,
Clare et al., *Int. J. Disaster Risk Reduction* (2026), whose 40-year,
5,113-fault database includes OceanIQ and ICPC staff as co-authors.
