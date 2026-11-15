"""
Charlie Cheng
CSE 163 AB

Run the whole EDA: parse the published reports, pull the Census tables,
compute the tables in the report, and render the figures.
"""

import acs
import analysis
import figures
import parse


def main():
    """Run each stage in the order the report depends on."""
    parse.main()
    acs.main()
    analysis.main()
    figures.main()
    print("EDA complete: see outputs/ and figures/")


if __name__ == "__main__":
    main()
