"""
Charlie Cheng, Zhongtian Liu
CSE 163
Computes every table in the EDA report from the parsed reports (parse.py)
and the Census tables (acs.py), and writes them to outputs/. The tables
cover the dataset overviews (size, missing data, summaries), the four
research questions, and the checks on the assumptions of the planned
statistical tests.
"""

import math
import os

import numpy as np
import pandas as pd
import ruptures

PROCESSED = os.path.join("data", "processed")
CROSSWALK = os.path.join("data", "crosswalk.csv")
OUTPUTS = "outputs"

STATE = "Washington"
FIRST_YEAR = 2015
LAST_YEAR = 2026
# The state report prints months only from FY2021 on.
MONTHLY_YEARS = list(range(2021, LAST_YEAR + 1))
# The SIV report ends at FY2025.
LEDGER_YEARS = list(range(FIRST_YEAR, 2026))
LEDGER_NATIONALITIES = ["Afghanistan", "Iraq"]
# RQ1: a month needs this many arrivals to have a share vector, and a year
# needs this many such months for its noise level to be used.
MIN_MONTH_ARRIVALS = 20
MIN_USABLE_MONTHS = 6
TOP_SIZE = 5
# RQ2: permutation settings.
PERMUTATIONS = 1000
BLOCK_MONTHS = 6
SEED = 163
BREAKS = 3
POLICY_EVENTS = [
    ("2017-01", "Travel ban (EO 13769)"),
    ("2020-03", "COVID-19 suspension"),
    ("2021-08", "Afghanistan evacuation"),
    ("2022-04", "Uniting for Ukraine"),
    ("2025-01", "Admissions suspended (EO 14163)"),
]
PERIODS = {"FY2015-19": range(2015, 2020), "FY2021-22": range(2021, 2023),
           "FY2023-25": range(2023, 2026)}


def load_arrivals() -> pd.DataFrame:
    """
    Returns the tidy arrivals table (both reports, all years) written by
    parse.py, with the columns source, fiscal_year, state, nationality,
    month (1 = October ... 12 = September, 13 = annual total), count and
    printed_nationality.
    """
    return pd.read_csv(os.path.join(PROCESSED, "arrivals.csv"))


def load_region() -> pd.DataFrame:
    """
    Returns the region-by-month table written by parse.py, with the
    columns fiscal_year, region, month and count.
    """
    return pd.read_csv(os.path.join(PROCESSED, "region.csv"))


def calendar_date(fiscal_year: int, month: int) -> pd.Timestamp:
    """
    Returns the first day of the calendar month for fiscal month 'month'
    (1 = October) of the given fiscal year, which starts the October
    before: fiscal month 1 of FY2021 is October 2020.
    """
    year = fiscal_year - 1 if month <= 3 else fiscal_year
    return pd.Timestamp(year=year, month=(month + 8) % 12 + 1, day=1)


def overview(frame: pd.DataFrame, name: str, unit: str) -> dict:
    """
    Returns the size of one dataset as a dict: its name, what a row is
    (unit), the number of rows and columns, and the number and share of
    missing cells.
    """
    missing = int(frame.isna().sum().sum())
    return {"dataset": name, "row_is": unit, "rows": len(frame),
            "columns": frame.shape[1], "missing_cells": missing,
            "missing_share": missing / frame.size}


def month_coverage(arrivals: pd.DataFrame) -> pd.DataFrame:
    """
    Returns, for each report and fiscal year, how many of the 12 months
    are printed (0 for the FY2015-FY2020 refugee files, which give only
    the annual total), with the columns source, fiscal_year and months.
    """
    monthly = arrivals[arrivals["month"] <= 12]
    printed = monthly.groupby(["source", "fiscal_year"])["month"].nunique()
    years = arrivals[["source", "fiscal_year"]].drop_duplicates()
    table = years.merge(printed.rename("months").reset_index(),
                        on=["source", "fiscal_year"], how="left")
    table["months"] = table["months"].fillna(0).astype(int)
    return table.sort_values(["source", "fiscal_year"])


def seven_number(values: pd.Series) -> pd.Series:
    """
    Returns the seven-number summary of a quantitative series: mean,
    standard deviation, minimum, first quartile, median, third quartile
    and maximum.
    """
    summary = values.describe()
    return summary[["mean", "std", "min", "25%", "50%", "75%", "max"]]


def state_annual(arrivals: pd.DataFrame, source: str = "refugee",
                 state: str = STATE) -> pd.DataFrame:
    """
    Returns one state's annual arrivals in one report as a table with the
    columns fiscal_year, nationality and count.
    """
    keep = (arrivals["source"] == source) & (arrivals["state"] == state) & \
        (arrivals["month"] == 13)
    rows = arrivals[keep]
    return rows.groupby(["fiscal_year", "nationality"], as_index=False)[
        "count"].sum()


def top_nationalities(annual: pd.DataFrame,
                      size: int = TOP_SIZE) -> pd.DataFrame:
    """
    Returns the largest nationalities of each fiscal year in an annual
    table (from state_annual), with the columns fiscal_year, rank,
    nationality, count, share and year_total.
    """
    totals = annual.groupby("fiscal_year")["count"].transform("sum")
    table = annual.assign(share=annual["count"] / totals, year_total=totals)
    table = table.sort_values(["fiscal_year", "count"],
                              ascending=[True, False])
    table["rank"] = table.groupby("fiscal_year").cumcount() + 1
    table = table[table["rank"] <= size]
    return table[["fiscal_year", "rank", "nationality", "count", "share",
                  "year_total"]]


def share_table(annual: pd.DataFrame, threshold: int = 0) -> pd.DataFrame:
    """
    Returns each nationality's share of each year's arrivals, with one row
    per nationality and one column per fiscal year. Nationalities that
    never reach threshold arrivals in any year are left out before the
    shares are computed.
    """
    table = annual.pivot_table(index="nationality", columns="fiscal_year",
                               values="count", aggfunc="sum", fill_value=0)
    table = table[table.max(axis=1) >= threshold]
    return table / table.sum()


def l1_distance(one: pd.Series, other: pd.Series) -> float:
    """
    Returns the L1 distance between two share vectors (0 = identical mix,
    2 = no nationality in common). Missing nationalities count as 0.
    """
    one, other = one.align(other, fill_value=0)
    return float((one - other).abs().sum())


def js_distance(one: pd.Series, other: pd.Series) -> float:
    """
    Returns the Jensen-Shannon distance (base 2, between 0 and 1) between
    two share vectors. Missing nationalities count as 0.
    """
    one, other = one.align(other, fill_value=0)
    middle = (one + other) / 2
    total = 0.0
    for left, right, mid in zip(one, other, middle):
        if left > 0:
            total += 0.5 * left * math.log2(left / mid)
        if right > 0:
            total += 0.5 * right * math.log2(right / mid)
    return math.sqrt(max(total, 0.0))


METRICS = {"L1": l1_distance, "JS": js_distance}


def year_changes(annual: pd.DataFrame, metric: str = "L1",
                 threshold: int = 0) -> pd.DataFrame:
    """
    Returns the change in the nationality mix between each pair of
    consecutive fiscal years, with the columns from, to and change,
    measured with the named metric ('L1' or 'JS') on share_table(annual,
    threshold).
    """
    shares = share_table(annual, threshold)
    years = list(shares.columns)
    rows = []
    for before, after in zip(years, years[1:]):
        rows.append({"from": before, "to": after,
                     "change": METRICS[metric](shares[before],
                                               shares[after])})
    return pd.DataFrame(rows)


def change_settings(annual: pd.DataFrame) -> pd.DataFrame:
    """
    Returns the largest year-over-year change under each of the four
    planned settings (L1 or JS distance, crossed with all nationalities or
    only those with at least 5 arrivals in some year), with the columns
    setting, from, to and change.
    """
    rows = []
    for metric in METRICS:
        for threshold in (0, 5):
            changes = year_changes(annual, metric, threshold)
            best = changes.loc[changes["change"].idxmax()]
            label = "all" if threshold == 0 else ">= 5"
            rows.append({"setting": metric + " / " + label,
                         "from": int(best["from"]), "to": int(best["to"]),
                         "change": best["change"]})
    return pd.DataFrame(rows)


def state_monthly_detail(arrivals: pd.DataFrame,
                         state: str = STATE) -> pd.DataFrame:
    """
    Returns one state's monthly refugee arrivals by nationality for the
    years that print months, with the columns fiscal_year, month,
    nationality and count.
    """
    keep = (arrivals["source"] == "refugee") & \
        (arrivals["state"] == state) & (arrivals["month"] <= 12)
    rows = arrivals[keep]
    return rows.groupby(["fiscal_year", "month", "nationality"],
                        as_index=False)["count"].sum()


def within_year_noise(detail: pd.DataFrame,
                      metric: str = "L1") -> pd.DataFrame:
    """
    Returns the month-to-month noise in the nationality mix inside each
    fiscal year of a monthly table (from state_monthly_detail): the median
    distance between the share vectors of consecutive months, using only
    months with at least MIN_MONTH_ARRIVALS arrivals. The columns are
    fiscal_year, months_used, median_distance and usable (at least
    MIN_USABLE_MONTHS months).
    """
    rows = []
    for year, block in detail.groupby("fiscal_year"):
        table = block.pivot_table(index="nationality", columns="month",
                                  values="count", aggfunc="sum",
                                  fill_value=0)
        table = table.loc[:, table.sum() >= MIN_MONTH_ARRIVALS]
        shares = table / table.sum()
        months = list(shares.columns)
        distances = [METRICS[metric](shares[first], shares[second])
                     for first, second in zip(months, months[1:])
                     if second - first == 1]
        rows.append({"fiscal_year": year, "months_used": len(months),
                     "median_distance": float(np.median(distances))
                     if distances else float("nan"),
                     "usable": len(months) >= MIN_USABLE_MONTHS})
    return pd.DataFrame(rows)


def change_against_noise(changes: pd.DataFrame,
                         noise: pd.DataFrame) -> pd.DataFrame:
    """
    Returns the year-over-year changes (from year_changes) with the noise
    level of the later year and their ratio r = change / noise; the ratio
    is missing where that year has no usable monthly noise level.
    """
    usable = noise[noise["usable"]][["fiscal_year", "median_distance"]]
    table = changes.merge(usable, left_on="to", right_on="fiscal_year",
                          how="left").drop(columns="fiscal_year")
    table["ratio"] = table["change"] / table["median_distance"]
    return table


def pair_permutation(detail: pd.DataFrame, before: int, after: int,
                     metric: str = "L1",
                     permutations: int = PERMUTATIONS) -> dict:
    """
    Returns a permutation test of whether the nationality mix of fiscal
    year 'after' differs from 'before' more than shuffling months between
    the two years would produce. The months of both years are pooled and
    randomly re-split into two groups of the same sizes; the statistic is
    the distance between the two groups' pooled share vectors. Returns the
    observed statistic, the p-value and the number of months used.
    """
    table = detail[detail["fiscal_year"].isin([before, after])]
    table = table.assign(key=table["fiscal_year"] * 100 + table["month"])
    counts = table.pivot_table(index="nationality", columns="key",
                               values="count", aggfunc="sum", fill_value=0)
    keys = np.array(counts.columns)
    first = keys // 100 == before

    def statistic(mask: np.ndarray) -> float:
        one = counts.loc[:, mask].sum(axis=1)
        other = counts.loc[:, ~mask].sum(axis=1)
        return METRICS[metric](one / one.sum(), other / other.sum())

    observed = statistic(first)
    generator = np.random.default_rng(SEED)
    exceed = 0
    for _ in range(permutations):
        if statistic(generator.permutation(first)) >= observed:
            exceed += 1
    return {"from": before, "to": after, "statistic": observed,
            "p_value": (exceed + 1) / (permutations + 1),
            "months": len(keys)}


def national_monthly(region: pd.DataFrame) -> pd.DataFrame:
    """
    Returns the national monthly refugee arrivals for every month from
    FY2015 to FY2026 (the region report's national row), with the columns
    fiscal_year, month, date and arrivals.
    """
    rows = region[(region["region"] == "Total") & (region["month"] <= 12)]
    table = rows[["fiscal_year", "month", "count"]].rename(
        columns={"count": "arrivals"}).copy()
    table["date"] = [calendar_date(year, month) for year, month
                     in zip(table["fiscal_year"], table["month"])]
    return table.sort_values("date").reset_index(drop=True)


def state_monthly(arrivals: pd.DataFrame, state: str = STATE) -> pd.DataFrame:
    """
    Returns one state's monthly refugee arrivals for every month of the
    years that print months (months with no arrivals are 0), with the
    columns fiscal_year, month, date and arrivals.
    """
    detail = state_monthly_detail(arrivals, state)
    totals = detail.groupby(["fiscal_year", "month"])["count"].sum()
    grid = pd.MultiIndex.from_product([MONTHLY_YEARS, range(1, 13)],
                                      names=["fiscal_year", "month"])
    table = totals.reindex(grid, fill_value=0).rename("arrivals")
    table = table.reset_index()
    table["date"] = [calendar_date(year, month) for year, month
                     in zip(table["fiscal_year"], table["month"])]
    return table


def largest_drops(series: pd.DataFrame, size: int = 5) -> pd.DataFrame:
    """
    Returns the largest month-over-month drops in a monthly series (from
    national_monthly or state_monthly), with the columns date, before,
    arrivals, drop (people) and drop_share (drop as a share of the month
    before), largest drop in people first.
    """
    table = series[["date", "arrivals"]].copy()
    table["before"] = table["arrivals"].shift(1)
    table["drop"] = table["before"] - table["arrivals"]
    table["drop_share"] = table["drop"] / table["before"]
    table = table.dropna().sort_values("drop", ascending=False)
    return table.head(size)[["date", "before", "arrivals", "drop",
                             "drop_share"]]


def split_gain(values: np.ndarray) -> tuple[int, float]:
    """
    Returns the best single change point of a series in mean and how much
    it lowers the sum of squared deviations (the L2 cost used by binary
    segmentation): the index where the second segment starts, and the
    cost reduction.
    """
    total = len(values)
    cumulative = np.cumsum(values)
    squares = np.cumsum(values ** 2)
    whole = squares[-1] - cumulative[-1] ** 2 / total
    best_index, best_gain = 1, -1.0
    for split in range(1, total):
        left = squares[split - 1] - cumulative[split - 1] ** 2 / split
        right_sum = cumulative[-1] - cumulative[split - 1]
        right = (squares[-1] - squares[split - 1]) - \
            right_sum ** 2 / (total - split)
        gain = whole - left - right
        if gain > best_gain:
            best_index, best_gain = split, gain
    return best_index, float(best_gain)


def break_dates(series: pd.DataFrame, breaks: int = BREAKS) -> list:
    """
    Returns the dates of the first month of each new segment that binary
    segmentation (L2 cost, ruptures) finds in a monthly series, for the
    given number of breaks.
    """
    signal = series["arrivals"].to_numpy(dtype=float)
    model = ruptures.Binseg(model="l2", min_size=2, jump=1).fit(signal)
    ends = model.predict(n_bkps=breaks)[:-1]
    return [series["date"].iloc[end] for end in ends]


def lag_one_autocorrelation(values: np.ndarray) -> float:
    """
    Returns the lag-1 autocorrelation of a series.
    """
    centred = values - values.mean()
    return float((centred[1:] * centred[:-1]).sum() / (centred ** 2).sum())


def segment_residuals(series: pd.DataFrame,
                      breaks: int = BREAKS) -> np.ndarray:
    """
    Returns a monthly series minus the mean of the segment each month
    falls in, using the segments binary segmentation finds.
    """
    signal = series["arrivals"].to_numpy(dtype=float)
    model = ruptures.Binseg(model="l2", min_size=2, jump=1).fit(signal)
    ends = model.predict(n_bkps=breaks)
    residuals = signal.copy()
    start = 0
    for end in ends:
        residuals[start:end] -= signal[start:end].mean()
        start = end
    return residuals


def break_permutation(series: pd.DataFrame, block: int = 1,
                      permutations: int = PERMUTATIONS) -> dict:
    """
    Returns a max-statistic permutation test for a change in mean in a
    monthly series. The statistic is the cost reduction of the best single
    split; on every shuffled series the split is searched again, so the
    test accounts for the break's location being estimated. With block > 1
    the series is cut into blocks of that many months and the blocks are
    shuffled, which keeps short-range dependence inside each block.
    Returns the break date, the statistic and the p-value.
    """
    values = series["arrivals"].to_numpy(dtype=float)
    index, observed = split_gain(values)
    pieces = [values[start:start + block]
              for start in range(0, len(values), block)]
    generator = np.random.default_rng(SEED)
    exceed = 0
    for _ in range(permutations):
        order = generator.permutation(len(pieces))
        shuffled = np.concatenate([pieces[i] for i in order])
        if split_gain(shuffled)[1] >= observed:
            exceed += 1
    return {"break": series["date"].iloc[index].strftime("%Y-%m"),
            "statistic": observed,
            "p_value": (exceed + 1) / (permutations + 1), "block": block}


def event_gaps(dates: list) -> pd.DataFrame:
    """
    Returns, for each break date, the nearest policy event in
    POLICY_EVENTS and the gap in months (break minus event), with the
    columns break, event, event_month and gap_months.
    """
    rows = []
    for date in dates:
        gaps = []
        for month, name in POLICY_EVENTS:
            event = pd.Timestamp(month + "-01")
            gap = (date.year - event.year) * 12 + date.month - event.month
            gaps.append((abs(gap), gap, name, month))
        _, gap, name, month = min(gaps)
        rows.append({"break": date.strftime("%Y-%m"), "event": name,
                     "event_month": month, "gap_months": gap})
    return pd.DataFrame(rows)


def tier(language: str, label: str) -> str:
    """
    Returns how an ACS category label shows a language: 'own' if the
    category is that language (the label is the language, possibly with
    '(incl. ...)' after it), 'shared' if the label names the language
    alongside others, and 'residual' if the label does not name it.
    """
    if label == language or label.startswith(language + " (incl."):
        return "own"
    if language in label:
        return "shared"
    return "residual"


def crosswalk_tiers(crosswalk: pd.DataFrame) -> pd.DataFrame:
    """
    Returns the crosswalk with a tier column for the state table (B16001)
    and the county table (C16001).
    """
    table = crosswalk.copy()
    table["b16001_tier"] = [tier(language, label) for language, label
                            in zip(table["language"],
                                   table["b16001_category"])]
    table["c16001_tier"] = [tier(language, label) for language, label
                            in zip(table["language"],
                                   table["c16001_category"])]
    return table


def visibility(annual: pd.DataFrame, crosswalk: pd.DataFrame,
               level: str = "b16001") -> pd.DataFrame:
    """
    Returns, for each fiscal year, the share of arrivals by how the ACS
    table at the given level ('b16001' state or 'c16001' county) shows
    their main language (own, shared, residual, or not in the crosswalk),
    plus two bounds on the share it can see: pessimistic (the main
    language has its own category) and optimistic (any common language
    does).
    """
    tiers = crosswalk_tiers(crosswalk)
    column = level + "_tier"
    main = tiers[tiers["role"] == "main"].set_index("nationality")[column]
    any_own = tiers.groupby("nationality")[column].apply(
        lambda values: "own" in set(values))
    table = annual.copy()
    table["tier"] = table["nationality"].map(main).fillna("not in crosswalk")
    table["any_own"] = table["nationality"].map(any_own).fillna(False)
    totals = table.groupby("fiscal_year")["count"].sum()
    shares = table.pivot_table(index="fiscal_year", columns="tier",
                               values="count", aggfunc="sum", fill_value=0)
    shares = shares.div(totals, axis=0)
    pessimistic = table[table["tier"] == "own"].groupby(
        "fiscal_year")["count"].sum()
    optimistic = table[table["any_own"].astype(bool)].groupby(
        "fiscal_year")["count"].sum()
    shares["pessimistic_visible"] = pessimistic.reindex(
        totals.index, fill_value=0) / totals
    shares["optimistic_visible"] = optimistic.reindex(
        totals.index, fill_value=0) / totals
    shares["arrivals"] = totals
    return shares.reset_index()


def acs_estimates(table: pd.DataFrame, categories: list) -> pd.DataFrame:
    """
    Returns the estimate and margin of error of each named language
    category in one row of an ACS language table (B16001 or C16001), with
    the columns category, estimate, margin and share (of the population
    aged 5 and over).
    """
    total = float(table["Estimate!!Total:"].iloc[0])
    rows = []
    for category in categories:
        name = "Estimate!!Total:!!" + category + ":"
        margin = name.replace("Estimate", "Margin of Error", 1)
        estimate = float(table[name].iloc[0])
        rows.append({"category": category, "estimate": estimate,
                     "margin": float(table[margin].iloc[0]),
                     "share": estimate / total})
    return pd.DataFrame(rows)


def county_estimates(counties: pd.DataFrame, category: str,
                     size: int = 10) -> pd.DataFrame:
    """
    Returns the counties with the largest estimate for one C16001 language
    category, with the columns county, estimate and margin, largest first.
    """
    name = "Estimate!!Total:!!" + category + ":"
    margin = name.replace("Estimate", "Margin of Error", 1)
    table = pd.DataFrame({
        "county": counties["NAME"].str.replace(" County, Washington", ""),
        "estimate": counties[name].astype(float),
        "margin": counties[margin].astype(float)})
    return table.sort_values("estimate", ascending=False).head(size)


def birth_estimates(birth: pd.DataFrame, country: str,
                    size: int = 5) -> pd.DataFrame:
    """
    Returns the counties with the most residents born in one country
    (B05006), with the columns county, country, estimate and margin.
    """
    names = [column for column in birth.columns
             if column.startswith("Estimate") and
             column.rstrip(":").endswith("!!" + country)]
    name = names[0]
    margin = name.replace("Estimate", "Margin of Error", 1)
    table = pd.DataFrame({
        "county": birth["NAME"].str.replace(" County, Washington", ""),
        "country": country, "estimate": birth[name].astype(float),
        "margin": birth[margin].astype(float)})
    return table.sort_values("estimate", ascending=False).head(size)


def two_ledgers(arrivals: pd.DataFrame) -> pd.DataFrame:
    """
    Returns the outer join of the refugee and SIV reports on state,
    nationality and fiscal year (annual totals, FY2015-FY2025), with the
    columns state, nationality, fiscal_year, refugee, siv and in_report
    ('both', 'refugee only' or 'SIV only'). A count missing on one side
    means the row is absent from that report, so it is 0 there.
    """
    annual = arrivals[(arrivals["month"] == 13) &
                      (arrivals["fiscal_year"].isin(LEDGER_YEARS))]
    keys = ["state", "nationality", "fiscal_year"]
    refugee = annual[annual["source"] == "refugee"].groupby(keys)[
        "count"].sum().rename("refugee").reset_index()
    siv = annual[annual["source"] == "siv"].groupby(keys)[
        "count"].sum().rename("siv").reset_index()
    merged = refugee.merge(siv, on=keys, how="outer", indicator=True)
    labels = {"both": "both", "left_only": "refugee only",
              "right_only": "SIV only"}
    merged["in_report"] = merged["_merge"].astype(str).map(labels)
    merged[["refugee", "siv"]] = merged[["refugee", "siv"]].fillna(0)
    return merged.drop(columns="_merge")


def siv_share(ledger: pd.DataFrame, state: str = STATE) -> pd.DataFrame:
    """
    Returns, for each ledger nationality and fiscal year in one state, the
    arrivals in each report, their sum (recorded) and the share recorded
    only in the SIV report.
    """
    rows = ledger[(ledger["state"] == state) &
                  (ledger["nationality"].isin(LEDGER_NATIONALITIES))]
    grid = pd.MultiIndex.from_product([LEDGER_NATIONALITIES, LEDGER_YEARS],
                                      names=["nationality", "fiscal_year"])
    table = rows.set_index(["nationality", "fiscal_year"])[
        ["refugee", "siv"]].reindex(grid, fill_value=0).reset_index()
    table["recorded"] = table["refugee"] + table["siv"]
    table["siv_share"] = table["siv"] / table["recorded"]
    return table


def period_shares(shares: pd.DataFrame) -> pd.DataFrame:
    """
    Returns the pooled SIV share (total SIV over total recorded) for each
    nationality in each period of PERIODS.
    """
    rows = []
    for name, years in PERIODS.items():
        block = shares[shares["fiscal_year"].isin(years)]
        sums = block.groupby("nationality")[["siv", "recorded"]].sum()
        for nationality, row in sums.iterrows():
            rows.append({"period": name, "nationality": nationality,
                         "siv": row["siv"], "recorded": row["recorded"],
                         "siv_share": row["siv"] / row["recorded"]})
    return pd.DataFrame(rows)


def category_summary(arrivals: pd.DataFrame, column: str) -> pd.DataFrame:
    """
    Returns every value of a categorical column of the Washington refugee
    arrivals with its arrivals (annual totals, all years), largest first.
    """
    rows = arrivals[(arrivals["source"] == "refugee") &
                    (arrivals["state"] == STATE) & (arrivals["month"] == 13)]
    table = rows.groupby(column)["count"].sum().sort_values(ascending=False)
    return table.rename("arrivals").reset_index()


def save(table: pd.DataFrame, name: str) -> None:
    """
    Writes a table to outputs/ as name.csv.
    """
    table.to_csv(os.path.join(OUTPUTS, name + ".csv"), index=False)


def main():
    os.makedirs(OUTPUTS, exist_ok=True)
    arrivals = load_arrivals()
    region = load_region()
    crosswalk = pd.read_csv(CROSSWALK)
    acs_state = pd.read_csv(os.path.join(PROCESSED, "acs_state.csv"))
    counties = pd.read_csv(os.path.join(PROCESSED, "acs_counties.csv"))
    birth = pd.read_csv(os.path.join(PROCESSED, "acs_birth.csv"))
    pd.set_option("display.width", 160)

    sizes = [overview(arrivals[arrivals["source"] == "refugee"],
                      "A refugee arrivals", "state x nationality x FY x "
                      "month (13 = year total)"),
             overview(arrivals[arrivals["source"] == "siv"],
                      "B SIV arrivals", "nationality x state x FY x month"),
             overview(acs_state, "C1 ACS B16001 (state)", "state"),
             overview(counties, "C2 ACS C16001 (counties)", "county"),
             overview(birth, "C3 ACS B05006 (counties)", "county"),
             overview(region, "D region by month", "region x FY x month")]
    save(pd.DataFrame(sizes), "dataset_sizes")
    save(month_coverage(arrivals), "month_coverage")
    acs_codes = pd.DataFrame({
        "table": ["B16001", "C16001", "B05006"],
        "negative_codes": [int((frame.select_dtypes("number") < 0).sum()
                               .sum()) for frame in (acs_state, counties,
                                                     birth)]})
    save(acs_codes, "acs_annotation_codes")

    annual = state_annual(arrivals)
    totals = annual.groupby("fiscal_year")["count"].sum()
    save(totals.rename("arrivals").reset_index(), "wa_annual")
    summary = pd.DataFrame({
        "WA refugee arrivals per FY": seven_number(totals),
        "WA SIV arrivals per FY": seven_number(
            state_annual(arrivals, "siv").groupby("fiscal_year")[
                "count"].sum()),
        "National monthly arrivals": seven_number(
            national_monthly(region)["arrivals"]),
        "WA monthly arrivals (FY2021-26)": seven_number(
            state_monthly(arrivals)["arrivals"])})
    save(summary.reset_index().rename(columns={"index": "statistic"}),
         "seven_number")
    save(category_summary(arrivals, "nationality"), "wa_nationalities")
    save(top_nationalities(annual), "wa_top5")
    print(totals.to_string())

    changes = year_changes(annual)
    detail = state_monthly_detail(arrivals)
    noise = within_year_noise(detail)
    save(change_against_noise(changes, noise), "rq1_change_vs_noise")
    save(change_settings(annual), "rq1_settings")
    save(pd.concat([within_year_noise(detail, metric).assign(metric=metric)
                    for metric in METRICS]), "rq1_noise")
    tests = [pair_permutation(detail, year, year + 1)
             for year in MONTHLY_YEARS[:-1]]
    save(pd.DataFrame(tests), "rq1_permutation")
    print(change_against_noise(changes, noise).round(3).to_string())

    nation = national_monthly(region)
    wa_months = state_monthly(arrivals)
    save(nation, "national_monthly")
    save(wa_months, "wa_monthly")
    save(largest_drops(nation), "rq2_national_drops")
    save(largest_drops(wa_months), "rq2_wa_drops")
    checks = []
    for name, series in (("national", nation), ("Washington", wa_months)):
        values = series["arrivals"].to_numpy(dtype=float)
        dates = break_dates(series)
        for block in (1, BLOCK_MONTHS):
            result = break_permutation(series, block)
            result["series"] = name
            result["breaks"] = ", ".join(d.strftime("%Y-%m") for d in dates)
            result["raw_lag1"] = lag_one_autocorrelation(values)
            result["residual_lag1"] = lag_one_autocorrelation(
                segment_residuals(series))
            checks.append(result)
        save(event_gaps(dates).assign(series=name),
             "rq2_event_gaps_" + name.lower())
    save(pd.DataFrame(checks), "rq2_breaks")
    print(pd.DataFrame(checks).to_string())

    save(crosswalk_tiers(crosswalk), "crosswalk_tiers")
    save(visibility(annual, crosswalk, "b16001"), "rq3_visibility_state")
    save(visibility(annual, crosswalk, "c16001"), "rq3_visibility_county")
    categories = ["Arabic", "Persian (incl. Farsi, Dari)",
                  "Ukrainian or other Slavic languages", "Russian",
                  "Amharic, Somali, or other Afro-Asiatic languages",
                  "Other languages of Asia",
                  "Swahili or other languages of Central, Eastern, and "
                  "Southern Africa", "Other Indo-European languages",
                  "Other and unspecified languages"]
    save(acs_estimates(acs_state, categories), "rq3_acs_state")
    save(pd.concat([county_estimates(counties, category).assign(
        category=category) for category in
        ["Other and unspecified languages",
         "Other Asian and Pacific Island languages",
         "Russian, Polish, or other Slavic languages"]]), "rq3_counties")
    save(pd.concat([birth_estimates(birth, country) for country in
                    ("Afghanistan", "Iraq")]), "rq4_birth_counties")

    ledger = two_ledgers(arrivals)
    save(ledger["in_report"].value_counts().rename("rows").reset_index(),
         "rq4_join_counts")
    shares = siv_share(ledger)
    save(shares, "rq4_siv_share")
    save(period_shares(shares), "rq4_periods")
    print(period_shares(shares).round(3).to_string())


if __name__ == "__main__":
    main()
