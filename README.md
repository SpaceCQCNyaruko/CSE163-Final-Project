# Two Ledgers, One Population — CSE 163 final project

Exploratory data analysis of refugee arrivals to Washington State
(FY2015–FY2026), combining three public sources: the Refugee Processing
Center's arrivals and SIV reports and the Census Bureau's 2024 five-year
American Community Survey estimates.

## Run

```bash
pip install -r requirements.txt
python src/main.py
```

`src/main.py` parses the raw files in `Dataset/`, pulls the Census tables
(needs `Dataset/American_Community_Survey_5-year_Estimates(2024)/ACSKEY.txt`),
writes the tables to `outputs/`, and renders the figures to `figures/`.

## Test

```bash
python test_project.py
```

## Report

`eda.pdf` is generated from `build_eda_docx.py` (python-docx) and the tables
in `outputs/`.

## Layout

- `src/parse.py` — coordinate-based parser for the Excel and PDF reports,
  with the reconciliation checks.
- `src/acs.py` — Census API pull for B16001, C16001 and B05006.
- `src/analysis.py` — every table quoted in the report.
- `src/figures.py` — the seven figures.
- `data/crosswalk.csv` — nationality → language → ACS category, with tier.
- `data/processed/` — tidy tables and the parse reconciliation.
