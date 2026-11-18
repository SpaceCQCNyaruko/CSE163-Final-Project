"""
Charlie Cheng, Zhongtian Liu
CSE 163
Tests for the EDA code. Unit tests run each parsing and analysis helper on
small hand-made inputs with known answers. The remaining tests check the
parsed data against numbers the publisher prints (national and state
totals, the separate region report) and against values read by eye from
the page images, so a wrong column model or a bad OCR reading cannot pass
silently. Run parse.py and analysis.py first.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "src"))

import analysis  # noqa: E402
import ocr  # noqa: E402
import parse  # noqa: E402

PROCESSED = os.path.join("data", "processed")
OUTPUTS = "outputs"
EXCEL_TOTALS = {2015: 69933, 2016: 84994, 2017: 53716, 2018: 22491,
                2019: 30000, 2020: 11814}
SIV_TOTALS = {2015: 7226, 2016: 12269, 2017: 19321, 2018: 10256,
              2019: 7892, 2020: 9768, 2021: 8567, 2022: 10492,
              2023: 17658, 2024: 31585, 2025: 18012}


def assert_equals(expected: object, received: object) -> None:
    """
    Raises an AssertionError naming both values if they differ. Floats are
    compared with a small tolerance.
    """
    if isinstance(expected, float) or isinstance(received, float):
        assert abs(expected - received) < 1e-9, (expected, received)
    else:
        assert expected == received, (expected, received)


def annual_row(state: str, nationality: str, fiscal_year: int,
               source: str = "refugee") -> int:
    """
    Returns the parsed annual count for one row of a report, or 0.
    """
    arrivals = pd.read_csv(os.path.join(PROCESSED, "arrivals.csv"))
    keep = (arrivals["source"] == source) & \
        (arrivals["state"] == state) & \
        (arrivals["nationality"] == nationality) & \
        (arrivals["fiscal_year"] == fiscal_year) & (arrivals["month"] == 13)
    return int(arrivals.loc[keep, "count"].sum())


def test_to_count() -> None:
    """Tests the function to_count."""
    assert_equals(1274, parse.to_count("1,274"))
    assert_equals(0, parse.to_count(""))
    assert_equals(3344, parse.to_count("3.344"))
    assert_equals(1314, parse.to_count("1314"))
    assert_equals(7, parse.to_count(" 7 "))
    assert_equals(None, parse.to_count("4r446"))
    assert_equals(None, parse.to_count("Total"))


def test_snap_state() -> None:
    """Tests the function snap_state."""
    assert_equals("Iowa", parse.snap_state("lowa"))
    assert_equals("Oregon", parse.snap_state("oregon"))
    assert_equals("Grand Total", parse.snap_state("Grand Total"))
    assert_equals("Not Available", parse.snap_state("Not Available"))
    assert_equals("", parse.snap_state("settlement in Doe"))


def test_repair() -> None:
    """Tests the function _repair."""
    printed = ["315", "307", "350", "492", "377", "344", "354", "290",
               "243", "251", "456", "667", "4r446"]
    counts = [parse.to_count(text) for text in printed]
    assert_equals(4446, parse._repair(counts, printed)[12])
    month_gap = [1, 2, None, 0, 0, 0, 0, 0, 0, 0, 0, 0, 30]
    month_text = ["1", "2", "2?", "", "", "", "", "", "", "", "", "", "30"]
    assert_equals(27, parse._repair(month_gap, month_text)[2])
    wrong_digit = list(month_text)
    wrong_digit[2] = "3?"
    assert_equals(None, parse._repair(month_gap, wrong_digit)[2])
    wrong_length = list(month_text)
    wrong_length[2] = "2??"
    assert_equals(None, parse._repair(month_gap, wrong_length)[2])
    two_gaps = [None, None] + [0] * 10 + [5]
    assert_equals(two_gaps, parse._repair(two_gaps, ["?"] * 13))


def test_state_sequence() -> None:
    """Tests the function _state_sequence."""
    labels = ["Alabama", "", "District of", "Columbia", "", "lowa"]
    expected = ["Alabama", "Alabama", "Alabama", "District of Columbia",
                "District of Columbia", "Iowa"]
    assert_equals(expected, parse._state_sequence(labels))
    assert_equals(["", ""], parse._state_sequence(["", ""]))


def test_split_glued() -> None:
    """Tests the function _split_glued."""
    assert_equals(("Massachusetts", "Afghanistan"),
                  parse._split_glued("MassachusettsAfghanistan"))
    assert_equals(("New Hampshire", "South Africa"),
                  parse._split_glued("New HampshireSouth Africa"))
    assert_equals(("West Virginia", ""), parse._split_glued("West Virginia"))
    assert_equals(("District of", ""), parse._split_glued("District of"))


def make_word(text: str, x0: float, bottom: float) -> dict:
    """
    Returns a word dict as pdf_words would, 6 points tall and 5 points
    wide per character.
    """
    return {"text": text, "x0": x0, "x1": x0 + 5 * len(text),
            "top": bottom - 6, "bottom": bottom, "visible": True}


def test_words_to_rows() -> None:
    """Tests the functions table_layout and words_to_rows."""
    words = [make_word("State", 10, 20), make_word("PA", 60, 20),
             make_word("Nationality", 72, 20), make_word("Total", 500, 20)]
    for index, month in enumerate(parse.MONTHS):
        words.append(make_word(month, 150 + 30 * index, 20))
    words += [make_word("Alabama", 10, 35), make_word("Total", 60, 35),
              make_word("3", 155, 35), make_word("3", 505, 35),
              make_word("Iraq", 60, 45), make_word("3", 155, 45),
              make_word("3", 505, 45),
              make_word("Based", 10, 60), make_word("9", 155, 60)]
    layout = parse.table_layout(words)
    rows = parse.words_to_rows(words, 1, layout)
    assert_equals(2, len(rows))
    assert_equals("Alabama", rows[0]["state_label"])
    assert_equals("Total", rows[0]["nationality"])
    assert_equals("Iraq", rows[1]["nationality"])
    assert_equals("3", rows[1]["Oct"])
    assert_equals("3", rows[1]["Total"])
    assert_equals("", rows[1]["Nov"])
    assert_equals(None, parse.table_layout(words[12:]))


def raw_table(rows: list) -> pd.DataFrame:
    """
    Returns rows given as (page, state_label, nationality, October count,
    total) as a raw table like read_text_pdf's, all other months blank.
    """
    records = []
    for page, state, nationality, october, total in rows:
        record = {"page": page, "row_y": 0, "state_label": state,
                  "nationality": nationality}
        for month in parse.MONTHS:
            record[month] = ""
        record["Oct"] = october
        record["Total"] = total
        records.append(record)
    return pd.DataFrame(records, columns=parse.ROW_COLUMNS)


def test_tidy_rows() -> None:
    """Tests the function tidy_rows."""
    raw = raw_table([(1, "Grand Total", "", "5", "5"),
                     (1, "Alabama", "Total", "5", "5"),
                     (1, "", "Iraq", "2", "2"),
                     (1, "", "Syria", "3", "3"),
                     (2, "Alabama", "Syria", "3", "3")])
    tidy, checks, repairs = parse.tidy_rows(raw, "refugee", 2021)
    assert_equals(1, checks["page_repeats"])
    assert_equals(0, checks["block_failures"])
    assert_equals(True, checks["grand_matches"])
    assert_equals(5, checks["grand_total_parsed"])
    assert_equals(0, len(repairs))
    annual = tidy[tidy["month"] == 13]
    assert_equals(["Iraq", "Syria"], sorted(annual["nationality"]))
    assert_equals({"Alabama"}, set(tidy["state"]))
    siv = raw_table([(1, "", "Grand Total", "4", "4"),
                     (1, "Alabama", "Afghanistan", "1", "1"),
                     (1, "Texas", "", "3", "3")])
    tidy, checks, _ = parse.tidy_rows(siv, "siv", 2021)
    assert_equals(True, checks["grand_matches"])
    assert_equals({"Afghanistan"}, set(tidy["nationality"]))
    assert_equals({"Alabama", "Texas"}, set(tidy["state"]))


def test_nationality_map() -> None:
    """Tests the function nationality_map."""
    arrivals = pd.DataFrame({
        "nationality": ["Dem. Rep. Congo", "Dem. Rep. Con..", "Poldova",
                        "Moldova", "iran", "Iran", "Iran", "The Gambia",
                        "Gambia"],
        "fiscal_year": [2024, 2021, 2024, 2019, 2022, 2019, 2023, 2024,
                        2019],
        "count": [1] * 9})
    names = parse.nationality_map(arrivals).set_index("printed")
    assert_equals("Dem. Rep. Congo", names.loc["Dem. Rep. Con..",
                                               "standard"])
    assert_equals("truncated", names.loc["Dem. Rep. Con..", "rule"])
    assert_equals("Moldova", names.loc["Poldova", "standard"])
    assert_equals("ocr spelling", names.loc["Poldova", "rule"])
    assert_equals("Iran", names.loc["iran", "standard"])
    assert_equals("Gambia", names.loc["The Gambia", "standard"])
    assert_equals("unchanged", names.loc["Iran", "rule"])


def test_has_ink() -> None:
    """Tests the function has_ink."""
    blank = np.full((20, 20), 255, np.uint8)
    shaded = np.full((20, 20), 240, np.uint8)
    printed = blank.copy()
    printed[5:15, 9:11] = 0
    assert_equals(False, ocr.has_ink(blank))
    assert_equals(False, ocr.has_ink(shaded))
    assert_equals(True, ocr.has_ink(printed))


def test_calendar_date() -> None:
    """Tests the function calendar_date."""
    assert_equals(pd.Timestamp("2020-10-01"), analysis.calendar_date(2021, 1))
    assert_equals(pd.Timestamp("2020-12-01"), analysis.calendar_date(2021, 3))
    assert_equals(pd.Timestamp("2021-01-01"), analysis.calendar_date(2021, 4))
    assert_equals(pd.Timestamp("2021-09-01"),
                  analysis.calendar_date(2021, 12))


def test_l1_distance() -> None:
    """Tests the function l1_distance."""
    one = pd.Series({"Iraq": 0.5, "Syria": 0.5})
    assert_equals(0.0, analysis.l1_distance(one, one))
    assert_equals(2.0, analysis.l1_distance(one, pd.Series({"Peru": 1.0})))
    other = pd.Series({"Iraq": 1.0})
    assert_equals(1.0, analysis.l1_distance(one, other))


def test_js_distance() -> None:
    """Tests the function js_distance."""
    one = pd.Series({"Iraq": 0.5, "Syria": 0.5})
    assert_equals(0.0, analysis.js_distance(one, one))
    assert_equals(1.0, analysis.js_distance(one, pd.Series({"Peru": 1.0})))


def test_split_gain() -> None:
    """Tests the function split_gain."""
    index, gain = analysis.split_gain(np.array([0, 0, 0, 10, 10, 10.0]))
    assert_equals(3, index)
    assert_equals(150.0, gain)
    _, flat = analysis.split_gain(np.array([4.0, 4.0, 4.0, 4.0]))
    assert_equals(0.0, flat)


def test_lag_one_autocorrelation() -> None:
    """Tests the function lag_one_autocorrelation."""
    alternating = np.array([1.0, -1.0] * 10)
    assert analysis.lag_one_autocorrelation(alternating) < -0.9
    trend = np.arange(20, dtype=float)
    assert analysis.lag_one_autocorrelation(trend) > 0.8


def test_tier() -> None:
    """Tests the function tier."""
    assert_equals("own", analysis.tier("Arabic", "Arabic"))
    assert_equals("own", analysis.tier("French", "French (incl. Cajun)"))
    assert_equals("shared", analysis.tier("Dari",
                                          "Persian (incl. Farsi, Dari)"))
    assert_equals("shared", analysis.tier(
        "Somali", "Amharic, Somali, or other Afro-Asiatic languages"))
    assert_equals("residual", analysis.tier(
        "Tigrinya", "Amharic, Somali, or other Afro-Asiatic languages"))
    assert_equals("residual", analysis.tier(
        "Ukrainian", "Russian, Polish, or other Slavic languages"))


def test_two_ledgers() -> None:
    """Tests the function two_ledgers."""
    arrivals = pd.DataFrame({
        "source": ["refugee", "siv", "siv"],
        "fiscal_year": [2017, 2017, 2017],
        "state": ["Washington"] * 3,
        "nationality": ["Iraq", "Iraq", "Afghanistan"],
        "month": [13, 13, 13], "count": [10, 4, 7]})
    ledger = analysis.two_ledgers(arrivals).set_index("nationality")
    assert_equals(2, len(ledger))
    assert_equals("both", ledger.loc["Iraq", "in_report"])
    assert_equals("SIV only", ledger.loc["Afghanistan", "in_report"])
    assert_equals(0.0, ledger.loc["Afghanistan", "refugee"])
    shares = analysis.siv_share(ledger.reset_index())
    iraq = shares[(shares["nationality"] == "Iraq") &
                  (shares["fiscal_year"] == 2017)].iloc[0]
    assert_equals(4 / 14, iraq["siv_share"])


def test_visibility() -> None:
    """Tests the function visibility."""
    crosswalk = pd.DataFrame({
        "nationality": ["Iraq", "Eritrea", "Eritrea"],
        "language": ["Arabic", "Tigrinya", "Arabic"],
        "role": ["main", "main", "other"],
        "b16001_category": ["Arabic", "Amharic, Somali, or other "
                            "Afro-Asiatic languages", "Arabic"],
        "c16001_category": ["Arabic", "Other and unspecified languages",
                            "Arabic"]})
    annual = pd.DataFrame({"fiscal_year": [2020, 2020, 2020],
                           "nationality": ["Iraq", "Eritrea", "Peru"],
                           "count": [2, 1, 1]})
    table = analysis.visibility(annual, crosswalk).iloc[0]
    assert_equals(0.5, table["pessimistic_visible"])
    assert_equals(0.75, table["optimistic_visible"])
    assert_equals(0.25, table["not in crosswalk"])
    assert_equals(0.25, table["residual"])


def test_load_report() -> None:
    """Tests the function load_report on every report, against the
    reconciliation table written by parse.py."""
    checks = pd.read_csv(os.path.join(PROCESSED, "checks.csv"))
    assert_equals(23, len(checks))
    for column in ("unreadable_cells", "row_sum_failures", "block_failures"):
        assert_equals(0, int(checks[column].sum()))
    assert checks["grand_matches"].astype(bool).all()
    refugee = checks[checks["source"] == "refugee"].set_index("fiscal_year")
    for year, total in EXCEL_TOTALS.items():
        assert_equals(total, int(refugee.loc[year, "grand_total_parsed"]))
    siv = checks[checks["source"] == "siv"].set_index("fiscal_year")
    for year, total in SIV_TOTALS.items():
        assert_equals(total, int(siv.loc[year, "grand_total_parsed"]))


def test_region_gaps() -> None:
    """Tests the function region_gaps: every year's parsed national
    totals must match the separate region report, month by month where
    months exist. FY2018 is the one known difference: its region file was
    regenerated in 2020 and counts 26 more arrivals."""
    checks = pd.read_csv(os.path.join(PROCESSED, "checks.csv"))
    refugee = checks[checks["source"] == "refugee"].set_index("fiscal_year")
    for year in range(2015, 2027):
        expected = -26 if year == 2018 else 0
        assert_equals(expected, int(refugee.loc[year, "region_total_gap"]))
    for year in analysis.MONTHLY_YEARS:
        assert_equals(0, int(refugee.loc[year, "region_month_gaps"]))


def test_repairs_logged() -> None:
    """Tests that the only repaired cell is the one known OCR misreading
    (FY2024 Pennsylvania total, printed 4,446)."""
    repairs = pd.read_csv(os.path.join(PROCESSED, "repairs.csv"))
    assert_equals(1, len(repairs))
    assert_equals(4446, int(repairs["repaired"].iloc[0]))
    assert_equals(2024, int(repairs["fiscal_year"].iloc[0]))


def test_read_values_by_eye() -> None:
    """Tests parsed rows against values read by eye from the page images
    of the OCR years (FY2022 page 2, FY2024 page 1) and a text year."""
    assert_equals(514, annual_row("California", "Syria", 2022))
    assert_equals(353, annual_row("California", "Ukraine", 2022))
    assert_equals(140, annual_row("Colorado", "Burma", 2022))
    assert_equals(53, annual_row("Alabama", "Afghanistan", 2024))
    assert_equals(199, annual_row("Alabama", "Venezuela", 2024))
    assert_equals(1274, annual_row("Arizona", "Dem. Rep. Congo", 2024))
    assert_equals(35, annual_row("Arizona", "Afghanistan", 2021))
    assert_equals(930, annual_row("Washington", "Afghanistan", 2017, "siv"))


def test_state_annual() -> None:
    """Tests the function state_annual against the Washington totals the
    FY2021 and FY2023 reports print."""
    arrivals = analysis.load_arrivals()
    totals = analysis.state_annual(arrivals).groupby("fiscal_year")[
        "count"].sum()
    assert_equals(480, int(totals[2021]))
    assert_equals(2429, int(totals[2023]))
    assert_equals(12, len(totals))


def test_national_monthly() -> None:
    """Tests the function national_monthly: 144 months, no gaps, and the
    known collapse from 10,285 (Jan 2025) to 2 (Feb 2025)."""
    series = analysis.national_monthly(analysis.load_region())
    assert_equals(144, len(series))
    assert_equals(0, int(series["arrivals"].isna().sum()))
    dated = series.set_index("date")["arrivals"]
    assert_equals(10285, int(dated[pd.Timestamp("2025-01-01")]))
    assert_equals(2, int(dated[pd.Timestamp("2025-02-01")]))


def main():
    test_to_count()
    test_snap_state()
    test_repair()
    test_state_sequence()
    test_split_glued()
    test_words_to_rows()
    test_tidy_rows()
    test_nationality_map()
    test_has_ink()
    test_calendar_date()
    test_l1_distance()
    test_js_distance()
    test_split_gain()
    test_lag_one_autocorrelation()
    test_tier()
    test_two_ledgers()
    test_visibility()
    test_load_report()
    test_region_gaps()
    test_repairs_logged()
    test_read_values_by_eye()
    test_state_annual()
    test_national_monthly()
    print("all tests passed")


if __name__ == "__main__":
    main()
