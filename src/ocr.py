"""
Charlie Cheng, Zhongtian Liu
CSE 163
Recovers the three published tables whose numbers cannot be read as text:
the FY2022 arrivals report (scanned page images), the FY2024 arrivals report
(text drawn in scrambled Type3 fonts), and the FY2024 region report (a single
picture). Each table is written to data/ocr/ as the raw strings that were
read, one row per table row, so parse.py can check and load it like any
other year.
"""

import os
import re
from collections import Counter

import cv2
import fitz
import numpy as np
import pandas as pd
import pdfplumber
from rapidocr_onnxruntime import RapidOCR

from parse import (MONTHS, NUMBER, ROW_COLUMNS, VALUE_COLUMNS, snap_state,
                   table_layout, words_to_rows)

ARRIVALS_DIR = os.path.join("Dataset",
                            "Refugee_Arrivals_by_State_and_Nationality")
REGION_DIR = os.path.join("Dataset", "Refugee_Arrivals_by_Region")
SCANNED_FILE = os.path.join(
    ARRIVALS_DIR,
    "FY 2022 Arrivals by State and Nationality as of 30 Sep 2022.pdf")
TYPE3_FILE = os.path.join(
    ARRIVALS_DIR,
    "FY 2024 Arrivals by State and Nationality as of 30 Oct 2024_updated.pdf")
REGION_IMAGE_FILE = os.path.join(
    REGION_DIR,
    "FY 2024 Arrivals by Region - Fiscal Year by Month as of 30 Sep 2024.pdf")
OCR_DIR = os.path.join("data", "ocr")

# The scanned footer is often split into several detected boxes, so any box
# containing one of these words marks the end of the table.
FOOTER_MARKERS = ("Based on", "Only Afghan", "Data provided", "settlement",
                  "Doe et", "admissions")

# A pixel darker than INK_LEVEL counts as ink; a cell needs MIN_INK of them.
INK_LEVEL = 140
MIN_INK = 8
# Page 1 of the scanned file has a text layer instead of an image; render it
# at the scans' own resolution (2 pixels per point) so one grid fits both.
SCAN_DPI = 144
# The Type3 pages are rendered sharper because only word crops are read.
TYPE3_DPI = 300
# Header words must sit in the top part of the page.
HEADER_ZONE = 0.35


def new_engine() -> RapidOCR:
    """
    Returns a RapidOCR engine (text detection plus recognition models).
    """
    return RapidOCR()


def has_ink(cell: np.ndarray) -> bool:
    """
    Returns True if the grayscale image cell contains enough dark pixels to
    hold a printed character, False for a blank or shaded-only cell.
    """
    return int((cell < INK_LEVEL).sum()) >= MIN_INK


def recognize(engine: RapidOCR, images: list[np.ndarray]) -> list[str]:
    """
    Returns the text the recognition model reads in each grayscale image,
    in the same order. Each image must hold a single line of text.
    """
    if not images:
        return []
    colour = [cv2.cvtColor(image, cv2.COLOR_GRAY2BGR) for image in images]
    results, _ = engine.text_recognizer(colour)
    return [text for text, _ in results]


def _pad(image: np.ndarray, size: int) -> np.ndarray:
    """
    Returns the grayscale image with a white border of the given size.
    """
    return cv2.copyMakeBorder(image, size, size, size, size,
                              cv2.BORDER_CONSTANT, value=255)


def read_cell(engine: RapidOCR, cell: np.ndarray) -> str:
    """
    Returns the text printed in one table cell (a grayscale image that has
    ink). The cell is cropped to its ink before reading. A lone character is
    hard for the model to read on its own, so when the cell holds a single
    glyph, or the first reading is not a number, the glyph is read twice
    side by side and the reading is kept only if both halves agree.
    """
    rows, cols = np.where(cell < INK_LEVEL)
    tight = cell[rows.min():rows.max() + 1, cols.min():cols.max() + 1]
    height = tight.shape[0]
    margin = max(4, height // 3)
    text = recognize(engine, [_pad(tight, margin)])[0].strip()
    count, _ = cv2.connectedComponents((tight < INK_LEVEL).astype(np.uint8))
    if count - 1 == 1 or not NUMBER.match(text):
        gap = np.full((height, max(3, height // 2)), 255, np.uint8)
        doubled = _pad(np.hstack([tight, gap, tight]), margin)
        twice = recognize(engine, [doubled])[0].strip()
        half = len(twice) // 2
        if len(twice) % 2 == 0 and twice[:half] == twice[half:] and \
                NUMBER.match(twice[:half]):
            return twice[:half]
    return text


def detect_boxes(engine: RapidOCR, gray: np.ndarray) -> list[dict]:
    """
    Returns every text box the detector finds in the grayscale page image,
    as dicts with the keys text, x0, x1, y0, y1 and yc (pixel units).
    """
    colour = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    found, _ = engine(colour)
    boxes = []
    for corners, text, _ in found or []:
        xs = [point[0] for point in corners]
        ys = [point[1] for point in corners]
        boxes.append({"text": text.strip(), "x0": min(xs), "x1": max(xs),
                      "y0": min(ys), "y1": max(ys),
                      "yc": (min(ys) + max(ys)) / 2})
    return boxes


def fit_columns(boxes: list[dict], page_height: float) -> dict:
    """
    Returns the value-column layout of a table page from its detected text
    boxes: the 13 column centres (12 months plus Grand Total), the column
    width, and the bottom of the header row. The month centres are fitted
    with a straight line, so a header word the detector misreads does not
    lose its column.
    """
    heads = {}
    for box in boxes:
        word = box["text"].title()
        if word in MONTHS and box["y0"] < page_height * HEADER_ZONE:
            heads[word] = box
    if len(heads) < 6:
        raise ValueError("only {} month headers found".format(len(heads)))
    index = [MONTHS.index(month) for month in heads]
    centre = [(box["x0"] + box["x1"]) / 2 for box in heads.values()]
    slope, intercept = np.polyfit(index, centre, 1)
    centres = [intercept + slope * i for i in range(12)]
    totals = [box for box in boxes
              if box["text"] == "Total" and box["x0"] > centres[-1]
              and box["y0"] < page_height * HEADER_ZONE]
    if totals:
        centres.append((totals[0]["x0"] + totals[0]["x1"]) / 2)
    else:
        centres.append(centres[-1] + slope)
    return {"centres": centres, "width": slope,
            "header_bottom": max(box["y1"] for box in heads.values())}


def page_gray(doc: fitz.Document, index: int) -> np.ndarray:
    """
    Returns page index of doc as a grayscale image. A page that is one
    full-page scan returns that scan at its own resolution; any other page
    (text, vector outlines, or a small logo image) is rendered at SCAN_DPI.
    """
    page = doc[index]
    images = page.get_images()
    full_page = False
    if len(images) == 1:
        rects = page.get_image_rects(images[0][0])
        full_page = bool(rects) and \
            rects[0].width * rects[0].height > 0.9 * page.rect.get_area()
    if full_page:
        pixmap = fitz.Pixmap(doc, images[0][0])
        if pixmap.n != 1:
            pixmap = fitz.Pixmap(fitz.csGRAY, pixmap)
    else:
        pixmap = page.get_pixmap(dpi=SCAN_DPI, colorspace=fitz.csGRAY)
    shape = (pixmap.height, pixmap.width)
    return np.frombuffer(pixmap.samples, np.uint8).reshape(shape).copy()


def _row_grid(labels: list[dict], header_bottom: float,
              limit: float) -> list[float]:
    """
    Returns the y centre of every table row on a page. Tableau draws rows
    at a fixed pitch, so the pitch is fitted from the label boxes that were
    detected and the grid is extended from just below the header down to
    the footer. Rows whose labels the detector missed are kept this way.
    """
    centres = [box["yc"] for box in labels]
    pitch = float(np.median(np.diff(centres)))
    steps = [round((y - centres[0]) / pitch) for y in centres]
    pitch, first = np.polyfit(steps, centres, 1)
    while first - pitch > header_bottom + 4:
        first -= pitch
    grid = []
    centre = first
    while centre + pitch / 4 < limit:
        grid.append(centre)
        centre += pitch
    return grid


def nationality_left(boxes: list[dict], default: float) -> float:
    """
    Returns the x position (pixels) where the 'PA Nationality' header
    starts, or default if the header was not read. The detector sometimes
    joins it with the state header into one box, so its position inside
    that box is estimated from where the words fall in the box's text.
    """
    for box in boxes:
        found = re.search(r"PA\s?Na", box["text"])
        if found:
            share = found.start() / len(box["text"])
            return box["x0"] + share * (box["x1"] - box["x0"])
    return default


def read_scanned_page(engine: RapidOCR, gray: np.ndarray, page_no: int,
                      default_left: float) -> tuple[list[dict], float]:
    """
    Returns the table rows on one scanned arrivals page as dicts with the
    keys of ROW_COLUMNS, together with the x position of the nationality
    column. Values are the raw strings read from each cell, with '' for a
    blank cell. State labels are only filled on the row where the page
    prints them. default_left is the nationality column position to use if
    this page's header cannot be read.
    """
    boxes = detect_boxes(engine, gray)
    layout = fit_columns(boxes, gray.shape[0])
    centres, width = layout["centres"], layout["width"]
    header_bottom = layout["header_bottom"]
    found_left = nationality_left(boxes, default_left)
    label_left = found_left - 4
    value_left = centres[0] - width / 2
    below = [box for box in boxes if box["yc"] > header_bottom + 4
             and re.search("[A-Za-z]", box["text"])]
    labels = sorted([box for box in below if box["x0"] >= label_left - 4
                     and box["x1"] < value_left + 5],
                    key=lambda box: box["yc"])
    states = [box for box in below if box["x1"] < label_left]
    footers = [box["y0"] for box in below
               if any(marker in box["text"] for marker in FOOTER_MARKERS)]
    limit = min(footers) if footers else gray.shape[0]
    grid = _row_grid(labels, header_bottom, limit)
    pitch = grid[1] - grid[0] if len(grid) > 1 else 20.0
    rows = []
    for centre in grid:
        top, bottom = int(centre - pitch / 2), int(centre + pitch / 2)
        if not has_ink(gray[top:bottom, int(label_left):]):
            continue
        near = [box for box in labels if abs(box["yc"] - centre) < pitch / 2]
        label_cell = gray[top:bottom, int(label_left):int(value_left)]
        if near:
            nationality = near[0]["text"]
        elif has_ink(label_cell):
            nationality = read_cell(engine, label_cell)
        else:
            nationality = ""
        state = [box["text"] for box in states
                 if abs(box["yc"] - centre) < pitch / 2]
        row = {"page": page_no, "row_y": round(centre),
               "state_label": (snap_state(state[0]) or state[0])
               if state else "",
               "nationality": nationality}
        for name, middle in zip(VALUE_COLUMNS, centres):
            cell = gray[top:bottom,
                        int(middle - width / 2):int(middle + width / 2)]
            row[name] = read_cell(engine, cell) if has_ink(cell) else ""
        # A line with letters in the value columns is the footer sentence,
        # which the detector does not always box: the table has ended.
        if any(re.search("[A-Za-z]", row[name]) for name in VALUE_COLUMNS):
            break
        rows.append(row)
    return rows, found_left


def read_scanned_pdf(engine: RapidOCR, path: str) -> pd.DataFrame:
    """
    Returns every table row of the scanned arrivals PDF at path, one row
    per printed row, with the columns of ROW_COLUMNS.
    """
    rows = []
    left = 0.0
    with fitz.open(path) as doc:
        for index in range(len(doc)):
            gray = page_gray(doc, index)
            page_rows, left = read_scanned_page(engine, gray, index + 1,
                                                left)
            rows.extend(page_rows)
    return pd.DataFrame(rows, columns=ROW_COLUMNS)


def glyph_words(page: pdfplumber.page.Page) -> list[dict]:
    """
    Returns the words drawn on a Type3-font page as dicts with the glyph
    codes in order and the word's box in points (x0, x1, top, bottom) plus
    its baseline. Boxes come from each glyph's text matrix, because the
    font metrics in these files report the wrong heights. Glyphs are taken
    in drawing order rather than sorted by position: some pages draw a
    clipped, invisible label on top of the header, and sorting would
    interleave its letters with the header's.
    """
    height = float(page.height)
    glyphs = []
    for char in page.chars:
        matrix = char["matrix"]
        glyphs.append({"code": char["text"], "x": matrix[4],
                       "base": height - matrix[5], "size": matrix[0]})
    words = []
    for glyph in glyphs:
        last = words[-1] if words else None
        if last and abs(glyph["base"] - last["base"]) < 0.6 and \
                0 < glyph["x"] - last["end"] < 1.2 * glyph["size"]:
            last["codes"].append(glyph["code"])
            last["end"] = glyph["x"]
        else:
            words.append({"codes": [glyph["code"]], "x0": glyph["x"],
                          "end": glyph["x"], "base": glyph["base"],
                          "size": glyph["size"]})
    for word in words:
        word["x1"] = word["end"] + 0.65 * word["size"]
        word["top"] = word["base"] - 0.85 * word["size"]
        word["bottom"] = word["base"] + 0.25 * word["size"]
    return words


def decode_page(engine: RapidOCR, page: pdfplumber.page.Page,
                gray: np.ndarray, scale: float) -> list[dict]:
    """
    Returns the words of one Type3 page with their decoded text. Each page
    has its own font in which every glyph code stands for one character.
    Every word is read by OCR from the rendered page (gray, scale pixels
    per point); each reading whose length matches the word votes for the
    character behind each code, and the majority decides. Words are then
    spelled from their codes, so a digit the OCR misreads in one place is
    still decoded correctly from its votes elsewhere. A word with a code
    that never received a vote keeps its OCR reading. Each word also gets
    a 'visible' flag: the text layer holds clipped copies of rows that
    continue on the next page, and those leave no ink on the rendered page.
    """
    words = glyph_words(page)
    crops = []
    for word in words:
        left = max(0, int(word["x0"] * scale) - 3)
        right = int(word["x1"] * scale) + 3
        top = max(0, int(word["top"] * scale) - 3)
        bottom = int(word["bottom"] * scale) + 3
        area = gray[top:bottom, left:right]
        word["visible"] = has_ink(area)
        crops.append(_pad(area, 10))
    readings = recognize(engine, crops)
    votes = {}
    for word, reading in zip(words, readings):
        word["ocr"] = reading
        for text in (reading, reading.replace(" ", "")):
            if len(text) == len(word["codes"]):
                for code, char in zip(word["codes"], text):
                    votes.setdefault(code, Counter())[char] += 1
                break
    key = {code: count.most_common(1)[0][0]
           for code, count in votes.items()}
    for word in words:
        if all(code in key for code in word["codes"]):
            word["text"] = "".join(key[code] for code in word["codes"])
        else:
            word["text"] = word["ocr"]
        word["text"] = word["text"].strip()
    return words


def read_type3_pdf(engine: RapidOCR, path: str) -> pd.DataFrame:
    """
    Returns every table row of the Type3-font arrivals PDF at path, one row
    per printed row, with the columns of ROW_COLUMNS.
    """
    scale = TYPE3_DPI / 72
    rows = []
    layout = None
    with pdfplumber.open(path) as pdf, fitz.open(path) as doc:
        for index, page in enumerate(pdf.pages):
            pixmap = doc[index].get_pixmap(dpi=TYPE3_DPI,
                                           colorspace=fitz.csGRAY)
            gray = np.frombuffer(pixmap.samples, np.uint8).reshape(
                pixmap.height, pixmap.width)
            words = decode_page(engine, page, gray, scale)
            layout = table_layout(words) or layout
            rows.extend(words_to_rows(words, index + 1, layout))
    return pd.DataFrame(rows, columns=ROW_COLUMNS)


def read_region_image(engine: RapidOCR, path: str) -> pd.DataFrame:
    """
    Returns the region-by-month table in the single-image region PDF at
    path: one row per printed row (the Grand Total row and each region),
    with a 'region' column and the 13 value columns as raw strings.
    """
    with fitz.open(path) as doc:
        gray = page_gray(doc, 0)
    boxes = detect_boxes(engine, gray)
    layout = fit_columns(boxes, gray.shape[0])
    centres, width = layout["centres"], layout["width"]
    value_left = centres[0] - width / 2
    labels = sorted([box for box in boxes
                     if box["yc"] > layout["header_bottom"] + 4
                     and box["x1"] < value_left
                     and re.search("[A-Za-z]", box["text"])
                     and not any(marker in box["text"]
                                 for marker in FOOTER_MARKERS)],
                    key=lambda box: box["yc"])
    labels = [box for box in labels if not box["text"].startswith("FY")]
    pitch = float(np.median(np.diff([box["yc"] for box in labels])))
    rows = []
    for box in labels:
        if box["yc"] - labels[0]["yc"] > pitch * (len(labels) + 0.5):
            break
        top = int(box["yc"] - pitch / 2)
        bottom = int(box["yc"] + pitch / 2)
        row = {"region": box["text"]}
        for name, middle in zip(VALUE_COLUMNS, centres):
            cell = gray[top:bottom,
                        int(middle - width / 2):int(middle + width / 2)]
            row[name] = read_cell(engine, cell) if has_ink(cell) else ""
        rows.append(row)
    return pd.DataFrame(rows, columns=["region"] + VALUE_COLUMNS)


def main():
    os.makedirs(OCR_DIR, exist_ok=True)
    engine = new_engine()
    jobs = [
        ("fy2024_region.csv", read_region_image, REGION_IMAGE_FILE),
        ("fy2024_arrivals.csv", read_type3_pdf, TYPE3_FILE),
        ("fy2022_arrivals.csv", read_scanned_pdf, SCANNED_FILE),
    ]
    for name, reader, path in jobs:
        table = reader(engine, path)
        table.to_csv(os.path.join(OCR_DIR, name), index=False)
        print(name, len(table), "rows")


if __name__ == "__main__":
    main()
