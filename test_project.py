"""
Charlie Cheng
CSE 163 AB

Tests for the EDA pipeline. Every assertion is anchored to a number printed
by the publisher (a national total, a state total, a category label), so a
wrong column model cannot pass silently.
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import parse  # noqa: E402

PROCESSED = os.path.join("data", "processed")
OUTPUTS = "outputs"

EXCEL_TOTALS = {
    2015: 69933,
    2016: 84994,
    2017: 53716,
    2018: 22491,
    2019: 30000,
    2020: 11814,
}
ARABIC = ["Iraq", "Syria", "Sudan"]


def load_checks():
    """Read the reconciliation table produced by the parser."""
    return pd.read_csv(os.path.join(PROCESSED, "parse_checks.csv"))


def load_annual():
    """Read the tidy annual arrivals table."""
    return pd.read_csv(os.path.join(PROCESSED, "arrivals_annual.csv"))


def test_excel_years_match_file_totals():
    """The spreadsheet years must reproduce their printed national totals."""
    annual = load_annual()
    refugee = annual[annual["source"] == "refugee"]
    for year, expected in EXCEL_TOTALS.items():
        block = refugee[refugee["fiscal_year"] == year]
        assert block["count"].sum() == expected, year


def test_pdf_years_reconcile_with_printed_totals():
    """Each PDF's parsed total must be within 2% of the printed total."""
    checks = load_checks()
    refugee = checks[checks["source"] == "refugee"]
    for year in (2021, 2023, 2025, 2026):
        row = refugee[refugee["fiscal_year"] == year].iloc[0]
        parse.validate_total(int(row["parsed_total"]),
                             int(row["printed_total"]))


def test_washington_matches_printed_state_total():
    """FY2021 and FY2023 print a Washington total; the parse must equal it."""
    checks = load_checks()
    refugee = checks[checks["source"] == "refugee"]
    for year in (2021, 2023):
        row = refugee[refugee["fiscal_year"] == year].iloc[0]
        assert int(row["parsed_wa"]) == int(row["printed_wa"]), year


def test_monthly_rows_sum_to_annual_rows():
    """Washington's monthly rows must sum to its annual total."""
    monthly = pd.read_csv(os.path.join(PROCESSED, "arrivals_monthly.csv"))
    annual = load_annual()
    month_part = monthly[
        (monthly["source"] == "refugee")
        & (monthly["state"] == "Washington")
        & (monthly["fiscal_year"] == 2021)
    ]["count"].sum()
    year_part = annual[
        (annual["source"] == "refugee")
        & (annual["state"] == "Washington")
        & (annual["fiscal_year"] == 2021)
    ]["count"].sum()
    assert year_part == 480
    assert abs(month_part - year_part) <= 0.02 * year_part


def test_states_are_known_names():
    """Every parsed state must be a real state or the national total row."""
    annual = load_annual()
    unknown = set(annual["state"]) - set(parse.STATES) - {"Grand"}
    assert not unknown, unknown


def test_crosswalk_known_answers():
    """Arabic-speaking nationalities must land in the Arabic category."""
    crosswalk = pd.read_csv(os.path.join("data", "crosswalk.csv"))
    for nationality in ARABIC:
        row = crosswalk[crosswalk["nationality"] == nationality].iloc[0]
        assert row["acs_category"] == "Arabic"
        assert row["tier"] == "own"
    somali = crosswalk[crosswalk["nationality"] == "Somalia"].iloc[0]
    assert somali["tier"] == "shared"
    tigrinya = crosswalk[crosswalk["nationality"] == "Eritrea"].iloc[0]
    assert tigrinya["tier"] == "residual"


def test_deviating_total_is_rejected():
    """A corrupted total must raise, so the check is not vacuous."""
    try:
        parse.validate_total(12000, 11411)
    except ValueError:
        return
    raise AssertionError("validate_total accepted a 5% deviation")


def test_two_ledgers_keep_both_reports():
    """The join must keep rows that appear in only one report."""
    ledger = pd.read_csv(os.path.join(OUTPUTS, "two_ledgers.csv"))
    afghan = ledger[
        (ledger["nationality"] == "Afghanistan")
        & (ledger["fiscal_year"] == 2017)
    ].iloc[0]
    assert afghan["refugee"] == 35
    assert afghan["siv"] == 930


def test_language_tiers_sum_to_one():
    """The four language tiers must partition each year's arrivals."""
    tiers = pd.read_csv(os.path.join(OUTPUTS, "language_tiers.csv"))
    columns = [name for name in tiers.columns if name != "fiscal_year"]
    totals = tiers[columns].sum(axis=1)
    assert all(abs(value - 1) < 1e-9 for value in totals)


def main():
    """Run every test."""
    test_excel_years_match_file_totals()
    test_pdf_years_reconcile_with_printed_totals()
    test_washington_matches_printed_state_total()
    test_monthly_rows_sum_to_annual_rows()
    test_states_are_known_names()
    test_crosswalk_known_answers()
    test_deviating_total_is_rejected()
    test_two_ledgers_keep_both_reports()
    test_language_tiers_sum_to_one()
    print("all tests passed")


if __name__ == "__main__":
    main()
