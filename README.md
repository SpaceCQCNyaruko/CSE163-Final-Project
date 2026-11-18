# Two Ledgers, One Population — CSE 163 final project

Exploratory data analysis of refugee arrivals to Washington State
(FY2015–FY2026), combining the Refugee Processing Center's arrivals, SIV and
region-by-month reports with the Census Bureau's 2024 five-year American
Community Survey estimates.

## Run

```bash
pip install -r requirements.txt
python src/main.py          # parse, analyse, draw figures
python test_project.py      # 23 tests
```

`src/main.py` re-runs OCR (`src/ocr.py`, about ten minutes) only if
`data/ocr/` is missing, and the Census download (`src/acs.py`, needs
`Dataset/American_Community_Survey_5-year_Estimates(2024)/ACSKEY.txt`) only
if the ACS tables in `data/processed/` are missing.

## Layout

- `eda.pdf` — the Part 2 EDA report.
- `Dataset/` — the published files, under the publisher's names, plus the
  Census language code list used for the crosswalk.
- `src/ocr.py` — recovers the three image-only tables: FY2022 arrivals
  (scanned pages, read cell by cell), FY2024 arrivals (scrambled Type3 fonts,
  decoded by OCR voting) and the FY2024 region report (a picture).
- `src/parse.py` — rebuilds every table from word positions, runs the
  reconciliation checks, standardizes nationality names.
- `src/acs.py` — Census API pull for B16001, C16001 and B05006.
- `src/analysis.py` — every table in the report (`outputs/`).
- `src/figures.py` — the seven figures (`figures/`).
- `data/crosswalk.csv` — nationality → language → Census code → B16001 and
  C16001 category, with the source for each row.
- `data/ocr/` — raw OCR output (strings as read).
- `data/processed/` — tidy tables: `arrivals.csv`, `region.csv`,
  `checks.csv` (one row of reconciliation checks per report), `repairs.csv`
  (cells filled from their row sum), `nationality_map.csv`.

## Data notes

- The FY2015–FY2020 state files give annual totals only; monthly state data
  starts in FY2021. The national monthly series (region report) covers all
  144 months.
- Every report reconciles exactly with its printed totals; the FY2018 region
  file (regenerated in 2020) counts 26 more arrivals than the FY2018 state
  file.
