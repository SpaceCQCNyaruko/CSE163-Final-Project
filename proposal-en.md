# Two Ledgers, One Population: How Administrative Categories Shape the Count of Refugee Arrivals in Washington State, FY2015–FY2026

**Authors:** Charlie Cheng, Zhongtian Liu
CSE 163, Autumn 2026

---

## 1. Summary of Research Questions

1. **Who arrives?** For each fiscal year from FY2015 to FY2026, how many refugees were
   resettled in Washington State, and which five nationalities made up the largest
   shares? In which fiscal year did the mix of nationalities change most compared with
   the year before, and is that change larger than the ordinary month-to-month variation
   within a year?
2. **When does it stop?** In which months did Washington's monthly refugee arrivals
   drop sharply, and which drop was the largest? How many months separate each of those
   drops from the nearest documented federal policy event (for example, the January 2017
   travel ban, the March 2020 COVID-19 suspension, the August 2021 Afghanistan evacuation,
   and the January 2025 suspension of admissions)?
3. **Who does the count miss?** What share of refugees who arrived in Washington in
   FY2015–FY2026 came from nationalities whose main language has no category of its own
   in the Census Bureau's language tables? Which nationalities are they, and in which
   Washington counties are the Census categories that absorb those languages most
   concentrated?
4. **Two ledgers.** For Afghan and Iraqi arrivals to Washington, what share appears only
   in the Special Immigrant Visa (SIV) report rather than the refugee arrivals report?
   How did that share change around the 2021 evacuation (FY2021–FY2022) compared with
   FY2015–FY2019?

---

## 2. Motivation

Resettlement agencies in King County plan language support, housing, and job services
for a population that changes with federal policy, not with gradual demographic trends.
Planning starts from three questions: who is arriving, from where, and how many. Our
starting observation is that the last question has no single answer in the public
record.

The national FY2025 refugee arrivals report shows why. It records 38,102 arrivals for
the year, but only 2 in February, 14 in March, and 41 in April. February through
September together account for 506 arrivals, or 1.3% of the year. An organization
reading only the annual total would plan for arrivals that had effectively stopped.

The difficulty runs deeper because arrivals are recorded by **legal status**, not by
who people are. Refugee, SIV holder, asylee, and humanitarian parolee are
administrative categories, and each determines which report, if any, a person appears
in. Afghan and Iraqi arrivals are split across two separately published reports, so
"how many Afghans arrived in Washington" has two different correct answers depending on
which file you open. Afghans who entered on humanitarian parole after 2021 appear in
neither report.

The reports themselves record changes in how the data is defined. A footnote in the
FY2025 file says the destination fields were updated to use "Actual Destination City"
and "Actual Destination State." The FY2025 PDF we downloaded is stamped *"Data as of
11/18/2025,"* even though its file name says "as of 30 Sep 2025." The same URL can
return different numbers at different times.

Our contribution is not another trend line. We **measure how much these administrative
choices change the answer**, and we state the denominator behind every number. This is
the provenance question named in Strand C: discontinuities in a refugee time series
often reflect policy events rather than changes in the underlying population.

---

## 3. Dataset

All sources are public, free, and aggregate. **We use no individual-level or client
records.** No dataset in this project was used in a CSE 163 assignment or demo. The ACS
language and place-of-birth tables below are different data from the tract-level food
access data in the Mapping assignment, and we do not use that assignment's shapefile.

**A. Refugee Arrivals by State and Nationality, FY2015–FY2026.** U.S. State Department,
Refugee Processing Center (RPC). Columns: resettlement state, nationality, one column
per month (October–September), and a Grand Total.

- Archive page (every file below is linked from here): https://www.rpc.state.gov/archives/
- Download rule: take the base `https://www.rpc.state.gov/documents/` and append one file
  name from the table below. Spaces in a file name become `%20` in a URL, and the
  FY2015–FY2020 files sit under an extra `Archives/` directory.
- One complete, working example (paste into a browser; it downloads the FY2025 PDF):
  `https://www.rpc.state.gov/documents/FY%202025%20Arrivals%20by%20State%20and%20Nationality%20as%20of%2030%20Sep%202025.pdf`

| FY | File name (append to the base URL) |
|---|---|
| 2026 | `FY 2026 Arrivals by State and Nationality as of 30 Sep 2026.pdf` |
| 2025 | `FY 2025 Arrivals by State and Nationality as of 30 Sep 2025.pdf` |
| 2024 | `FY 2024 Arrivals by State and Nationality as of 30 Oct 2024_updated.pdf` |
| 2023 | `FY 2023 Refugee Arrivals by State and Nationality as of 30 Sep 2023.pdf` |
| 2022 | `FY 2022 Arrivals by State and Nationality as of 30 Sep 2022.pdf` |
| 2021 | `FY 2021 Arrivals by State and Nationality as of 30 Sep 2021.pdf` |
| 2020 | `Archives/FY 2020 Arrivals by State and Nationality.xlsx` |
| 2019 | `Archives/FY 2019 Arrivals by State and Nationality.xlsx` |
| 2018 | `Archives/FY 2018 Arrivals by State and Nationality.xls` |
| 2017 | `Archives/FY 2017 Arrivals by State and Nationality.xls` |
| 2016 | `Archives/FY 2016 Arrivals by State and Nationality.xls` |
| 2015 | `Archives/FY 2015 Arrivals by State and Nationality.xls` |

The names look irregular because the agency's naming is irregular, not because of typos on
our side: FY2023 alone contains the word "Refugee"; FY2024 is stamped "30 Oct" and
suffixed `_updated`; and the file format changes three times. Our code therefore uses an
explicit year-to-filename map rather than a generated pattern. FY2026 is also published on
the Admissions & Arrivals page as `Refugee Arrivals by State and Nationality as of
September 30, 2026.pdf`; we check that the two files agree.

**B. SIV Arrivals by Nationality and State, FY2015–FY2026.** PDFs from the same base URL.
FY2015–FY2025 are the combined "Amerasian & SIV" reports. FY2026 is split into two
separate files on the Admissions & Arrivals page (https://www.rpc.state.gov/admissions-and-arrivals/):
an Amerasian report and a SIV report. Because the report boundaries and the file naming
change in FY2026, that year is a seam we check explicitly.

| FY | File name (append to the base URL) |
|---|---|
| 2026 | `SIV Arrivals by Nationality and State as of September 30, 2026.pdf` (Admissions & Arrivals page) |
| 2025 | `FY 2025 Amerasian & SIV Arrivals by Nationality and State.pdf` |
| 2024 | `FY 2024 Amerasian & SIV Arrivals by Nationality and State_updated_2025_01_14.pdf` |
| 2023 | `FY 2023 Amerasian & SIV Arrivals by Nationality and State.pdf` |
| 2022 | `FY 2022 Amerasian & SIV Arrivals by Nationality and State.pdf` |
| 2021 | `FY2021 Amerasian & SIV Arrivals by Nationality and State.pdf` |
| 2020 | `FY2020 Amerasian & SIV Arrivals by Nationality and State.pdf` |
| 2019 | `FY2019 Amerasian & SIV Arrivals by Nationality and State.pdf` |
| 2018 | `FY2018 Amerasian & SIV Arrivals by Nationality and State.pdf` |
| 2017 | `FY2017 Amerasian & SIV Arrivals by Nationality and State.pdf` |
| 2016 | `FY2016 Amerasian & SIV Arrivals by Nationality and State.pdf` |
| 2015 | `FY2015 Amerasian & SIV Arrivals by Nationality and State.pdf` |

(There is no space after "FY" in FY2015–FY2021 and a space from FY2022 on — another
mid-series change, handled by the same explicit map.)

**C. American Community Survey (ACS) 5-year estimates, 2024.** U.S. Census Bureau,
through the Census Data API (free key: https://api.census.gov/data/key_signup.html).
We use estimates **and** their margins of error.

- `B16001`: detailed language spoken at home, Washington State. Data query:
  `https://api.census.gov/data/2024/acs/acs5?get=NAME,B16001_001E,B16001_105E,B16001_111E&for=state:53&key=YOUR_KEY`
  (variable IDs and labels: https://api.census.gov/data/2024/acs/acs5/groups/B16001.html)
- `C16001`: language spoken at home (12 categories), all 39 Washington counties. Data query:
  `https://api.census.gov/data/2024/acs/acs5?get=NAME,C16001_001E&for=county:*&in=state:53&key=YOUR_KEY`
  (variable IDs and labels: https://api.census.gov/data/2024/acs/acs5/groups/C16001.html)
- `B05006`: place of birth of the foreign-born population, Washington counties. Data query:
  `https://api.census.gov/data/2024/acs/acs5?get=NAME,B05006_001E&for=county:*&in=state:53&key=YOUR_KEY`
  (variable IDs and labels: https://api.census.gov/data/2024/acs/acs5/groups/B05006.html)

**D. Refugee Arrivals by Region, Fiscal Year by Month, FY2021–FY2026.** Same RPC
archive page, same base URL; PDFs. These are the same years in which A is a PDF, where
parsing errors are most likely. We use D only to check our parsed national monthly totals
from A.

| FY | File name (append to the base URL) |
|---|---|
| 2026 | `FY 2026 Arrivals by Region - Fiscal Year by Month as of 30 Sep 2026.pdf` |
| 2025 | `FY 2025 Arrivals by Region - Fiscal Year by Month as of 30 Sep 2025.pdf` |
| 2024 | `FY 2024 Arrivals by Region - Fiscal Year by Month as of 30 Sep 2024.pdf` |
| 2023 | `Refugee Arrivals by Region - Fiscal Year by Month as of 30 Sep 2023.pdf` |
| 2022 | `Refugee Arrivals by Region - Fiscal Year by Month as of 30 Sep 2022.pdf` |
| 2021 | `Refugee Arrivals by Region - Fiscal Year by Month as of 30 Sep 2021.pdf` |

**Reproducibility.** RPC revises files without notice. For example, the FY2024 file
carries an `_updated` suffix. We will save a snapshot of every file with its download
date and report which version we parsed.

**Stock vs. flow.** ACS counts (C) are a *stock*: everyone currently living in a county,
across all arrival years and immigration statuses. RPC counts (A, B) are a *flow*: one
year of arrivals, recorded by the state of initial resettlement. We never add, subtract,
or divide one by the other. ACS describes where communities speaking these languages
live today. It does not tell us where refugees were resettled.

**No manual cleaning.** All extraction and cleaning is done by our Python code. The
nationality → language → ACS category crosswalk is a version-controlled CSV loaded by
the code. Each row records the ACS variable ID and label it relies on, so anyone can
check every assignment.

---

## 4. Challenge Goals

**Messy Data.** Source A comes in three formats across twelve years: `.xls` for
FY2015–FY2018, `.xlsx` for FY2019–FY2020, and PDF for FY2021–FY2026. Source B is PDF
throughout. These PDFs were exported from Tableau, and our first parsing probe already
showed what that means:

- `pdfplumber.extract_table()` returns a grid in which one cell holds a state name plus
  a newline-separated list of all its nationalities, while the matching numeric rows
  have empty label columns.
- Labels and numbers sit on two text layers that share line spacing but have different
  y-origins.
- Each page also carries a second band of numeric rows in addition to its own table
  rows. Summing both inflated the national total in our first parse by about 22%
  (46,425 against the 38,102 printed in the file).

No five-line conversion produces a **usable** table here: `extract_table()` does return a
70 × 15 grid, but the labels that make the grid interpretable come out on a different
layer, so the rows cannot be attributed. We will write a parser for each format and
rebuild the labels for every numeric row. Every parse must pass three checks or fail
loudly:

1. Each row's 12 monthly values sum to its Grand Total.
2. All rows sum to the national total printed in the file.
3. National monthly totals match source D, where D is available.

**We never drop a row to make a check pass.** With merged cells, a failing row is often
the label row for a whole group of nationalities.

**Result Validity.** Arrival counts are a complete administrative record, not a sample,
so we do **not** use sampling confidence intervals for them. Instead, each test targets
a real source of uncertainty in this data:

- **Noise vs. real change (RQ1).** We compare each year-over-year composition change
  with the month-to-month variation inside the same year.
- **Breakpoints (RQ2).** We use a max-statistic permutation test. The breakpoint is
  re-estimated on every shuffled series, because the breakpoint's location is itself
  estimated from the data.
- **Positive control (RQ2).** The detector must find the known early-2025 collapse in
  the national series without being told where it is.
- **Sensitivity to our own choices (RQ1, RQ3).** We repeat each analysis under
  alternative reasonable settings, and we test the crosswalk with nationalities whose
  answer we already know.

ACS figures *are* sample estimates, so we report every ACS number as estimate ± margin
of error.

**Multiple Datasets.** We combine three separately published sources: the refugee
arrivals report (A), the SIV report (B), and the Census Bureau's ACS tables (C), plus the
regional report (D) as a third-party check on A. RQ3 combines A with C, merging arrivals
by nationality onto ACS language counts through our crosswalk. RQ4 merges A with B on
`state` + `nationality` using an outer join. RQ1 and RQ2 use D to verify A's parsed
national totals. This meets the goal's minimums: at least three datasets used together,
at least two research questions that each draw on more than one source, and at least one
join between datasets.

**Software.** We will use `pdfplumber` (PDF tables), `ruptures` (change-point
detection), and `scipy.stats` (permutation tests and distance measures), in addition to
pandas, matplotlib/seaborn, and `requests`.

---

## 5. Method

**Shared first step.** Parse every A and B file into one tidy table with the columns
`state`, `nationality`, `fiscal_year`, `month`, `count`, using the checks described
under Messy Data. Standardize nationality names (for example, "Burma" and "Myanmar")
with a documented mapping.

### RQ1: Who arrives?
1. Filter to `state == "Washington"` and sum arrivals by nationality and fiscal year.
   For each year, report the total and the top five nationalities with their counts and
   shares.
2. For each year `t`, build the share vector `p_t`, which is each nationality's share of
   that year's arrivals. Then compute the year-over-year change
   `d_t = Σ |p_t(n) − p_{t−1}(n)|`, which ranges from 0 to 2.
3. Compute the within-year noise level `m_t`: the median distance between the share
   vectors of consecutive months in year `t`. Only months with at least 20 Washington
   arrivals are used, because a month with zero arrivals has no share vector. A year
   with fewer than six such months is flagged, and its `m_t` is not used. Report
   `r_t = d_t / m_t`.
4. Repeat steps 2–3 under four settings: L1 or Jensen–Shannon distance, crossed with
   including all nationalities or only those with at least 5 arrivals.

**Leads to a conclusion:** If the year with the largest change is the same in at least
3 of the 4 settings and its `r_t > 3`, we name it the turning-point year and report
which nationalities rose and fell, and by how many people. Otherwise we report the
candidate years instead of a single answer. Years with very low totals, such as FY2025
after February and FY2026, are described but not named as turning points.

### RQ2: When does it stop?
1. Build two monthly series for FY2015–FY2026 (144 months): Washington, and the
   national total across all states.
2. Report the largest month-over-month drops, in both number of people and percent.
3. Estimate change points with `ruptures`, using binary segmentation with an L2 cost.
4. Assess significance with 1,000 permutations, re-estimating the breakpoint on each
   shuffled series, and take the maximum statistic as the null distribution. Shuffling
   ignores the order of months, so we will also report results when 6-month blocks are
   shuffled instead of individual months.
5. Build a table of policy event dates with sources: the January 2017 travel ban, the
   March 2020 COVID-19 suspension, the August 2021 Afghanistan evacuation, the April
   2022 Uniting for Ukraine parole program, and the January 2025 suspension. Report the
   gap in months between each breakpoint and its nearest event.

**Leads to a conclusion:** A breakpoint that passes the permutation test, with the
positive control recovered, is reported with its month gap to the nearest event. We
describe timing only and claim no causal effect. If a breakpoint is not significant, we
say the series does not support it.

### RQ3: Who does the count miss?
1. Take the 10 nationalities with the most Washington arrivals over FY2015–FY2026.
2. Build the crosswalk from each nationality to its main language and other common
   languages, then from each language to an ACS category. Classify each language into
   one of three tiers, separately for B16001 (state) and C16001 (county):
   - **Own category.** For example, Arabic is `B16001_105E` "Arabic."
   - **Shared category.** The language is counted together with others, even when the
     label names it. For example, Somali and Amharic are both in `B16001_111E`
     "Amharic, Somali, or other Afro-Asiatic languages." Dari is in `B16001_042E`
     "Persian (incl. Farsi, Dari)." Ukrainian is in `B16001_036E` "Ukrainian or other
     Slavic languages."
   - **Residual.** The language is absorbed into an unnamed catch-all category, such as
     "Other Indo-European languages" or "Other and unspecified languages."

   At the county level, C16001 has only 12 categories, so many of these languages drop
   a tier. For example, Somali falls into "Other and unspecified languages." For
   languages that no label names (Tigrinya, Pashto, Burmese, Karen, Kinyarwanda), we
   assign the category using the Census Bureau's published language code list, not our
   own judgment.
3. Compute two bounds:
   - **Optimistic:** a nationality is visible if *any* of its common languages has its
     own category.
   - **Pessimistic:** a nationality is visible only if its *main* language does.
4. **Check the crosswalk with a known answer.** Arabic-speaking nationalities, such as
   Iraqi, Syrian, and Sudanese, must come out as visible. If they don't, the crosswalk
   is wrong and we fix it before reporting anything.
5. **Geography.** From C16001, report each county's count (± margin of error) for the
   categories that absorb the missed languages. At the county level these languages
   fall into broad categories such as "Other and unspecified languages," so the counts
   include speakers of many other languages. We report them as an upper bound on where
   these communities could live, not as counts of the communities themselves.

**Leads to a conclusion:** We report the share of arrivals that is invisible as a range
[pessimistic, optimistic], the nationalities in that range with their counts, and a
table of the counties where the absorbing categories are largest. If the range crosses
50%, we write "about half," not "most."

### RQ4: Two ledgers
1. Sum A to `(state, nationality, fiscal_year, count_refugee)` and B to
   `(state, nationality, fiscal_year, count_siv)`.
2. Merge them on `state` + `nationality` + `fiscal_year` with an **outer join** and
   `indicator=True`. An inner join would drop exactly the rows that appear in only one
   report.
3. For Afghanistan and Iraq in Washington, compute
   `missed_by_refugee_report = count_siv / (count_refugee + count_siv)` for each year.
4. Compare FY2021–FY2022 with FY2015–FY2019, and report FY2023–FY2026 alongside. From B05006, report the Washington
   counties with the largest Afghan-born and Iraqi-born populations, as background only.

**Leads to a conclusion:** A clear rise in the SIV share in FY2021–FY2022 means that,
for Afghans, the refugee report alone increasingly undercounts the arrivals that were
recorded. No change is also a finding. **Limitation:** parolees and asylees appear in
neither report, so every share is a share *of recorded arrivals*, not of everyone who
arrived.

### Code testing (separate from validity)
Unit tests check the parsers and the crosswalk loader. They test row sums, column
counts, and values we hand-checked on sample pages. These tests are not part of our
Result Validity claim.

---

## 6. Work Plan

| # | Task | Hours |
|---|---|---|
| 1 | Set up the environment and acquire data: install packages; download, snapshot, and date all A, B, and D files; get a Census API key and pull C | 5 |
| 2 | Write parsers for the three formats (PDF, `.xlsx`, `.xls`), rebuild labels, and implement the three checks | 16 |
| 3 | Build the nationality and language crosswalk, the merges, and the county aggregation; check match rates | 9 |
| 4 | Run the four analyses and the validity tests; make figures | 12 |
| 5 | Write unit tests, the report, and the presentation | 10 |
| | **Total** | **52** |

**Division of work.** Charlie Cheng leads tasks 1–2, getting the data and rebuilding it
correctly. Zhongtian Liu leads tasks 3–4, the analysis. We share task 5. The lead on each
task writes the code, and the other member reviews it before it is merged. If either of
us is stuck on a task for more than 24 hours, the other takes over half of it rather
than the whole task.

**Workflow.** We develop locally in VS Code with Python 3.12, writing scripts rather
than notebooks so we can handle files of any size. Code lives in a shared GitHub
repository with one branch per task. Every change goes through a pull request reviewed
by the other member, and we meet twice a week to go through open PRs and re-check the
schedule.

**Environment status.** Python 3.12, pandas, pdfplumber, ruptures, scipy, requests, and
pytest are installed locally. A first probe on the FY2025 arrivals PDF read all 15 pages.
`extract_table()` on page 1 returned a 70 × 15 grid with the collapsed labels described
above, which confirms both that the setup works and what the parsing challenge is.
