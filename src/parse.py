"""
Charlie Cheng, Zhongtian Liu
CSE 163
Turns every published arrivals report into tidy tables. Three kinds of
source are read: the FY2015-FY2020 Excel files (annual counts only), the
text PDFs (arrivals FY2021, FY2023, FY2025, FY2026 and every SIV year), and
the OCR output that ocr.py writes for the FY2022 and FY2024 arrivals files.
The region-by-month reports are read too, as an independent check on the
national monthly totals. Every PDF table is rebuilt from word positions and
must pass three checks: each row's months add up to its Grand Total, each
state's rows add up to the state's printed Total row, and the state totals
add up to the printed Grand Total row.
"""

import difflib
import os
import re

import fitz
import numpy as np
import pandas as pd
import pdfplumber

DATASET = "Dataset"
ARRIVALS_DIR = os.path.join(DATASET,
                            "Refugee_Arrivals_by_State_and_Nationality")
SIV_DIR = os.path.join(DATASET, "SIV_Arrivals_by_Nationality_and_State")
REGION_DIR = os.path.join(DATASET, "Refugee_Arrivals_by_Region")
OCR_DIR = os.path.join("data", "ocr")
OUT_DIR = os.path.join("data", "processed")

# The publisher's file names change from year to year, so each year is
# mapped to its file explicitly instead of generating a pattern.
ARRIVAL_FILES = {
    2015: "FY 2015 Arrivals by State and Nationality.xls",
    2016: "FY 2016 Arrivals by State and Nationality.xls",
    2017: "FY 2017 Arrivals by State and Nationality.xls",
    2018: "FY 2018 Arrivals by State and Nationality.xls",
    2019: "FY 2019 Arrivals by State and Nationality.xlsx",
    2020: "FY 2020 Arrivals by State and Nationality.xlsx",
    2021: "FY 2021 Arrivals by State and Nationality as of 30 Sep 2021.pdf",
    2022: "fy2022_arrivals.csv",
    2023: "FY 2023 Refugee Arrivals by State and Nationality as of "
          "30 Sep 2023.pdf",
    2024: "fy2024_arrivals.csv",
    2025: "FY 2025 Arrivals by State and Nationality as of 30 Sep 2025.pdf",
    2026: "FY 2026 Arrivals by State and Nationality as of 30 Sep 2026.pdf",
}
SIV_FILES = {
    2015: "FY2015 Amerasian & SIV Arrivals by Nationality and State.pdf",
    2016: "FY2016 Amerasian & SIV Arrivals by Nationality and State.pdf",
    2017: "FY2017 Amerasian & SIV Arrivals by Nationality and State.pdf",
    2018: "FY2018 Amerasian & SIV Arrivals by Nationality and State.pdf",
    2019: "FY2019 Amerasian & SIV Arrivals by Nationality and State.pdf",
    2020: "FY2020 Amerasian & SIV Arrivals by Nationality and State.pdf",
    2021: "FY2021 Amerasian & SIV Arrivals by Nationality and State.pdf",
    2022: "FY 2022 Amerasian & SIV Arrivals by Nationality and State.pdf",
    2023: "FY 2023 Amerasian & SIV Arrivals by Nationality and State.pdf",
    2024: "FY 2024 Amerasian & SIV Arrivals by Nationality and "
          "State_updated_2025_01_14.pdf",
    2025: "FY 2025 Amerasian & SIV Arrivals by Nationality and State.pdf",
}
REGION_FILES = {
    2015: "Arrivals by PA Region by Month(FY15).xls",
    2016: "Arrivals by PA Region by Month(10.19.17(FY16)).xls",
    2017: "Arrivals by PA Region by Month(FY17).xls",
    2018: "FY2018 Refugee Arrivals by Region.pdf",
    2019: "Arrivals by PA Region by Month FY19REF.xlsx",
    2020: "Arrivals by PA Region by Month as of 9-30-20.xlsx",
    2021: "Refugee Arrivals by Region - Fiscal Year by Month as of "
          "30 Sep 2021.pdf",
    2022: "Refugee Arrivals by Region - Fiscal Year by Month as of "
          "30 Sep 2022.pdf",
    2023: "Refugee Arrivals by Region - Fiscal Year by Month as of "
          "30 Sep 2023.pdf",
    2024: "fy2024_region.csv",
    2025: "FY 2025 Arrivals by Region - Fiscal Year by Month as of "
          "30 Sep 2025.pdf",
    2026: "FY 2026 Arrivals by Region - Fiscal Year by Month as of "
          "30 Sep 2026.pdf",
}

MONTHS = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar",
          "Apr", "May", "Jun", "Jul", "Aug", "Sep"]
VALUE_COLUMNS = MONTHS + ["Total"]
ROW_COLUMNS = ["page", "row_y", "state_label", "nationality"] + VALUE_COLUMNS
STATE_NAMES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "District of Columbia", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan",
    "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York", "North Carolina",
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas",
    "Utah", "Vermont", "Virginia", "Washington", "West Virginia",
    "Wisconsin", "Wyoming", "Puerto Rico", "Guam", "Not Available",
    "Grand Total",
]
NUMBER = re.compile(r"^(\d{1,3}(,\d{3})*|\d+)$")
# Names the publisher changed between years, mapped to the earlier name.
NATIONALITY_ALIASES = {"The Gambia": "Gambia"}
# Fiscal years whose labels were read by OCR and may be misspelled.
OCR_YEARS = (2022, 2024)
FOOTER_STARTS = ("Based", "Only", "Data", "Please", "*Please", "Any SIV")
# Words closer than this (points) vertically belong to the same table line;
# some files draw labels and numbers on layers about 2 points apart.
LINE_TOLERANCE = 2.5
# Text PDFs are rendered at this resolution only to test whether a word
# leaves ink on the page (clipped text does not). Labels are printed in a
# light gray, so anything darker than the row shading (about 245) is ink.
INK_DPI = 100
INK_LEVEL = 210
MIN_INK = 3


def snap_state(text: str) -> str:
    """
    Returns the state name that text most likely spells (ignoring case), so
    OCR readings such as 'lowa' become 'Iowa'. Returns '' if text is close
    to no state name.
    """
    lowered = {name.lower(): name for name in STATE_NAMES}
    match = difflib.get_close_matches(text.lower().strip(), list(lowered),
                                      n=1, cutoff=0.75)
    if match:
        return lowered[match[0]]
    return ""


def to_count(text: str) -> int | None:
    """
    Returns the count printed as text ('1,274' -> 1274, '' -> 0), or None
    if text is not a count. A period between digit groups ('3.344') is read
    as the thousands comma, since every count is a whole number.
    """
    text = str(text).strip()
    if text in ("", "nan"):
        return 0
    text = re.sub(r"(?<=\d)\.(?=\d{3}(\D|$))", ",", text)
    if NUMBER.match(text):
        return int(text.replace(",", ""))
    return None


def _ink_image(doc: fitz.Document, index: int) -> np.ndarray:
    """
    Returns page index of doc rendered as a grayscale array at INK_DPI.
    """
    pixmap = doc[index].get_pixmap(dpi=INK_DPI, colorspace=fitz.csGRAY)
    shape = (pixmap.height, pixmap.width)
    return np.frombuffer(pixmap.samples, np.uint8).reshape(shape)


def pdf_words(page: pdfplumber.page.Page, image: np.ndarray) -> list[dict]:
    """
    Returns the words on a text PDF page as dicts with the keys text, x0,
    x1, top, bottom (points) and visible. Words are built from characters
    in the order the PDF draws them, not sorted by position: the pages hold
    clipped copies of rows drawn on top of the header, and sorting would
    interleave their letters with the header's. Copies of a word drawn on
    more than one text layer are kept once, and a word is visible only if
    it leaves ink on the rendered page image.
    """
    scale = INK_DPI / 72
    words = []
    seen = set()
    for word in page.extract_words(use_text_flow=True):
        key = (word["text"], round(word["x0"]), round(word["bottom"]))
        if key in seen:
            continue
        seen.add(key)
        area = image[int(word["top"] * scale):int(word["bottom"] * scale) + 1,
                     int(word["x0"] * scale):int(word["x1"] * scale) + 1]
        words.append({"text": word["text"], "x0": word["x0"],
                      "x1": word["x1"], "top": word["top"],
                      "bottom": word["bottom"],
                      "visible": int((area < INK_LEVEL).sum()) >= MIN_INK})
    return words


def _label_starts(header: list[dict]) -> dict:
    """
    Returns the x position where each label column starts, keyed by
    'state' and 'nationality', from the words of the table header. The
    nationality column starts at 'PA', which can be glued to the previous
    header word ('Destin..PA'), so its position inside that word is
    estimated from where it falls in the word's text.
    """
    starts = {}
    for word in header:
        place = word["text"].find("PA")
        if place >= 0 and "nationality" not in starts:
            share = place / len(word["text"])
            starts["nationality"] = word["x0"] + share * (word["x1"] -
                                                          word["x0"])
    state_words = [word["x0"] for word in header
                   if word["text"].startswith(("Affiliate", "Actual",
                                               "State", "Placement"))]
    if state_words:
        starts["state"] = min(state_words)
    return starts


def _split_glued(text: str) -> tuple[str, str]:
    """
    Returns the text of a state label split into the state name and
    whatever follows it. Some files draw a state name and the nationality
    beside it without a gap ('MassachusettsAfghanistan', 'New
    HampshireSouth Africa'), so a label that starts with a state name and
    continues is split after the name. Any other text is returned whole,
    with '' as the second part.
    """
    for name in sorted(STATE_NAMES, key=len, reverse=True):
        if text.startswith(name) and len(text) > len(name):
            return name, text[len(name):].strip()
    return text, ""


def table_layout(words: list[dict]) -> dict | None:
    """
    Returns the column layout of a table page from its words, or None if
    the page prints no month header. The layout holds the 13 value-column
    centres (12 months plus Grand Total), the column width, the left edge
    of the value columns, where each label column starts, and the bottom
    of the header. A month with no arrivals can be left out of the header
    entirely, so the centres are fitted to the month headers printed.
    """
    heads = {}
    for word in words:
        if word["text"] in MONTHS and word["text"] not in heads:
            heads[word["text"]] = word
    if len(heads) < 6 or "Sep" not in heads:
        return None
    index = [MONTHS.index(month) for month in heads]
    middle = [(word["x0"] + word["x1"]) / 2 for word in heads.values()]
    width, intercept = np.polyfit(index, middle, 1)
    centres = [intercept + width * i for i in range(12)]
    header_bottom = max(word["bottom"] for word in heads.values())
    header_top = min(word["top"] for word in heads.values())
    totals = [word for word in words if word["text"] == "Total"
              and word["x0"] > heads["Sep"]["x1"]
              and header_top - 12 < word["top"] < header_bottom + 2]
    if totals:
        centres.append((totals[0]["x0"] + totals[0]["x1"]) / 2)
    else:
        centres.append(centres[-1] + width)
    value_left = centres[0] - width / 2
    header = [word for word in words if word["x1"] < value_left
              and header_top - 12 < word["top"] < header_bottom + 2]
    return {"centres": centres, "width": width, "value_left": value_left,
            "starts": _label_starts(header), "header_bottom": header_bottom}


def words_to_rows(words: list[dict], page_no: int,
                  layout: dict) -> list[dict]:
    """
    Returns the table rows on one page, built from its words (dicts with
    text, x0, x1, top, bottom and visible) and the table's layout (from
    table_layout, possibly from an earlier page when this page prints no
    header), as dicts with the keys of ROW_COLUMNS holding the printed
    strings. Numbers go to the value column whose centre is nearest; words
    left of the value columns form the state and nationality labels, split
    where the header puts each column. Lines from the top of the footer
    down are dropped, because the PDFs carry clipped copies of the next
    page's first row there.
    """
    centres, width = layout["centres"], layout["width"]
    value_left, starts = layout["value_left"], layout["starts"]
    own = table_layout(words)
    header_bottom = own["header_bottom"] if own else 0
    footer_tops = [word["top"] for word in words
                   if word["text"].startswith(FOOTER_STARTS)
                   and word["top"] > header_bottom
                   and word["x0"] < value_left]
    table_bottom = min(footer_tops) if footer_tops else float("inf")
    body = sorted([word for word in words if word["visible"]
                   and word["top"] > header_bottom + 1
                   and word["bottom"] < table_bottom],
                  key=lambda word: word["bottom"])
    lines = []
    for word in body:
        if lines and word["bottom"] - lines[-1][0]["bottom"] < LINE_TOLERANCE:
            lines[-1].append(word)
        else:
            lines.append([word])
    order = sorted(starts, key=lambda name: starts[name])
    rows = []
    for line in lines:
        row = {"page": page_no, "row_y": round(line[0]["bottom"], 1),
               "state_label": "", "nationality": ""}
        for name in VALUE_COLUMNS:
            row[name] = ""
        labels = {name: [] for name in starts}
        for word in sorted(line, key=lambda word: word["x0"]):
            if word["x1"] > value_left and re.search(r"\d", word["text"]):
                centre_x = (word["x0"] + word["x1"]) / 2
                gaps = [abs(centre_x - centre) for centre in centres]
                if min(gaps) <= width * 0.6:
                    row[VALUE_COLUMNS[gaps.index(min(gaps))]] = word["text"]
            elif word["x0"] < value_left:
                column = order[0]
                for name in order:
                    if word["x0"] >= starts[name] - 3:
                        column = name
                labels[column].append(word["text"])
        state = " ".join(labels.get("state", []))
        nationality = " ".join(labels.get("nationality", []))
        if order[0] == "state" and "nationality" in starts:
            state, rest = _split_glued(state)
            nationality = (rest + " " + nationality).strip()
        row["state_label"] = state
        row["nationality"] = nationality
        rows.append(row)
    return rows


def read_text_pdf(path: str) -> pd.DataFrame:
    """
    Returns every table row of the text PDF at path, one row per printed
    line, with the columns of ROW_COLUMNS holding the printed strings. A
    page that prints no month header uses the layout of the page before.
    """
    rows = []
    layout = None
    with pdfplumber.open(path) as pdf, fitz.open(path) as doc:
        for index, page in enumerate(pdf.pages):
            words = pdf_words(page, _ink_image(doc, index))
            layout = table_layout(words) or layout
            if layout:
                rows.extend(words_to_rows(words, index + 1, layout))
    return pd.DataFrame(rows, columns=ROW_COLUMNS)


def _repair(values: list, raw: list[str]) -> list:
    """
    Returns the row's counts with at most one unreadable cell filled in
    from the row sum (Total minus the months, or the months' sum for the
    Total). values holds the counts in VALUE_COLUMNS order, None where the
    cell could not be read; raw holds the printed strings. The filled value
    is kept only if its digits agree with every digit that was read in that
    cell; otherwise the row is returned unchanged.
    """
    missing = [i for i, value in enumerate(values) if value is None]
    if len(missing) != 1:
        return values
    spot = missing[0]
    known = [value for i, value in enumerate(values) if i != spot]
    if spot == 12:
        guess = sum(known)
    else:
        guess = known[-1] - sum(known[:-1])
    printed = "{:,}".format(guess) if guess >= 0 else ""
    seen = raw[spot]
    if len(printed) != len(seen):
        return values
    for want, got in zip(printed, seen):
        if got.isdigit() and got != want:
            return values
    repaired = list(values)
    repaired[spot] = guess
    return repaired


def _state_sequence(labels: list[str]) -> list[str]:
    """
    Returns the state each row belongs to, given each row's printed state
    label ('' where none is printed). A state label is printed once per
    block and carried down; a label split over two lines ('District of',
    'Columbia') is joined before it is matched to a state name.
    """
    states = []
    current = ""
    partial = ""
    for label in labels:
        label = label.strip()
        if label:
            name = snap_state(label)
            joined = snap_state((partial + " " + label).strip())
            if partial and joined:
                current, partial = joined, ""
            elif name:
                current, partial = name, ""
            else:
                partial = (partial + " " + label).strip()
        states.append(current)
    return states


def _carry(labels: list[str]) -> list[str]:
    """
    Returns labels with each blank entry replaced by the last non-blank
    label above it (a label printed once per block applies to every row of
    the block).
    """
    carried = []
    current = ""
    for label in labels:
        if label.strip():
            current = label.strip()
        carried.append(current)
    return carried


def _add(one: list[int], other: list[int]) -> list[int]:
    """
    Returns the element-wise sum of two equal-length lists of counts.
    """
    return [left + right for left, right in zip(one, other)]


def tidy_rows(raw: pd.DataFrame, source: str,
              fiscal_year: int) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """
    Returns the parsed rows of one report as a tidy table plus its checks.
    raw is the output of read_text_pdf or ocr.py, and source says which
    report it is: in the refugee report the state is printed once per block
    and each row is a nationality, with a 'Total' row per state; in the SIV
    report the nationality is printed once per block and each row is a
    state. The tidy table has the columns source, fiscal_year, state,
    nationality, month (1 = October, 13 = the Grand Total column) and
    count. A page's first row that repeats the previous page's last row is
    skipped. The checks dict counts unreadable cells, rows whose months do
    not add up, state blocks that do not add up to their Total row, and
    whether the rows add up to the printed Grand Total row in every column.
    The repairs table lists every cell filled in from its row sum.
    """
    values = []
    repairs = []
    for _, row in raw.iterrows():
        printed = [str(row[name]) if pd.notna(row[name]) else ""
                   for name in VALUE_COLUMNS]
        counts = [to_count(text) for text in printed]
        fixed = _repair(counts, printed)
        for name, before, after, text in zip(VALUE_COLUMNS, counts, fixed,
                                             printed):
            if before is None and after is not None:
                repairs.append({"source": source, "fiscal_year": fiscal_year,
                                "page": row["page"], "row_y": row["row_y"],
                                "nationality": row["nationality"],
                                "column": name, "read": text,
                                "repaired": after, "rule": "row sum"})
        values.append(fixed)
    state_labels = raw["state_label"].fillna("").astype(str).tolist()
    nation_labels = raw["nationality"].fillna("").astype(str).tolist()
    is_grand = [one.startswith("Grand") or other.startswith("Grand")
                for one, other in zip(state_labels, nation_labels)]
    state_labels = ["" if grand else label
                    for label, grand in zip(state_labels, is_grand)]
    if source == "refugee":
        states = _state_sequence(state_labels)
        nations = [label.strip() for label in nation_labels]
    else:
        nations = _carry(["" if grand else label for label, grand
                          in zip(nation_labels, is_grand)])
        states = [snap_state(label) or label.strip()
                  for label in state_labels]
    pages = raw["page"].tolist()
    checks = {"source": source, "fiscal_year": fiscal_year,
              "printed_rows": len(raw), "page_repeats": 0,
              "unreadable_cells": 0, "row_sum_failures": 0,
              "state_blocks": 0, "block_failures": 0,
              "grand_total_printed": None, "grand_total_parsed": 0,
              "grand_matches": None, "repairs": len(repairs)}
    records = []
    blocks = {}
    grand = None
    parsed = [0] * 13
    previous = None
    for index, counts in enumerate(values):
        if None in counts:
            checks["unreadable_cells"] += counts.count(None)
            continue
        if sum(counts[:12]) != counts[12]:
            checks["row_sum_failures"] += 1
        if is_grand[index]:
            grand = grand or counts
            continue
        key = (states[index], nations[index], counts)
        if previous and pages[index] != previous[0] and key == previous[1]:
            checks["page_repeats"] += 1
            continue
        previous = (pages[index], key)
        state, name = states[index], nations[index]
        if source == "refugee":
            block = blocks.setdefault(state, {"printed": [0] * 13,
                                              "parsed": [0] * 13})
            if name.lower() == "total":
                block["printed"] = _add(block["printed"], counts)
                continue
            block["parsed"] = _add(block["parsed"], counts)
        parsed = _add(parsed, counts)
        for month, count in enumerate(counts, start=1):
            if count:
                records.append({"source": source, "fiscal_year": fiscal_year,
                                "state": state, "nationality": name,
                                "month": month, "count": count})
    checks["state_blocks"] = len(blocks)
    has_totals = any(block["printed"] != [0] * 13
                     for block in blocks.values())
    if has_totals:
        checks["block_failures"] = sum(block["printed"] != block["parsed"]
                                       for block in blocks.values())
    checks["grand_total_parsed"] = parsed[12]
    if grand:
        checks["grand_total_printed"] = grand[12]
        checks["grand_matches"] = grand == parsed
    tidy = pd.DataFrame(records, columns=["source", "fiscal_year", "state",
                                          "nationality", "month", "count"])
    return tidy, checks, pd.DataFrame(repairs)


def read_arrivals_excel(path: str, fiscal_year: int) -> pd.DataFrame:
    """
    Returns the annual arrivals in one FY2015-FY2020 Excel file as a tidy
    table with the columns source, fiscal_year, state, nationality, month
    and count, where month is always 13 (these files print only the
    cumulative total for the year).
    """
    raw = pd.read_excel(path, header=None)
    first = raw.iloc[:, 0].astype(str).str.strip()
    start = first[first == "Placement State"].index[0] + 2
    records = []
    state = ""
    for index in range(start, len(raw)):
        cell, name, count = raw.iloc[index, 0], raw.iloc[index, 1], \
            raw.iloc[index, 2]
        if isinstance(cell, str) and cell.strip().lower() == "total":
            break
        if pd.notna(cell):
            state = str(cell).strip()
        elif pd.notna(name) and pd.notna(count) and \
                str(name).strip().lower() != "total":
            records.append({"source": "refugee", "fiscal_year": fiscal_year,
                            "state": state, "nationality": str(name).strip(),
                            "month": 13, "count": int(count)})
    return pd.DataFrame(records)


def excel_printed_total(path: str) -> int:
    """
    Returns the national total printed on the 'Total' line of a
    FY2015-FY2020 Excel arrivals file.
    """
    raw = pd.read_excel(path, header=None)
    first = raw.iloc[:, 0].astype(str).str.strip().str.lower()
    return int(raw.loc[first == "total"].iloc[0, 2])


def read_region_excel(path: str, fiscal_year: int) -> pd.DataFrame:
    """
    Returns the refugee arrivals by region and month in one region Excel
    file, with the columns fiscal_year, region, month (1-12, plus 13 for
    the cumulative total) and count. The FY2016 file prints a refugee and
    an SIV column for each month; only the refugee columns are kept.
    """
    raw = pd.read_excel(path, header=None)
    header = None
    for index in range(len(raw)):
        texts = [str(cell).strip() for cell in raw.iloc[index]]
        if "Oct" in texts and "Sep" in texts:
            header = index
            break
    texts = [str(cell).strip() for cell in raw.iloc[header]]
    below = [str(cell).strip() for cell in raw.iloc[header + 1]]
    split = "Ref" in below
    columns = []
    for month in MONTHS:
        position = texts.index(month)
        columns.append(position)
    if split:
        total_position = below.index("Ref", columns[-1] + 2)
    else:
        total_position = texts.index("Inds") if "Inds" in texts else \
            [str(cell).strip() for cell in raw.iloc[header]].index("Inds")
    columns.append(total_position)
    start = header + (2 if split else 1)
    label = 0
    for row in (texts, below):
        if "PA Region" in row:
            label = row.index("PA Region")
    records = []
    for index in range(start, len(raw)):
        region = raw.iloc[index, label]
        if pd.isna(region) or str(region).startswith(("Please", "*",
                                                      "Based")):
            break
        for month, position in enumerate(columns, start=1):
            records.append({"fiscal_year": fiscal_year,
                            "region": str(region).strip(), "month": month,
                            "count": int(raw.iloc[index, position])})
    return pd.DataFrame(records)


def region_rows_to_table(rows: pd.DataFrame,
                         fiscal_year: int) -> pd.DataFrame:
    """
    Returns region rows (a 'region' label column plus the 13 value columns
    as printed strings) as a table with the columns fiscal_year, region,
    month and count. The national row is named 'Total'.
    """
    records = []
    for _, row in rows.iterrows():
        region = str(row["region"]).strip()
        if region.startswith("Grand"):
            region = "Total"
        for month, name in enumerate(VALUE_COLUMNS, start=1):
            records.append({"fiscal_year": fiscal_year, "region": region,
                            "month": month, "count": to_count(row[name])})
    return pd.DataFrame(records)


def read_region_pdf(path: str) -> pd.DataFrame:
    """
    Returns the region rows of a text region PDF, as a frame with a
    'region' column and the 13 value columns as printed strings. Labels are
    in the single label column. In some years the numbers sit several
    points above their label inside tall rows, so a line of numbers with no
    label is joined to the nearest label line that has no numbers.
    """
    with pdfplumber.open(path) as pdf, fitz.open(path) as doc:
        page = pdf.pages[0]
        words = pdf_words(page, _ink_image(doc, 0))
        table = words_to_rows(words, 1, table_layout(words))
    labelled = []
    loose = []
    for row in table:
        row["region"] = (row["state_label"] + " " +
                         row["nationality"]).strip()
        has_values = any(row[name] for name in VALUE_COLUMNS)
        if row["region"]:
            labelled.append(row)
        elif has_values:
            loose.append(row)
    for row in loose:
        empty = [other for other in labelled
                 if not any(other[name] for name in VALUE_COLUMNS)]
        if empty:
            nearest = min(empty,
                          key=lambda other: abs(other["row_y"] -
                                                row["row_y"]))
            for name in VALUE_COLUMNS:
                nearest[name] = row[name]
    return pd.DataFrame(labelled, columns=["region"] + VALUE_COLUMNS)


def load_region(fiscal_year: int) -> pd.DataFrame:
    """
    Returns the region-by-month table for one fiscal year with the columns
    fiscal_year, region, month and count, whichever format its file is in.
    """
    name = REGION_FILES[fiscal_year]
    if name.endswith(".csv"):
        rows = pd.read_csv(os.path.join(OCR_DIR, name), dtype=str)
        return region_rows_to_table(rows.fillna(""), fiscal_year)
    path = os.path.join(REGION_DIR, name)
    if name.endswith((".xls", ".xlsx")):
        return read_region_excel(path, fiscal_year)
    return region_rows_to_table(read_region_pdf(path), fiscal_year)


def load_report(source: str, fiscal_year: int) -> tuple:
    """
    Returns the tidy table, checks dict and repairs table for one report
    (source 'refugee' or 'siv', and its fiscal year), whatever its format.
    """
    files = ARRIVAL_FILES if source == "refugee" else SIV_FILES
    folder = ARRIVALS_DIR if source == "refugee" else SIV_DIR
    name = files[fiscal_year]
    if name.endswith((".xls", ".xlsx")):
        path = os.path.join(folder, name)
        tidy = read_arrivals_excel(path, fiscal_year)
        printed = excel_printed_total(path)
        checks = {"source": source, "fiscal_year": fiscal_year,
                  "printed_rows": len(tidy), "page_repeats": 0,
                  "unreadable_cells": 0,
                  "row_sum_failures": 0, "state_blocks":
                  tidy["state"].nunique(), "block_failures": 0,
                  "grand_total_printed": printed,
                  "grand_total_parsed": int(tidy["count"].sum()),
                  "grand_matches": printed == int(tidy["count"].sum()),
                  "repairs": 0}
        return tidy, checks, pd.DataFrame()
    if name.endswith(".csv"):
        raw = pd.read_csv(os.path.join(OCR_DIR, name), dtype=str)
        raw = raw.fillna("")
    else:
        raw = read_text_pdf(os.path.join(folder, name))
    return tidy_rows(raw, source, fiscal_year)


def _name_key(name: str) -> str:
    """
    Returns a nationality name reduced to lower-case letters, digits and
    brackets, so spellings that differ only in spacing, case or dots
    ('Dem.Rep. Con..', 'Dem. Rep. Con..') compare equal.
    """
    return re.sub(r"[^a-z0-9()]", "", name.lower())


def nationality_map(arrivals: pd.DataFrame) -> pd.DataFrame:
    """
    Returns the mapping from every printed nationality name in arrivals to
    one standard name, with the columns printed, standard and rule. The
    rules, tried in order: a known rename by the publisher; the same name
    up to spacing, case and dots (the most common spelling wins); a name
    cut short with '..' whose start matches exactly one full name; and,
    for names read by OCR only, the closest full name (difflib ratio of at
    least 0.8). Names that match none of these are kept as printed.
    """
    usage = arrivals.groupby("nationality").agg(
        rows=("count", "size"),
        ocr_only=("fiscal_year", lambda years: set(years) <= set(OCR_YEARS)))
    full = usage[[not name.endswith("..") for name in usage.index]]
    spelling = {}
    for name, row in full.sort_values("rows").iterrows():
        spelling[_name_key(name)] = name
    reference = [name for name, row in full.iterrows()
                 if not row["ocr_only"]]
    rows = []
    for name, row in usage.iterrows():
        key = _name_key(name)
        standard, rule = name, "unchanged"
        if name in NATIONALITY_ALIASES:
            standard, rule = NATIONALITY_ALIASES[name], "renamed"
        elif name.endswith(".."):
            start = _name_key(name.rstrip("."))
            matches = {spelling[_name_key(other)] for other in full.index
                       if _name_key(other).startswith(start)}
            if len(matches) == 1:
                standard, rule = matches.pop(), "truncated"
        elif row["ocr_only"] and key not in [_name_key(other)
                                             for other in reference]:
            close = difflib.get_close_matches(name, reference, n=1,
                                              cutoff=0.8)
            if close:
                standard, rule = spelling[_name_key(close[0])], "ocr spelling"
        elif spelling[key] != name:
            standard, rule = spelling[key], "spacing or case"
        rows.append({"printed": name, "standard": standard, "rule": rule})
    return pd.DataFrame(rows)


def load_all() -> dict:
    """
    Returns every parsed table, keyed by name: 'arrivals' (tidy arrivals
    from both reports, all years, with standardized nationality names and
    the printed name kept beside them), 'region' (region-by-month tables),
    'checks' (one row of checks per report, including the comparison of
    each year's monthly national totals with the region report), 'repairs'
    (cells filled in from their row sums) and 'nationality_map' (how each
    printed name was standardized).
    """
    tidy, checks, repairs = [], [], []
    for source, files in (("refugee", ARRIVAL_FILES), ("siv", SIV_FILES)):
        for year in sorted(files):
            frame, check, fixed = load_report(source, year)
            tidy.append(frame)
            checks.append(check)
            repairs.append(fixed)
    arrivals = pd.concat(tidy, ignore_index=True)
    names = nationality_map(arrivals)
    standard = dict(zip(names["printed"], names["standard"]))
    arrivals["printed_nationality"] = arrivals["nationality"]
    arrivals["nationality"] = arrivals["nationality"].map(standard)
    region = pd.concat([load_region(year) for year in sorted(REGION_FILES)],
                       ignore_index=True)
    checks = pd.DataFrame(checks)
    gaps = region_gaps(arrivals, region)
    checks = checks.merge(gaps, on=["source", "fiscal_year"], how="left")
    return {"arrivals": arrivals, "region": region, "checks": checks,
            "repairs": pd.concat(repairs, ignore_index=True),
            "nationality_map": names}


def region_gaps(arrivals: pd.DataFrame, region: pd.DataFrame) -> pd.DataFrame:
    """
    Returns, for each refugee year, how far the parsed national totals are
    from the national row of the region report: the columns source,
    fiscal_year, region_total (the region report's annual total),
    region_month_gaps (number of months whose totals differ; missing for
    the Excel years, which have no months) and region_total_gap (parsed
    annual total minus the region report's).
    """
    national = region[region["region"] == "Total"]
    refugee = arrivals[arrivals["source"] == "refugee"]
    parsed = refugee.groupby(["fiscal_year", "month"])["count"].sum()
    rows = []
    for year in sorted(refugee["fiscal_year"].unique()):
        printed = national[national["fiscal_year"] == year]
        printed = printed.set_index("month")["count"]
        mine = parsed.loc[year]
        row = {"source": "refugee", "fiscal_year": year,
               "region_total": None, "region_month_gaps": None,
               "region_total_gap": None}
        if 13 in printed.index:
            row["region_total"] = int(printed[13])
            row["region_total_gap"] = int(mine.get(13, 0) - printed[13])
        if len(mine) > 1:
            row["region_month_gaps"] = sum(
                int(mine.get(month, 0)) != int(printed.get(month, 0))
                for month in range(1, 13))
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    tables = load_all()
    pd.set_option("display.width", 200)
    print(tables["checks"].to_string(index=False))
    for name, table in tables.items():
        table.to_csv(os.path.join(OUT_DIR, name + ".csv"), index=False)


if __name__ == "__main__":
    main()
