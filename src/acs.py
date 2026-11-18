"""
Charlie Cheng, Zhongtian Liu
CSE 163
Downloads the Census tables the project needs into CSV files: the 2024
ACS five-year estimates for B16001 (detailed language spoken at home,
Washington State), C16001 (language spoken at home, every Washington
county) and B05006 (place of birth, every Washington county), each with its
margins of error. Columns are named by the Census variable labels.
"""

import json
import os
import urllib.request

import pandas as pd

KEY_FILE = os.path.join(
    "Dataset", "American_Community_Survey_5-year_Estimates(2024)",
    "ACSKEY.txt")
OUT_DIR = os.path.join("data", "processed")
API = "https://api.census.gov/data/2024/acs/acs5"
# The API accepts at most 50 variables per request.
CHUNK = 45
STATE_QUERY = "for=state:53"
COUNTY_QUERY = "for=county:*&in=state:53"


def read_key() -> str:
    """
    Returns the Census API key stored with the data.
    """
    with open(KEY_FILE, encoding="utf-8") as handle:
        return handle.read().strip()


def group_labels(table: str) -> dict:
    """
    Returns {variable name: label} for every variable of one ACS table.
    """
    url = "{}/groups/{}.json".format(API, table)
    with urllib.request.urlopen(url, timeout=60) as response:
        data = json.load(response)
    return {name: info["label"] for name, info in data["variables"].items()
            if "label" in info}


def estimate_variables(labels: dict) -> list:
    """
    Returns the estimate and margin-of-error variable names of a table, in
    table order with each estimate before its margin.
    """
    names = [name for name in labels
             if name.endswith(("E", "M")) and "_" in name]
    return sorted(names, key=lambda name: (int(name.split("_")[1][:-1]),
                                           name[-1] != "E"))


def fetch(variables: list, query: str, key: str) -> pd.DataFrame:
    """
    Returns the given variables for the geographies in query (one row per
    geography), fetched in chunks and joined on the geography codes.
    """
    frames = []
    for start in range(0, len(variables), CHUNK):
        block = variables[start:start + CHUNK]
        names = block if start else ["NAME"] + block
        url = "{}?get={}&{}&key={}".format(API, ",".join(names), query, key)
        with urllib.request.urlopen(url, timeout=120) as response:
            payload = json.load(response)
        frames.append(pd.DataFrame(payload[1:], columns=payload[0]))
    merged = frames[0]
    keys = [name for name in ("state", "county") if name in merged.columns]
    for frame in frames[1:]:
        merged = merged.merge(frame, on=keys)
    return merged


def download(table: str, query: str, key: str) -> pd.DataFrame:
    """
    Returns one ACS table for the geographies in query, with its columns
    renamed to the Census variable labels.
    """
    labels = group_labels(table)
    names = estimate_variables(labels)
    frame = fetch(names, query, key)
    return frame.rename(columns={name: labels[name] for name in names})


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    key = read_key()
    jobs = [("B16001", STATE_QUERY, "acs_state.csv"),
            ("C16001", COUNTY_QUERY, "acs_counties.csv"),
            ("B05006", COUNTY_QUERY, "acs_birth.csv")]
    for table, query, name in jobs:
        frame = download(table, query, key)
        frame.to_csv(os.path.join(OUT_DIR, name), index=False)
        print(table, frame.shape)


if __name__ == "__main__":
    main()
