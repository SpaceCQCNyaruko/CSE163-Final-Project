"""
Charlie Cheng, Zhongtian Liu
CSE 163
Draws the EDA figures from the tables in outputs/ and saves them as PNG
files in figures/. Captions are written in the report; each figure's title
names what is plotted.
"""

import os

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker
import pandas as pd

import analysis

matplotlib.use("Agg")

OUTPUTS = "outputs"
FIGURES = "figures"
PROCESSED = os.path.join("data", "processed")
# Categorical slots in their fixed, colorblind-checked order, then gray for
# 'Other'. Ordinal blues for the language tiers (most visible = darkest).
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300",
          "#6250d6"]
OTHER = "#b4b2a9"
TIERS = {"own": "#0d366b", "shared": "#1c5cab", "residual": "#86b6ef",
         "not in crosswalk": OTHER}
INK = "#52514e"
GRID = "#e6e5e1"
SHADE = "#f1f0ec"
WIDTH = 6.5
TOP_SERIES = 7


def setup() -> None:
    """
    Creates the figures folder and applies one quiet style to every
    figure: light grid behind the data, no top or right frame.
    """
    os.makedirs(FIGURES, exist_ok=True)
    plt.rcParams.update({
        "figure.dpi": 200, "font.size": 8.5, "axes.titlesize": 9.5,
        "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": INK, "axes.labelcolor": INK,
        "xtick.color": INK, "ytick.color": INK, "axes.grid": True,
        "axes.grid.axis": "y", "grid.color": GRID, "axes.axisbelow": True,
        "legend.frameon": False, "lines.linewidth": 1.4})


def read(name: str) -> pd.DataFrame:
    """
    Returns the table outputs/name.csv.
    """
    return pd.read_csv(os.path.join(OUTPUTS, name + ".csv"))


def save(figure: plt.Figure, name: str) -> None:
    """
    Saves a figure as figures/name.png and closes it.
    """
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, name + ".png"))
    plt.close(figure)


def mark_events(axes: plt.Axes, label: bool) -> None:
    """
    Draws a dashed vertical line at each policy event, numbered 1-5 above
    the plot when label is True (the caption names the events; some are
    only months apart, so names would collide).
    """
    for number, (month, _) in enumerate(analysis.POLICY_EVENTS, start=1):
        date = pd.Timestamp(month + "-01")
        axes.axvline(date, color=INK, linestyle=(0, (3, 3)), linewidth=0.7)
        if label:
            axes.annotate(str(number), (date, 1.0),
                          xycoords=("data", "axes fraction"),
                          xytext=(0, 2), textcoords="offset points",
                          fontsize=7, color=INK, ha="center", va="bottom")


def monthly_series() -> None:
    """
    Two aligned panels: national monthly arrivals FY2015-FY2026 from the
    region report, and Washington's monthly arrivals, which exist only
    from FY2021; the FY2015-FY2020 span is shaded as annual-only.
    """
    nation = read("national_monthly")
    state = read("wa_monthly")
    for table in (nation, state):
        table["date"] = pd.to_datetime(table["date"])
    figure, (top, bottom) = plt.subplots(2, 1, figsize=(WIDTH, 4.4),
                                         sharex=True)
    top.plot(nation["date"], nation["arrivals"], color=SERIES[0])
    top.set_title("National refugee arrivals per month, FY2015-FY2026",
                  pad=14)
    top.set_ylabel("Arrivals")
    mark_events(top, True)
    bottom.plot(state["date"], state["arrivals"], color=SERIES[1])
    start = analysis.calendar_date(analysis.FIRST_YEAR, 1)
    end = analysis.calendar_date(analysis.MONTHLY_YEARS[0], 1)
    bottom.axvspan(start, end, color=SHADE, zorder=0)
    bottom.text(start + (end - start) / 2, 0.5, "FY2015-FY2020: state "
                "report gives annual totals only", transform=bottom.
                get_xaxis_transform(), ha="center", va="center",
                color=INK, fontsize=7.5)
    bottom.set_title("Washington refugee arrivals per month, FY2021-FY2026")
    bottom.set_ylabel("Arrivals")
    mark_events(bottom, False)
    save(figure, "f1_monthly")


def composition() -> None:
    """
    Stacked bars of each fiscal year's nationality mix in Washington: the
    seven largest nationalities over all years, the rest as 'Other', with
    the year's total above each bar.
    """
    arrivals = analysis.load_arrivals()
    annual = analysis.state_annual(arrivals)
    shares = analysis.share_table(annual)
    leaders = annual.groupby("nationality")["count"].sum().sort_values(
        ascending=False).head(TOP_SERIES).index.tolist()
    years = list(shares.columns)
    totals = annual.groupby("fiscal_year")["count"].sum()
    figure, axes = plt.subplots(figsize=(WIDTH, 3.0))
    bottom = pd.Series(0.0, index=years)
    labels = [str(year) for year in years]
    rows = [(name, shares.loc[name], colour)
            for name, colour in zip(leaders, SERIES)]
    rows.append(("Other", shares.drop(index=leaders).sum(), OTHER))
    for name, values, colour in rows:
        axes.bar(labels, values, bottom=bottom, color=colour, width=0.72,
                 edgecolor="white", linewidth=0.8, label=name)
        bottom = bottom + values
    others = shares.drop(index=leaders)
    for label, year in zip(labels, years):
        axes.text(label, 1.02, "{:,}".format(int(totals[year])),
                  ha="center", va="bottom", fontsize=6.8, color=INK)
        # Name a single nationality that makes up most of a year's 'Other'.
        biggest = others[year].idxmax()
        if others[year].max() > 0.5:
            axes.text(label, 1 - others[year].max() / 2, biggest,
                      rotation=90, ha="center", va="center", fontsize=7,
                      color="white")
    axes.set_ylim(0, 1.1)
    axes.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    axes.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    axes.set_ylabel("Share of the year's arrivals")
    axes.set_title("Washington refugee arrivals by nationality (number "
                   "above bar = year total)")
    axes.legend(ncol=1, fontsize=7, loc="center left",
                bbox_to_anchor=(1.0, 0.5))
    save(figure, "f2_composition")


def ledgers() -> None:
    """
    Two panels, Afghanistan and Iraq: Washington arrivals per fiscal year
    stacked by the report that records them (refugee or SIV).
    """
    shares = read("rq4_siv_share")
    figure, panels = plt.subplots(1, 2, figsize=(WIDTH, 2.6))
    for axes, nationality in zip(panels, analysis.LEDGER_NATIONALITIES):
        block = shares[shares["nationality"] == nationality]
        labels = [str(year)[2:] for year in block["fiscal_year"]]
        axes.bar(labels, block["refugee"], color=SERIES[0], width=0.72,
                 label="Refugee report")
        axes.bar(labels, block["siv"], bottom=block["refugee"],
                 color=SERIES[1], width=0.72, edgecolor="white",
                 linewidth=0.8, label="SIV report")
        axes.set_title(nationality)
        axes.set_xlabel("Fiscal year (20xx)")
    panels[0].set_ylabel("Recorded arrivals")
    panels[0].legend(loc="upper left", fontsize=7)
    figure.suptitle("Afghan and Iraqi arrivals to Washington by the report "
                    "that records them", x=0.01, ha="left",
                    fontsize=9.5, fontweight="bold")
    save(figure, "f3_ledgers")


def siv_share() -> None:
    """
    The share of recorded Afghan and Iraqi arrivals in Washington that
    appears only in the SIV report, per fiscal year, with the comparison
    periods shaded.
    """
    shares = read("rq4_siv_share")
    figure, axes = plt.subplots(figsize=(WIDTH, 2.5))
    for (name, years), shade in zip(analysis.PERIODS.items(),
                                    [SHADE, "#e4e2dc", SHADE]):
        axes.axvspan(min(years) - 0.4, max(years) + 0.4, color=shade,
                     zorder=0)
        axes.text((min(years) + max(years)) / 2, 1.04, name, ha="center",
                  fontsize=7, color=INK)
    for nationality, colour in zip(analysis.LEDGER_NATIONALITIES, SERIES):
        block = shares[shares["nationality"] == nationality]
        axes.plot(block["fiscal_year"], block["siv_share"], color=colour,
                  marker="o", markersize=4, label=nationality)
        last = block.iloc[-1]
        axes.annotate(nationality, (last["fiscal_year"], last["siv_share"]),
                      xytext=(6, 0), textcoords="offset points",
                      va="center", fontsize=7.5, color=INK)
    axes.set_ylim(0, 1.12)
    axes.set_xlim(2014.5, 2026.2)
    axes.set_xticks(analysis.LEDGER_YEARS)
    axes.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    axes.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    axes.set_ylabel("Share in SIV report only")
    axes.set_title("Share of recorded arrivals to Washington found only in "
                   "the SIV report", pad=12)
    axes.legend(loc="center", bbox_to_anchor=(0.8, 0.5), fontsize=7)
    save(figure, "f4_siv_share")


def language_tiers() -> None:
    """
    Two panels, state table (B16001) and county table (C16001): the share
    of each year's Washington arrivals by how the ACS shows their main
    language (own category, shared, residual, or not in the crosswalk).
    """
    figure, panels = plt.subplots(1, 2, figsize=(WIDTH, 2.8), sharey=True)
    for axes, (name, title) in zip(panels, [
            ("rq3_visibility_state", "State table B16001 (42 groups)"),
            ("rq3_visibility_county", "County table C16001 (12 groups)")]):
        table = read(name)
        labels = [str(year)[2:] for year in table["fiscal_year"]]
        bottom = pd.Series(0.0, index=table.index)
        for tier, colour in TIERS.items():
            values = table[tier] if tier in table.columns else 0 * bottom
            axes.bar(labels, values, bottom=bottom, color=colour,
                     width=0.75, edgecolor="white", linewidth=0.6,
                     label=tier)
            bottom = bottom + values
        axes.set_title(title)
        axes.set_xlabel("Fiscal year (20xx)")
        axes.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        axes.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    panels[0].set_ylabel("Share of arrivals (main language)")
    handles, names = panels[0].get_legend_handles_labels()
    figure.legend(handles, names, ncol=4, loc="lower center", fontsize=7,
                  bbox_to_anchor=(0.5, -0.01))
    figure.tight_layout(rect=(0, 0.07, 1, 1))
    figure.savefig(os.path.join(FIGURES, "f5_tiers.png"))
    plt.close(figure)


def counties() -> None:
    """
    Two panels of horizontal bars: the ten Washington counties with the
    most speakers in the C16001 categories that absorb the missed
    languages, each estimate with its 90% margin of error.
    """
    table = read("rq3_counties")
    figure, panels = plt.subplots(1, 2, figsize=(WIDTH, 3.0))
    for axes, category, colour in zip(
            panels, ["Other and unspecified languages",
                     "Other Asian and Pacific Island languages"], SERIES):
        block = table[table["category"] == category].iloc[::-1]
        axes.barh(block["county"], block["estimate"], xerr=block["margin"],
                  color=colour, height=0.65,
                  error_kw={"ecolor": INK, "elinewidth": 0.8, "capsize": 2})
        title = category.replace(" and Pacific", "\nand Pacific")
        axes.set_title(title.replace(" and unspecified",
                                     "\nand unspecified"), fontsize=8.5)
        axes.set_xlabel("Speakers aged 5+ (estimate ± MOE)")
        axes.xaxis.set_major_formatter(
            matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
        axes.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(4))
        axes.grid(axis="x", color=GRID)
        axes.grid(axis="y", visible=False)
    save(figure, "f6_counties")


def reconciliation() -> None:
    """
    Parsed national monthly totals (summed over every state row of each
    arrivals report) against the totals printed in the separate region
    report, for every month that both give; points on the diagonal agree
    exactly.
    """
    arrivals = analysis.load_arrivals()
    region = analysis.load_region()
    parsed = arrivals[(arrivals["source"] == "refugee") &
                      (arrivals["month"] <= 12)].groupby(
        ["fiscal_year", "month"])["count"].sum().rename("parsed")
    printed = region[(region["region"] == "Total") &
                     (region["month"] <= 12)].set_index(
        ["fiscal_year", "month"])["count"].rename("printed")
    table = pd.concat([parsed, printed], axis=1, join="inner").reset_index()
    figure, axes = plt.subplots(figsize=(3.4, 3.0))
    limit = table[["parsed", "printed"]].max().max() * 1.05
    axes.plot([0, limit], [0, limit], color=GRID, linewidth=1.2, zorder=0)
    axes.scatter(table["printed"], table["parsed"], s=16, color=SERIES[0],
                 edgecolor="white", linewidth=0.5)
    axes.set_xlabel("Printed in region report")
    axes.set_ylabel("Parsed from state report")
    axes.set_title("Monthly national totals\nFY{}-FY{}, {} months".format(
        table["fiscal_year"].min(), table["fiscal_year"].max(),
        len(table)), fontsize=8.5)
    axes.grid(axis="x", color=GRID)
    save(figure, "f7_reconciliation")


def main():
    setup()
    monthly_series()
    composition()
    ledgers()
    siv_share()
    language_tiers()
    counties()
    reconciliation()


if __name__ == "__main__":
    main()
