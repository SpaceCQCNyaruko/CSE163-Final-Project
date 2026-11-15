"""Compute the EDA tables behind the report.

Every number in the report comes from this module: Washington's yearly
arrivals and their composition, the monthly series, the two-ledger
comparison with the SIV report, and the language-category analysis built on
the ACS tables. Results are written to ``outputs/`` so the report and the
tests can both read them.
"""

import os

import pandas as pd

PROCESSED = os.path.join("data", "processed")
OUTPUTS = "outputs"

# Refugee years whose Washington rows reconcile with the totals printed in the
# source file (or, for the Excel years, with the published national totals).
# FY2022 and FY2024 are scanned image / broken-font files; FY2026 has no usable
# state breakdown because its single-page PDF packs state and nationality into
# one column. See the report's data-quality section.
USABLE = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2023, 2025]
SIV_USABLE = [2015, 2017, 2018, 2019, 2020]
MONTHLY_YEARS = [2021, 2023, 2025]
MONTH_LABELS = [
    "Oct", "Nov", "Dec", "Jan", "Feb", "Mar",
    "Apr", "May", "Jun", "Jul", "Aug", "Sep",
]


def load_arrivals():
    """Read the parsed arrivals tables."""
    annual = pd.read_csv(os.path.join(PROCESSED, "arrivals_annual.csv"))
    monthly = pd.read_csv(os.path.join(PROCESSED, "arrivals_monthly.csv"))
    return annual, monthly


def find_column(frame, keyword, exclude=()):
    """Return the column whose name matches the keyword.

    An exact name wins; otherwise the keyword must match exactly one column.
    """
    exact = [
        name for name in frame.columns
        if name.lower().strip() == keyword.lower().strip()
    ]
    if len(exact) == 1:
        return exact[0]
    hits = [
        name for name in frame.columns
        if keyword.lower() in name.lower()
        and not any(bad.lower() in name.lower() for bad in exclude)
    ]
    if len(hits) != 1:
        raise ValueError("column {} matched {} columns".format(
            keyword, len(hits)))
    return hits[0]


def washington(annual):
    """Washington refugee arrivals, one row per year and nationality."""
    rows = annual[
        (annual["source"] == "refugee")
        & (annual["state"] == "Washington")
        & (annual["fiscal_year"].isin(USABLE))
    ]
    return rows[["fiscal_year", "nationality", "count"]].copy()


def top_table(wa, size=5):
    """Top nationalities per year with counts and shares."""
    totals = wa.groupby("fiscal_year")["count"].sum()
    rows = []
    for year, block in wa.groupby("fiscal_year"):
        ranked = block.sort_values("count", ascending=False).head(size)
        for rank, (_, row) in enumerate(ranked.iterrows(), start=1):
            rows.append(
                {
                    "fiscal_year": year,
                    "rank": rank,
                    "nationality": row["nationality"],
                    "count": row["count"],
                    "share": row["count"] / totals[year],
                    "year_total": totals[year],
                }
            )
    return pd.DataFrame(rows)


def composition_change(wa):
    """Year-over-year L1 change in the nationality mix."""
    shares = (
        wa.pivot_table(
            index="nationality", columns="fiscal_year",
            values="count", aggfunc="sum",
        )
        .fillna(0)
    )
    shares = shares / shares.sum()
    rows = []
    years = [year for year in USABLE if year in shares.columns]
    for before, after in zip(years, years[1:]):
        delta = (shares[after] - shares[before]).abs().sum()
        rows.append(
            {
                "from": before,
                "to": after,
                "gap_years": after - before,
                "l1_change": delta,
                "arrivals_from": int(shares[before].sum() * 0 + 1),
            }
        )
    return pd.DataFrame(rows), shares


def monthly_series(monthly):
    """Washington and national monthly arrivals for the parsed years."""
    rows = monthly[
        (monthly["source"] == "refugee")
        & (monthly["fiscal_year"].isin(MONTHLY_YEARS))
    ]
    state = rows[rows["state"] == "Washington"]
    national = rows.groupby(["fiscal_year", "month"])["count"].sum()
    wash = state.groupby(["fiscal_year", "month"])["count"].sum()
    frame = pd.DataFrame(
        {"washington": wash, "national": national}
    ).fillna(0).reset_index()
    frame["label"] = [
        "{} {}".format(MONTH_LABELS[int(m) - 1], int(y))
        for y, m in zip(frame["fiscal_year"], frame["month"])
    ]
    return frame


def two_ledgers(annual):
    """Afghan and Iraqi arrivals in Washington, by report."""
    frame = annual[
        (annual["state"] == "Washington")
        & (annual["nationality"].isin(["Afghanistan", "Iraq"]))
        & (annual["fiscal_year"].isin(SIV_USABLE))
    ]
    table = frame.pivot_table(
        index=["nationality", "fiscal_year"], columns="source",
        values="count", aggfunc="sum",
    ).fillna(0)
    table = table.reset_index()
    if "siv" not in table.columns:
        table["siv"] = 0
    if "refugee" not in table.columns:
        table["refugee"] = 0
    table["recorded"] = table["siv"] + table["refugee"]
    table["siv_share"] = table["siv"] / table["recorded"]
    return table


def language_shares(wa, crosswalk):
    """Share of Washington arrivals by how the ACS names their language."""
    merged = wa.merge(
        crosswalk[["nationality", "language", "tier"]],
        on="nationality", how="left",
    )
    merged["tier"] = merged["tier"].fillna("not in crosswalk")
    table = merged.groupby(["fiscal_year", "tier"])["count"].sum()
    table = table.unstack(fill_value=0)
    table = table.div(table.sum(axis=1), axis=0)
    return table


def find_category(frame, keyword):
    """Return the single ACS column whose last label part matches."""
    keyword = keyword.lower()
    exact = []
    loose = []
    for name in frame.columns:
        if not name.startswith("Estimate"):
            continue
        last = name.split("!!")[-1].rstrip(":").lower()
        if last == keyword:
            exact.append(name)
        elif keyword in last and "speak english" not in last:
            loose.append(name)
    if len(exact) == 1:
        return exact[0]
    if len(loose) == 1:
        return loose[0]
    raise ValueError("category {} matched {} columns".format(
        keyword, len(exact) + len(loose)))


def acs_category(state, keyword):
    """Estimate and margin of error for one ACS language category."""
    name = find_category(state, keyword)
    total_name = find_column(state, "Estimate!!Total:")
    margin = name.replace("Estimate", "Margin of Error", 1)
    estimate = float(state[name].iloc[0])
    error = float(state[margin].iloc[0]) if margin in state.columns else 0.0
    return {
        "category": name.split("!!")[-1].rstrip(":"),
        "estimate": estimate,
        "margin": error,
        "share_of_population": estimate / float(state[total_name].iloc[0]),
    }


def county_table(counties, keyword, size=8):
    """Counties ranked by one C16001 category, with margins of error."""
    name = find_category(counties, keyword)
    margin = name.replace("Estimate", "Margin of Error", 1)
    total = find_column(counties, "Estimate!!Total:")
    frame = pd.DataFrame(
        {
            "county": counties[total].index.map(
                lambda i: counties.loc[i, "NAME"]
                if "NAME" in counties.columns else str(i)
            ),
            "estimate": counties[name].astype(float).values,
            "margin": counties[margin].astype(float).values,
        }
    )
    frame = frame.sort_values("estimate", ascending=False).head(size)
    return frame


def main():
    """Build every EDA table and print the headline numbers."""
    os.makedirs(OUTPUTS, exist_ok=True)
    annual, monthly = load_arrivals()
    wa = washington(annual)
    crosswalk = pd.read_csv(os.path.join("data", "crosswalk.csv"))

    totals = wa.groupby("fiscal_year")["count"].sum()
    totals.to_frame("arrivals").to_csv(
        os.path.join(OUTPUTS, "wa_annual.csv")
    )
    print("Washington arrivals by year")
    print(totals.to_string())

    top = top_table(wa)
    top.to_csv(os.path.join(OUTPUTS, "wa_top5.csv"), index=False)
    print("\nLargest nationality by year")
    first = top[top["rank"] == 1][["fiscal_year", "nationality", "share"]]
    print(first.to_string(index=False))

    change, shares = composition_change(wa)
    change.to_csv(os.path.join(OUTPUTS, "wa_change.csv"), index=False)
    print("\nYear-over-year L1 composition change")
    print(change.to_string(index=False))

    series = monthly_series(monthly)
    series.to_csv(os.path.join(OUTPUTS, "wa_monthly.csv"), index=False)
    print("\nMonthly series", series.shape)
    peak = series.sort_values("washington", ascending=False).head(3)
    print(peak[["label", "washington", "national"]].to_string(index=False))

    ledger = two_ledgers(annual)
    ledger.to_csv(os.path.join(OUTPUTS, "two_ledgers.csv"), index=False)
    print("\nTwo ledgers (Washington)")
    print(ledger.to_string(index=False))

    tiers = language_shares(wa, crosswalk)
    tiers.to_csv(os.path.join(OUTPUTS, "language_tiers.csv"))
    print("\nLanguage tiers by year")
    print(tiers.round(3).to_string())

    state = pd.read_csv(os.path.join(PROCESSED, "acs_state.csv"))
    counties = pd.read_csv(os.path.join(PROCESSED, "acs_counties.csv"))
    for keyword in ("Arabic", "Other and unspecified"):
        print("\nACS state category", keyword)
        print(acs_category(state, keyword))
    county = county_table(counties, "Other and unspecified")
    county.to_csv(os.path.join(OUTPUTS, "county_residual.csv"), index=False)
    print(county.to_string(index=False))


if __name__ == "__main__":
    main()
