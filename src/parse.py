"""Parse the RPC arrivals reports into tidy tables.

The annual Excel files (FY2015-FY2020) and the PDF files (FY2021-FY2026) do
not share a layout, and the PDFs do not share one either: the nationality
label sits in a different column from year to year, some pages continue a
state block without repeating the month header, and the FY2025-FY2026 files
draw every row on two or three text layers. Parsing therefore works from word
coordinates instead of ``extract_table``: the value columns are recovered from
where the numbers end, and each label is matched to the line it sits on.
"""

import glob
import os
import re

import pandas as pd
import pdfplumber

SOURCE_DIR = "Dataset"
ARRIVALS_DIR = os.path.join(
    SOURCE_DIR, "Refugee_Arrivals_by_State_and_Nationality"
)
SIV_DIR = os.path.join(SOURCE_DIR, "SIV_Arrivals_by_Nationality_and_State")
OUT_DIR = os.path.join("data", "processed")

MONTHS = [
    "Oct", "Nov", "Dec", "Jan", "Feb", "Mar",
    "Apr", "May", "Jun", "Jul", "Aug", "Sep",
]
NUMBER = re.compile(r"^[\d,]+$")
SKIP = (
    "Refugee", "Arrivals by", "October", "Fiscal", "Page",
    "Based on", "Please note", "Data provided",
    "Only Afghan", "Special Immigrant", "Note:",
)
STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas",
    "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
    "Wisconsin", "Wyoming",
]
STATES.sort(key=len, reverse=True)

ROW_GAP = 2.5
EDGE_TOLERANCE = 1.5
MIN_CLUSTER = 4
MAX_OFFSET = 9.0
RECONCILE_TOLERANCE = 0.02


def validate_total(parsed, printed, tolerance=RECONCILE_TOLERANCE):
    """Raise when a parsed total drifts from the total printed in the file.

    The two totals are not expected to agree exactly: a row repeated across a
    page break leaves a small residue. Anything beyond the tolerance means
    the column model is wrong, so it fails loudly instead of producing a
    plausible wrong number.
    """
    if not printed:
        return
    deviation = abs(parsed - printed) / printed
    if deviation > tolerance:
        raise ValueError(
            "parsed {} vs printed {} ({:.1%} off)".format(
                parsed, printed, deviation
            )
        )


def _to_int(text):
    """Turn '1,533' into 1533."""
    return int(text.replace(",", ""))


def _lines(page):
    """Group a page's words into text lines, dropping repeated layers."""
    rows = []
    words = page.extract_words()
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if rows and word["top"] - rows[-1]["top"] <= ROW_GAP:
            rows[-1]["words"].append(word)
        else:
            rows.append({"top": word["top"], "words": [word]})
    cleaned = []
    for row in rows:
        seen = set()
        unique = []
        for word in sorted(row["words"], key=lambda w: w["x0"]):
            key = (word["text"], round(word["x1"], 1))
            if key not in seen:
                seen.add(key)
                unique.append(word)
        cleaned.append({"top": row["top"], "words": unique})
    return cleaned


def _is_header(line):
    """True when the line is the month header of a table."""
    texts = [w["text"] for w in line["words"]]
    return texts.count("Oct") == 1 and "Sep" in texts


def _is_noise(line):
    """True for titles, dates and closing notes rather than table rows."""
    text = " ".join(w["text"] for w in line["words"])
    return any(marker in text for marker in SKIP)


def _cluster(values):
    """Group sorted floats that sit within tolerance of each other."""
    groups = []
    for value in sorted(values):
        if groups and value - groups[-1][-1] <= EDGE_TOLERANCE:
            groups[-1].append(value)
        else:
            groups.append([value])
    return [group for group in groups if len(group) >= MIN_CLUSTER]


def _header_centres(line):
    """Centres of the 13 value columns, read off the month header.

    The Total column has no consistent header word across layouts, so it is
    extrapolated from the month spacing instead.
    """
    months = [w for w in line["words"] if w["text"] in MONTHS]
    months.sort(key=lambda w: w["x0"])
    if len(months) != 12:
        return []
    centres = [(w["x0"] + w["x1"]) / 2 for w in months]
    steps = [b - a for a, b in zip(centres, centres[1:])]
    step = sorted(steps)[len(steps) // 2]
    centres.append(centres[-1] + step)
    return centres


def _fit(lines, centres):
    """Choose the number edge and offset that align the page's values."""
    tokens = [
        word
        for line in lines
        for word in line["words"]
        if NUMBER.match(word["text"]) and word["x0"] > 70
    ]
    if not tokens:
        return [], "x1"
    best = (-1, "", 0.0)
    for side in ("x1", "x0"):
        for step in range(-44, 45):
            offset = step * 0.5
            score = 0
            for word in tokens:
                best_gap = min(
                    abs(word[side] - (centre + offset))
                    for centre in centres
                )
                if best_gap <= 2.5:
                    score += 1
            if score > best[0]:
                best = (score, side, offset)
    _, side, offset = best
    if not side:
        return [], "x1"
    return [centre + offset for centre in centres], side


def _edges(lines):
    """Column edges for a page, fitted to its own header."""
    header = None
    for line in lines:
        if _is_header(line):
            header = line
            break
    if header is None:
        return [], "x1"
    centres = _header_centres(header)
    if len(centres) != 13:
        return [], "x1"
    return _fit(lines, centres)


def _split(line, edges, side):
    """Split one line into a label and the value of each column."""
    label_max = edges[0] - 15
    words = []
    values = {}
    for word in line["words"]:
        if NUMBER.match(word["text"]) and word["x0"] > 70:
            anchor = word[side]
            index = min(
                range(len(edges)), key=lambda i: abs(edges[i] - anchor)
            )
            if abs(edges[index] - anchor) <= MAX_OFFSET:
                values[index] = _to_int(word["text"])
        elif word["x1"] <= label_max:
            words.append(word)
    return " ".join(w["text"] for w in words), values


def _state_prefix(label):
    """Split a label into a state name and the rest, noting the order.

    The arrivals report prints ``State Nationality``; the SIV report prints
    ``Nationality State``. The returned mode says which one was found.
    """
    for state in STATES:
        if label == state:
            return state, "", "state"
        if label.startswith(state + " "):
            return state, label[len(state) + 1:], "prefix"
        if label.endswith(" " + state):
            return state, label[:-(len(state) + 1)], "suffix"
    return "", label, ""


def _read_page(page, records, passed, cached):
    """Append one page's rows to records, carrying labels across pages.

    ``passed`` holds the last state and nationality seen, because both
    reports merge the label cell that repeats down a block.
    """
    last_state, last_nationality, orientation = passed
    pending = ""
    lines = _lines(page)
    edges, side = _edges(lines)
    if len(edges) < 12:
        edges, side = cached
    if len(edges) < 12:
        return (last_state, last_nationality, orientation), cached
    for line in lines:
        if _is_header(line) or _is_noise(line):
            continue
        label, values = _split(line, edges, side)
        if not values:
            if label:
                pending = (pending + " " + label).strip()
            continue
        text = (pending + " " + label).strip()
        pending = ""
        if "Grand" in text:
            records.append(
                {"state": "Grand", "nationality": "Total", "values": values}
            )
            continue
        state, rest, mode = _state_prefix(text)
        if mode in ("prefix", "suffix"):
            orientation = mode
        if mode:
            if state:
                last_state = state
            nationality = rest
        else:
            nationality = text
        if not nationality:
            if orientation == "suffix":
                nationality = last_nationality
            else:
                nationality = "Total"
        if orientation == "suffix":
            last_nationality = nationality
        records.append(
            {
                "state": last_state,
                "nationality": nationality,
                "values": values,
            }
        )
    return (last_state, last_nationality, orientation), (edges, side)


def parse_arrivals_pdf(path, fiscal_year):
    """Parse one arrivals PDF into monthly and annual frames plus checks."""
    records = []
    carried = ("", "", "")
    cached = ([], "x1")
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            carried, cached = _read_page(page, records, carried, cached)
    monthly = []
    annual = []
    totals = []
    grand = {}
    for row in records:
        values = row["values"]
        name = row["nationality"]
        if row["state"] == "Grand":
            grand = grand or values
            continue
        if name.lower() == "total":
            totals.append(
                {
                    "state": row["state"],
                    "fiscal_year": fiscal_year,
                    "count": values.get(12, 0),
                }
            )
            continue
        if 12 not in values:
            continue
        annual.append(
            {
                "state": row["state"],
                "nationality": name,
                "fiscal_year": fiscal_year,
                "count": values[12],
            }
        )
        for index in range(12):
            if values.get(index):
                monthly.append(
                    {
                        "state": row["state"],
                        "nationality": name,
                        "fiscal_year": fiscal_year,
                        "month": index + 1,
                        "count": values[index],
                    }
                )
    if len(totals):
        totals = pd.DataFrame(totals).drop_duplicates(subset=["state"])
    return (
        pd.DataFrame(monthly),
        pd.DataFrame(annual),
        pd.DataFrame(totals),
        grand,
    )


def read_arrivals_excel(path, fiscal_year):
    """Read one annual Excel file (FY2015-FY2020) into annual rows."""
    raw = pd.read_excel(path, header=None)
    header = None
    for index in range(len(raw)):
        if str(raw.iloc[index, 0]).strip() == "Placement State":
            header = index
            break
    rows = []
    state = ""
    for index in range(header + 2, len(raw)):
        first, second, third = (
            raw.iloc[index, 0], raw.iloc[index, 1], raw.iloc[index, 2]
        )
        if isinstance(first, str) and first.strip().lower() == "total":
            break
        if pd.notna(first):
            state = str(first).strip()
            continue
        if pd.notna(second) and pd.notna(third):
            name = str(second).strip()
            if name.lower() == "total":
                continue
            rows.append(
                {
                    "state": state,
                    "nationality": name,
                    "fiscal_year": fiscal_year,
                    "count": int(third),
                }
            )
    return pd.DataFrame(rows)


def _dedupe(frame):
    """Drop repeated (state, nationality) rows produced by repeated pages."""
    if not len(frame):
        return frame
    frame = frame.drop_duplicates(subset=["state", "nationality"])
    return frame.reset_index(drop=True)


def load_all():
    """Parse every arrivals and SIV file into tidy frames plus checks."""
    monthly = []
    annual = []
    checks = []
    for label, folder in (("refugee", ARRIVALS_DIR), ("siv", SIV_DIR)):
        for path in sorted(glob.glob(os.path.join(folder, "*"))):
            name = os.path.basename(path)
            year = int(re.search(r"FY\s?(\d{4})", name).group(1))
            if path.endswith(".pdf"):
                m, a, t, grand = parse_arrivals_pdf(path, year)
            else:
                m, a, t, grand = (
                    pd.DataFrame(),
                    read_arrivals_excel(path, year),
                    pd.DataFrame(),
                    {},
                )
            a = _dedupe(a)
            if not len(a):
                a = pd.DataFrame(
                    columns=["state", "nationality", "fiscal_year", "count"]
                )
            a["source"] = label
            if not len(m):
                m = pd.DataFrame(
                    columns=[
                        "state", "nationality", "fiscal_year", "month",
                        "count",
                    ]
                )
            m = m.drop_duplicates(
                subset=["state", "nationality", "fiscal_year", "month"]
            )
            m["source"] = label
            monthly.append(m)
            annual.append(a)
            washington = a.loc[a["state"] == "Washington", "count"].sum()
            printed = t.loc[t["state"] == "Washington", "count"] if len(t) \
                else t
            total = int(a["count"].sum())
            printed_total = grand.get(12) if grand else None
            try:
                validate_total(total, printed_total)
                status = "ok"
            except ValueError:
                status = "check"
            checks.append(
                {
                    "source": label,
                    "fiscal_year": year,
                    "rows": len(a),
                    "parsed_total": total,
                    "printed_total": printed_total,
                    "parsed_wa": int(washington),
                    "printed_wa": int(printed.sum()) if len(printed) else None,
                    "month_rows": len(m),
                    "status": status,
                }
            )
    return (
        pd.concat(monthly, ignore_index=True),
        pd.concat(annual, ignore_index=True),
        pd.DataFrame(checks),
    )


def main():
    """Parse every file, print the checks, and save tidy tables."""
    os.makedirs(OUT_DIR, exist_ok=True)
    monthly, annual, checks = load_all()
    print(checks.to_string(index=False))
    annual.to_csv(os.path.join(OUT_DIR, "arrivals_annual.csv"), index=False)
    monthly.to_csv(
        os.path.join(OUT_DIR, "arrivals_monthly.csv"), index=False
    )
    checks.to_csv(os.path.join(OUT_DIR, "parse_checks.csv"), index=False)


if __name__ == "__main__":
    main()
