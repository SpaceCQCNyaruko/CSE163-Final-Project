"""Draw the figures used in the EDA report.

Each function reads one table from ``outputs/`` and saves a PNG in
``figures/``. Captions live in the report, so the titles here only name the
axes and the subset of data on display.
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

OUTPUTS = "outputs"
FIGURES = "figures"
ALL_YEARS = list(range(2015, 2027))
MONTH_LABELS = [
    "Oct", "Nov", "Dec", "Jan", "Feb", "Mar",
    "Apr", "May", "Jun", "Jul", "Aug", "Sep",
]
COLORS = ["#1f4e79", "#2e75b6", "#9dc3e6", "#c55a11", "#f4b183",
          "#7f7f7f", "#d9d9d9"]


def setup():
    """Apply one visual style to every figure."""
    os.makedirs(FIGURES, exist_ok=True)
    plt.rcParams.update(
        {
            "figure.dpi": 150,
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": "#e6e6e6",
            "axes.axisbelow": True,
        }
    )


def annual_arrivals():
    """Bar chart of Washington's refugee arrivals per fiscal year."""
    annual = pd.read_csv(os.path.join(OUTPUTS, "wa_annual.csv"))
    values = dict(zip(annual["fiscal_year"], annual["arrivals"]))
    heights = [values.get(year, 0) for year in ALL_YEARS]
    figure, axes = plt.subplots(figsize=(6.4, 2.8))
    bars = axes.bar(
        [str(year) for year in ALL_YEARS], heights,
        color=COLORS[0], width=0.7,
    )
    for year, bar in zip(ALL_YEARS, bars):
        if year not in values:
            bar.set_hatch("///")
            bar.set_color("#ffffff")
            bar.set_edgecolor("#999999")
            axes.text(
                bar.get_x() + bar.get_width() / 2, 40, "no data",
                rotation=90, ha="center", va="bottom", fontsize=6,
                color="#777777",
            )
    axes.set_ylabel("Refugee arrivals")
    axes.set_title("Washington State refugee arrivals by fiscal year")
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, "f1_annual.png"))
    plt.close(figure)


def composition():
    """Stacked bars of the five largest nationalities each year."""
    top = pd.read_csv(os.path.join(OUTPUTS, "wa_top5.csv"))
    years = sorted(top["fiscal_year"].unique())
    names = (
        top.groupby("nationality")["count"].sum()
        .sort_values(ascending=False).head(5).index.tolist()
    )
    figure, axes = plt.subplots(figsize=(6.4, 3.0))
    bottom = [0.0] * len(years)
    for colour, name in zip(COLORS, names):
        shares = []
        for year in years:
            selected = (top["fiscal_year"] == year) & (
                top["nationality"] == name
            )
            row = top[selected]
            shares.append(float(row["share"].iloc[0]) if len(row) else 0.0)
        axes.bar(
            [str(year) for year in years], shares, bottom=bottom,
            label=name, color=colour,
        )
        bottom = [a + b for a, b in zip(bottom, shares)]
    axes.bar(
        [str(year) for year in years], [1 - b for b in bottom],
        bottom=bottom, label="all others", color="#d9d9d9",
    )
    axes.set_ylabel("Share of the year's arrivals")
    axes.set_ylim(0, 1)
    axes.legend(frameon=False, fontsize=7, ncol=3, loc="upper right")
    axes.set_title("Nationalities making up most of the year's arrivals")
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, "f2_composition.png"))
    plt.close(figure)


def monthly_series():
    """Small multiples of the monthly series for the parsed years.

    Washington and the national total differ by an order of magnitude, so the
    national line sits on its own axis instead of hiding the state series.
    """
    frame = pd.read_csv(os.path.join(OUTPUTS, "wa_monthly.csv"))
    years = sorted(frame["fiscal_year"].unique())
    figure, panels = plt.subplots(
        len(years), 1, figsize=(6.4, 1.7 * len(years)), sharex=True
    )
    for panel, year in zip(panels, years):
        block = frame[frame["fiscal_year"] == year].sort_values("month")
        panel.bar(
            block["month"], block["washington"], width=0.7,
            color=COLORS[0], label="Washington (left)",
        )
        twin = panel.twinx()
        twin.plot(
            block["month"], block["national"], marker="o", ms=3,
            lw=1.2, color=COLORS[3], label="All states (right)",
        )
        twin.grid(False)
        twin.set_ylabel("all states", fontsize=6, color=COLORS[3])
        twin.tick_params(labelsize=6, colors=COLORS[3])
        panel.set_ylabel(str(year), rotation=0, labelpad=22)
        panel.set_xticks(range(1, 13))
        panel.set_xticklabels(MONTH_LABELS, fontsize=7)
        panel.tick_params(labelsize=7)
        if year == years[0]:
            panel.legend(frameon=False, fontsize=6, loc="upper left")
    panels[-1].set_xlabel("Month of the fiscal year")
    figure.suptitle(
        "Monthly arrivals: Washington bars, national line", y=0.995
    )
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, "f3_monthly.png"))
    plt.close(figure)


def siv_share():
    """Share of recorded arrivals that appears only in the SIV report."""
    frame = pd.read_csv(os.path.join(OUTPUTS, "two_ledgers.csv"))
    figure, axes = plt.subplots(figsize=(6.4, 2.3))
    for colour, name in zip(COLORS, ("Afghanistan", "Iraq")):
        block = frame[frame["nationality"] == name].sort_values(
            "fiscal_year"
        )
        axes.plot(
            block["fiscal_year"], block["siv_share"], marker="o", ms=4,
            lw=1.4, color=colour, label=name,
        )
    years = sorted(frame["fiscal_year"].unique())
    axes.set_xticks(years)
    axes.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    axes.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    axes.set_xlabel("Fiscal year")
    axes.set_ylabel("SIV share of recorded arrivals")
    axes.set_ylim(0, 1.05)
    axes.legend(frameon=False, fontsize=7, loc="center right")
    axes.set_title("How much of the recorded count the refugee report misses")
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, "f8_siv_share.png"))
    plt.close(figure)


def language_tiers():
    """Share of arrivals by how the ACS names their language."""
    frame = pd.read_csv(os.path.join(OUTPUTS, "language_tiers.csv"))
    frame = frame.set_index("fiscal_year")
    order = [c for c in ("own", "shared", "residual",
                         "not in crosswalk") if c in frame.columns]
    figure, axes = plt.subplots(figsize=(6.4, 2.8))
    bottom = [0.0] * len(frame)
    for colour, name in zip(COLORS, order):
        axes.bar(
            [str(year) for year in frame.index], frame[name],
            bottom=bottom, label=name, color=colour,
        )
        bottom = [a + b for a, b in zip(bottom, frame[name])]
    axes.set_ylabel("Share of arrivals")
    axes.set_ylim(0, 1)
    axes.legend(
        frameon=False, fontsize=6.5, ncol=4, loc="lower center",
        bbox_to_anchor=(0.5, 1.0), handlelength=1.2, columnspacing=1.0,
    )
    axes.set_title(
        "Arrivals by how the Census language table names them", pad=14
    )
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, "f5_language.png"))
    plt.close(figure)


def counties():
    """Counties where the absorbing language category is largest."""
    frame = pd.read_csv(os.path.join(OUTPUTS, "county_residual.csv"))
    frame = frame.iloc[::-1]
    figure, axes = plt.subplots(figsize=(6.4, 2.8))
    axes.barh(
        frame["county"].str.replace(" County, Washington", ""),
        frame["estimate"], xerr=frame["margin"], color=COLORS[1],
        error_kw={"ecolor": "#333333", "capsize": 2, "lw": 0.8},
    )
    axes.set_xlabel("Population 5+, estimate +/- margin of error")
    axes.set_title('"Other and unspecified languages", by county')
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, "f6_counties.png"))
    plt.close(figure)


def ledgers():
    """Afghan and Iraqi arrivals in each report."""
    frame = pd.read_csv(os.path.join(OUTPUTS, "two_ledgers.csv"))
    afghan = frame[frame["nationality"] == "Afghanistan"]
    iraq = frame[frame["nationality"] == "Iraq"]
    figure, panels = plt.subplots(1, 2, figsize=(6.4, 2.6), sharey=False)
    for panel, block, title in zip(
        panels, (afghan, iraq), ("Afghanistan", "Iraq")
    ):
        positions = range(len(block))
        panel.bar(
            [p - 0.2 for p in positions], block["refugee"], width=0.4,
            label="Refugee report", color=COLORS[0],
        )
        panel.bar(
            [p + 0.2 for p in positions], block["siv"], width=0.4,
            label="SIV report", color=COLORS[3],
        )
        panel.set_xticks(list(positions))
        panel.set_xticklabels(block["fiscal_year"].astype(int), fontsize=7)
        panel.set_title(title, fontsize=9)
        panel.legend(frameon=False, fontsize=6)
    panels[0].set_ylabel("Arrivals in Washington")
    figure.suptitle("Two reports, one nationality", y=1.0, fontsize=10)
    figure.tight_layout()
    figure.savefig(os.path.join(FIGURES, "f7_ledgers.png"))
    plt.close(figure)


def main():
    """Render every figure."""
    setup()
    annual_arrivals()
    composition()
    monthly_series()
    language_tiers()
    counties()
    ledgers()
    siv_share()
    print("figures written to", FIGURES)


if __name__ == "__main__":
    main()
