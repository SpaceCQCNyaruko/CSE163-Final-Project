"""Download the Census tables the project needs into tidy CSV files.

The files collected by hand earlier were one-year tables for the whole
country, so the state and county rows the analysis needs were missing. This
module pulls the 2024 five-year estimates directly from the Census API: one
state row for B16001 (languages) and one row per Washington county for
C16001 (languages) and B05006 (place of birth).
"""

import json
import os
import urllib.request

import pandas as pd

KEY_FILE = os.path.join(
    "Dataset", "American_Community_Survey_5-year_Estimates(2024)",
    "ACSKEY.txt",
)
OUT_DIR = os.path.join("data", "processed")
API = "https://api.census.gov/data/2024/acs/acs5"
CHUNK = 45


def read_key():
    """Read the Census API key from the file collected with the data."""
    with open(KEY_FILE, encoding="utf-8") as handle:
        return handle.read().strip()


def group_labels(table):
    """Return {variable: label} for one ACS table."""
    url = "{}/groups/{}.json".format(API, table)
    with urllib.request.urlopen(url, timeout=60) as response:
        data = json.load(response)
    return {
        name: info["label"]
        for name, info in data["variables"].items()
        if "label" in info
    }


def fetch(table, variables, query, key):
    """Fetch the given variables in chunks and merge them on geography."""
    frames = []
    for start in range(0, len(variables), CHUNK):
        block = variables[start:start + CHUNK]
        names = block if start else ["NAME"] + block
        url = "{}?get={}&{}&key={}".format(
            API, ",".join(names), query, key
        )
        with urllib.request.urlopen(url, timeout=120) as response:
            payload = json.load(response)
        frames.append(pd.DataFrame(payload[1:], columns=payload[0]))
    merged = frames[0]
    keys = [name for name in ("state", "county") if name in merged.columns]
    for frame in frames[1:]:
        extra = [c for c in ("NAME",) if c in frame.columns]
        merged = merged.merge(frame.drop(columns=extra), on=keys)
    return merged


def estimate_variables(labels):
    """Keep the estimate and margin columns of a table, in table order."""
    names = [
        name for name in labels
        if (name.endswith("E") or name.endswith("M")) and "_" in name
    ]
    names.sort(key=lambda name: (
        int(name.split("_")[1][:-1]), name[-1] != "E"
    ))
    return names


def main():
    """Pull B16001, C16001 and B05006 and write tidy CSV files."""
    os.makedirs(OUT_DIR, exist_ok=True)
    key = read_key()

    labels = group_labels("B16001")
    names = estimate_variables(labels)
    state = fetch("B16001", names, "for=state:53", key)
    state = state.rename(columns={name: labels[name] for name in names})
    state.to_csv(os.path.join(OUT_DIR, "acs_state.csv"), index=False)

    labels = group_labels("C16001")
    names = estimate_variables(labels)
    counties = fetch("C16001", names, "for=county:*&in=state:53", key)
    counties = counties.rename(
        columns={name: labels[name] for name in names}
    )
    counties.to_csv(
        os.path.join(OUT_DIR, "acs_counties.csv"), index=False
    )

    labels = group_labels("B05006")
    names = estimate_variables(labels)
    born = fetch("B05006", names, "for=county:*&in=state:53", key)
    born = born.rename(columns={name: labels[name] for name in names})
    born.to_csv(os.path.join(OUT_DIR, "acs_birth.csv"), index=False)

    print("state", state.shape, "counties", counties.shape,
          "birth", born.shape)


if __name__ == "__main__":
    main()
