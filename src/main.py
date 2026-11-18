"""
Charlie Cheng, Zhongtian Liu
CSE 163
Runs the whole EDA: recovers the image-only tables (OCR), downloads the
Census tables, parses every report, computes the tables in the report, and
draws the figures. The OCR step (about ten minutes) and the Census download
(needs a key and a network connection) run only when their saved outputs
are missing, so the rest of the pipeline can be re-run quickly from them.
"""

import os

import acs
import analysis
import figures
import ocr
import parse

OCR_OUTPUTS = ["fy2022_arrivals.csv", "fy2024_arrivals.csv",
               "fy2024_region.csv"]
ACS_OUTPUTS = ["acs_state.csv", "acs_counties.csv", "acs_birth.csv"]


def missing(folder: str, names: list) -> bool:
    """
    Returns True if any of the named files is missing from folder.
    """
    return not all(os.path.exists(os.path.join(folder, name))
                   for name in names)


def main():
    if missing(ocr.OCR_DIR, OCR_OUTPUTS):
        ocr.main()
    if missing(acs.OUT_DIR, ACS_OUTPUTS):
        acs.main()
    parse.main()
    analysis.main()
    figures.main()
    print("EDA complete: see data/processed/, outputs/ and figures/")


if __name__ == "__main__":
    main()
