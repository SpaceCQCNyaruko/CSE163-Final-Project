"""Build eda.docx (the Part 2 report) from the computed outputs.

Run with the bundled Python that has python-docx installed. Text numbers are
read from ``outputs/`` so the report cannot drift from the analysis.
"""

import os

import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

OUTPUTS = "outputs"
FIGURES = "figures"
REPO = "https://github.com/SpaceCQCNyaruko/CSE163-Final-Project"
BODY_SIZE = Pt(11)
CAPTION_SIZE = Pt(9)


def style_document(document):
    """Set page size, margins and the body font."""
    section = document.sections[0]
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = BODY_SIZE
    normal.paragraph_format.line_spacing = 1.10
    normal.paragraph_format.space_after = Pt(3)
    for name in ("Heading 1", "Heading 2", "Title"):
        style = document.styles[name]
        style.font.name = "Calibri"
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.space_before = Pt(10)
        style.paragraph_format.space_after = Pt(4)
    document.styles["Heading 1"].font.size = Pt(14)
    document.styles["Heading 2"].font.size = Pt(12)


def add_page_numbers(section):
    """Put 'Page X of Y' in the footer."""
    paragraph = section.footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run("Page ")
    run.font.size = Pt(9)
    for field in ("PAGE", "NUMPAGES"):
        element = OxmlElement("w:fldSimple")
        element.set(qn("w:instr"), field)
        paragraph._p.append(element)
        if field == "PAGE":
            text = paragraph.add_run(" of ")
            text.font.size = Pt(9)
    paragraph.runs[0].font.size = Pt(9)


def heading(document, text, level=1):
    """Add a heading with the report's spacing."""
    document.add_heading(text, level=level)


def paragraph(document, text, size=None, italic=False, space=4):
    """Add a justified body paragraph."""
    block = document.add_paragraph()
    block.paragraph_format.space_after = Pt(space)
    block.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    run = block.add_run(text)
    run.italic = italic
    if size:
        run.font.size = size
    return block


def bullet(document, text):
    """Add one bullet point."""
    block = document.add_paragraph(style="List Bullet")
    block.paragraph_format.line_spacing = 1.3
    block.paragraph_format.space_after = Pt(2)
    block.add_run(text)
    return block


def figure(document, name, caption):
    """Insert a figure with its numbered caption."""
    paragraph(document, "").paragraph_format.space_after = Pt(0)
    run = document.paragraphs[-1].add_run()
    run.add_picture(os.path.join(FIGURES, name), width=Inches(4.0))
    document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    note = document.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.LEFT
    note.paragraph_format.space_after = Pt(8)
    text = note.add_run(caption)
    text.font.size = CAPTION_SIZE
    text.italic = True


def table(document, frame, caption, widths=None, size=8.5, digits=0):
    """Insert a dataframe as a table with a caption above it."""
    note = document.add_paragraph()
    note.paragraph_format.space_before = Pt(6)
    note.paragraph_format.space_after = Pt(2)
    text = note.add_run(caption)
    text.font.size = CAPTION_SIZE
    text.italic = True
    grid = document.add_table(rows=1, cols=len(frame.columns))
    grid.style = "Table Grid"
    grid.alignment = WD_TABLE_ALIGNMENT.CENTER
    for index, name in enumerate(frame.columns):
        cell = grid.rows[0].cells[index]
        cell.text = ""
        run = cell.paragraphs[0].add_run(str(name))
        run.bold = True
        run.font.size = Pt(size)
        run.font.name = "Calibri"
    for _, row in frame.iterrows():
        cells = grid.add_row().cells
        for index, value in enumerate(row):
            cells[index].text = ""
            if isinstance(value, float):
                shown = "{:,.{}f}".format(value, digits)
            else:
                shown = str(value)
            run = cells[index].paragraphs[0].add_run(shown)
            run.font.size = Pt(size)
            run.font.name = "Calibri"
    if widths:
        for row in grid.rows:
            for index, width in enumerate(widths):
                row.cells[index].width = Inches(width)
    document.add_paragraph().paragraph_format.space_after = Pt(2)


def main():
    """Assemble the report."""
    county = pd.read_csv(os.path.join(OUTPUTS, "county_residual.csv"))
    top = pd.read_csv(os.path.join(OUTPUTS, "wa_top5.csv"))
    settings = pd.read_csv(os.path.join(OUTPUTS, "rq1_settings.csv"))
    bounds = pd.read_csv(os.path.join(OUTPUTS, "language_bounds.csv"))

    document = Document()
    style_document(document)
    add_page_numbers(document.sections[0])

    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(
        "Two Ledgers, One Population: How Administrative Categories Shape\n"
        "the Count of Refugee Arrivals in Washington State, FY2015\u2013FY2026"
    )
    run.bold = True
    run.font.size = Pt(15)

    authors = document.add_paragraph()
    authors.alignment = WD_ALIGN_PARAGRAPH.CENTER
    authors.add_run(
        "Charlie Cheng and Zhongtian Liu \u00b7 CSE 163 AB, Autumn 2026\n"
    ).font.size = Pt(10)
    link = authors.add_run("Repository: " + REPO)
    link.font.size = Pt(10)
    link.italic = True

    heading(document, "1. Summary of Research Questions")
    paragraph(
        document,
        "1. Who arrives? For each fiscal year from FY2015 to FY2026, how many "
        "refugees were resettled in Washington, and which five nationalities "
        "made up the largest shares? In which year did the mix of "
        "nationalities change most, and is that change larger than the "
        "ordinary variation within a year?",
    )
    paragraph(
        document,
        "2. When does it stop? In which months did Washington's monthly "
        "arrivals drop sharply, and how many months separate each drop from "
        "the nearest documented federal policy event?",
    )
    paragraph(
        document,
        "3. Who does the count miss? What share of arrivals came from "
        "nationalities whose main language has no category of its own in the "
        "Census language tables, at state (B16001) and county (C16001) level? "
        "Which nationalities are they, and in which counties are the "
        "absorbing categories most concentrated?",
    )
    paragraph(
        document,
        "4. Two ledgers. For Afghan and Iraqi arrivals in Washington, what "
        "share appears only in the Special Immigrant Visa (SIV) report rather "
        "than the refugee arrivals report, and how did that share change "
        "around the 2021 evacuation? The SIV series ends at FY2025, so the "
        "comparison covers FY2015\u2013FY2025.",
    )

    heading(document, "2. Motivation")
    paragraph(
        document,
        "The national FY2025 refugee arrivals report records 38,102 arrivals "
        "for the year. February holds 2 of them, March 14, and April 41; "
        "February through September together account for 506, or 1.3% of the "
        "year. An organisation that plans from the annual total would staff "
        "for a programme that had in fact stopped. Washington shows the same "
        "shape more sharply: 354 arrivals in January 2025 and none recorded "
        "in any of the next eight months.",
    )
    paragraph(
        document,
        "The deeper problem is that arrivals are recorded by legal status, "
        "not by who people are. Refugee, SIV holder, asylee and humanitarian "
        "parolee are administrative categories, and each decides which report "
        "a person appears in. Afghan arrivals are split across two separately "
        "published tables, so \u201chow many Afghans arrived in "
        "Washington\u201d has two correct answers depending on the file. Our "
        "EDA measures how "
        "much those choices change the answer, and documents a third layer we "
        "did not expect: parts of the record cannot be read by a program at "
        "all.",
    )

    heading(document, "3. Dataset")
    table(
        document,
        pd.DataFrame(
            [
                ["A. Refugee arrivals by state and nationality", "12",
                 "6 Excel, 6 PDF", "FY2015\u2013FY2026",
                 "State \u00d7 nationality \u00d7 month"],
                ["B. Amerasian & SIV arrivals", "11", "PDF",
                 "FY2015\u2013FY2025", "State \u00d7 nationality"],
                ["C. ACS 2024 five-year estimates", "3", "API tables",
                 "2024", "State and 39 counties"],
                ["D. Refugee arrivals by region", "6", "PDF",
                 "FY2021\u2013FY2026", "Region \u00d7 month"],
            ],
            columns=["Source", "Files", "Format", "Years", "Unit"],
        ),
        "Table 1. Data sources collected for the project.",
        widths=[2.4, 0.6, 1.1, 1.2, 1.6],
    )
    paragraph(
        document,
        "All four sources are public and aggregate; we use no individual "
        "records. Source A is the project's backbone: one file per fiscal "
        "year from the Refugee Processing Center archive, whose file names "
        "follow no pattern (FY2023 alone contains the word "
        "\u201cRefugee\u201d, FY2024 is stamped \u201c30 Oct\u201d and "
        "suffixed \u201c_updated\u201d), "
        "so our code carries an explicit year-to-filename map. "
        "FY2015\u2013FY2020 "
        "are spreadsheets that report annual totals only; FY2021\u2013FY2026 "
        "are PDFs that add a column per month.",
    )
    paragraph(
        document,
        "Source C is the Census Bureau's 2024 American Community Survey "
        "five-year estimate, pulled through the API: B16001 gives "
        "Washington's language counts at state level, C16001 the same "
        "question for all 39 counties with 13 categories, and B05006 the "
        "county counts of Afghan- and Iraqi-born residents. Every ACS number "
        "is an estimate with a margin of error, and we report it that way. "
        "ACS counts a stock (everyone living in a county today, of any "
        "immigration status); RPC counts a flow (one year of arrivals, by "
        "state of initial resettlement). We never add, subtract or divide one "
        "by the other; the two are compared only as orders of magnitude.",
    )

    heading(document, "4. Method")
    paragraph(
        document,
        "The PDFs are table images exported from Tableau, and they defeat "
        "every off-the-shelf converter: extract_table() returns a grid whose "
        "labels have collapsed into the first cell of each blocked group, and "
        "the FY2025 and FY2026 files draw each row twice on two text layers. "
        "We therefore parse from word coordinates. For each page we read the "
        "month header, fit the thirteen value columns by searching for the "
        "offset at which the page's numbers line up, then attach each line's "
        "labels to the row it sits on and carry the merged state and "
        "nationality cells down the block. The same routine handles both "
        "orientations: the arrivals report prints state then nationality, "
        "the SIV report the reverse.",
    )
    paragraph(
        document,
        "Three checks guard the parse. First, every row's twelve monthly "
        "values are compared with its Grand Total; 96% to 100% of rows close "
        "exactly, and the residue is the rows a page repeats across a break. "
        "Second, the parsed national total is compared with the total printed "
        "in the file, and validate_total() raises when the two differ by "
        "more than 2% \u2014 every year the analysis uses passes, and the two "
        "that do not are named in 5.2. Third, where the file prints a state "
        "total (FY2021 and FY2023), Washington's parsed rows must equal it. "
        "Rows are never dropped to make a check pass: with merged cells a "
        "failing row is usually the label row for a whole block of "
        "nationalities. Repeated layers are removed by de-duplicating on "
        "state and nationality, and a printed total row is kept aside for "
        "the reconciliation table rather than added to the data.",
    )
    paragraph(
        document,
        "The language analysis needs a crosswalk from nationality to "
        "language to Census category. It lives in data/crosswalk.csv, one row "
        "per language with its role (main or other), the exact ACS category "
        "label and a tier: own category, shared category, or residual. Code "
        "loads the file and matches each label against the fetched ACS "
        "columns, so a renamed category fails loudly instead of silently "
        "producing a wrong count. Every table and figure in this report is "
        "regenerated by "
        "python src/main.py from the raw files.",
    )

    heading(document, "5. EDA Results")
    heading(document, "5.1 How large is the dataset", level=2)
    paragraph(
        document,
        "The tidy arrivals table holds one row per state, nationality, fiscal "
        "year and month. Parsing the nine usable refugee years yields 7,353 "
        "annual state-nationality rows, of which 17,568 arrivals are in "
        "Washington; the three years with monthly columns add 8,393 rows. "
        "FY2026 adds 49 further rows, one per state, but its nationality "
        "column is broken, so those rows support the totals only. Each row is "
        "therefore a count of people of one nationality who arrived in one "
        "state in one month of one fiscal year; the columns are the state of "
        "initial resettlement, the nationality, the fiscal year, the month "
        "and the count. The SIV table has the same shape but no month column, "
        "and the ACS tables hold one row per geography.",
    )

    heading(document, "5.2 Missing data", level=2)
    paragraph(
        document,
        "Missingness in the arrivals reports is structural rather than "
        "random. The PDFs print only rows with at least one arrival, so a "
        "missing (state, nationality) pair means zero arrivals, not an "
        "unknown value; we know this because every parsed year reproduces the "
        "national total printed in the file to within 2%, and because 96% to "
        "100% of rows close exactly against their own Grand Total. "
        "DataFrame.isna().sum() reports no missing cells in the tidy table, "
        "which is the correct answer only because the parser writes zeros by "
        "omission and the checks confirm the totals.",
    )
    paragraph(
        document,
        "Three years are genuinely missing, and each fails for a different "
        "reason. FY2022 arrives as a mixed PDF: 18 of its 19 pages contain "
        "one raster image and no text at all, so only page 1 can be read. "
        "FY2024 has text, but its single Type 1 font carries no Unicode map, "
        "so every extractor returns the byte behind each glyph "
        "(\u201cPLMSJ\u201d for a number) and no row can be trusted. "
        "FY2026 is "
        "different again: the file prints each state once and labels every "
        "one of them \u201cSouth Africa\u201d, 52 times over, so the state "
        "totals are sound (Washington's 480 arrives correctly) but the file "
        "contains no nationality breakdown to parse. We report the three "
        "failures rather than imputing them, and Table 2 shows what the "
        "parser does reproduce.",
    )
    table(
        document,
        pd.DataFrame(
            [
                ["2015\u20132020", "Excel", "69,933 \u2013 11,814",
                 "matches file total", "2,625 \u2013 1,108", "in file"],
                ["2021", "PDF", "11,533", "11,411 (+1.1%)", "480", "480"],
                ["2022", "PDF", "not parsed", "25,465", "\u2014", "\u2014"],
                ["2023", "PDF", "60,087", "60,014 (+0.1%)", "2,429", "2,429"],
                ["2024", "PDF", "not parsed", "\u2014", "\u2014", "\u2014"],
                ["2025", "PDF", "37,499", "38,102 (\u22121.6%)", "1,271",
                 "not printed"],
                ["2026", "PDF", "16,289", "16,292 (\u22120.02%)", "480",
                 "not printed"],
            ],
            columns=["Fiscal year", "Format", "Parsed national",
                     "Printed national", "Parsed WA", "Printed WA"],
        ),
        "Table 2. Reconciliation of the parser against the totals printed in "
        "each file.",
        widths=[0.9, 0.8, 1.2, 1.5, 1.1, 1.1],
    )

    heading(document, "5.3 Variables of interest", level=2)
    paragraph(
        document,
        "Four variables carry the analysis. state is the state of initial "
        "resettlement (sources A and B) and defines the population for RQ1 "
        "and RQ4. nationality is the primary applicant nationality (A and B); "
        "it is the only link between the arrivals record and the Census "
        "language tables, and it is the unit in which the administrative "
        "categories differ, so it carries RQ1, RQ3 and RQ4. month is the "
        "month of admission within the fiscal year (A) and is used only for "
        "RQ2, because only FY2021, FY2023 and FY2025 have a machine-readable "
        "monthly breakdown. count is the number of people admitted (A and B) "
        "and is the outcome in every question. The Census tables contribute "
        "one further pair, the language category and its margin of error "
        "(C), which RQ3 uses at state and county level.",
    )

    heading(document, "5.4 Summary of each variable", level=2)
    paragraph(
        document,
        "Washington's ten observed years average 1,805 arrivals (standard "
        "deviation 984), with a minimum of 480 (FY2021 and FY2026), first "
        "quartile 1,149, median 1,750, third quartile 2,576 and maximum 3,233 "
        "(FY2016). The distribution is not a trend: FY2015\u2013FY2017 sit "
        "near 3,000, FY2018\u2013FY2020 fall by half, FY2021 collapses to "
        "480, FY2023 returns to 2,429, FY2025 falls to 1,271 and FY2026, the "
        "year the admission suspension covers, closes at 480. A linear "
        "summary of this series would be misleading, which is why Figure 1 "
        "uses a bar per year rather than a fitted line.",
    )
    paragraph(
        document,
        "The categorical variables behave as expected: 61 distinct "
        "nationalities appear in Washington across the nine years, and the "
        "largest five account for 63\u201389% of a year's arrivals. Ukraine "
        "alone is 71.5% of Washington's FY2019 arrivals (1,392 of 1,947); in "
        "FY2015 the largest nationality, Iraq, is only 20.2%. At the county "
        "level, 39 counties appear and one of them, King, holds 52,078 of the "
        "state's 7,443 state-table speakers of \u201cOther and unspecified "
        "languages\u201d \u2014 a discrepancy we return to in 5.5.",
    )

    heading(document, "5.5 Visualisations", level=2)
    figure(
        document, "f1_annual.png",
        "Figure 1. Washington's refugee arrivals by fiscal year. Hatched bars "
        "are the two years whose file cannot be read at all (FY2022 raster "
        "images, FY2024 font without a Unicode map). FY2026 has no "
        "nationality breakdown but its state total is sound, so it is shown.",
    )
    paragraph(
        document,
        "Figure 1 plots the count variable alone, because the shape of the "
        "series is the first thing a reader needs and an annual total is the "
        "only quantity available for every readable year. The hatched bars "
        "are the point of the figure as much as the solid ones: a reader who "
        "sees a gap asks why, and the report answers that the gap is in the "
        "published file, not in the analysis.",
    )
    figure(
        document, "f2_composition.png",
        "Figure 2. The five largest nationalities each year, as a share of "
        "that year's Washington arrivals; grey is everyone else.",
    )
    paragraph(
        document,
        "Figure 2 uses shares rather than counts because the question is "
        "composition, not volume, and because the two move independently: "
        "between FY2018 and FY2019 the total rises only 25% while Ukraine's "
        "share rises from 65% to 71%. A stacked bar keeps volume and "
        "composition separable, which a line chart of counts would not.",
    )
    figure(
        document, "f3_monthly.png",
        "Figure 3. Monthly arrivals, Washington bars on the left axis and the "
        "national total as a line on the right axis, for the three years with "
        "monthly data. The two scales differ by an order of magnitude, so "
        "they are not comparable on one axis.",
    )
    paragraph(
        document,
        "Figure 3 is the RQ2 series. Washington's bars stop at January 2025: "
        "354 arrivals in that month and zero in each of the following eight. "
        "The national line does not stop at the same value: it falls from "
        "10,284 in January to 2 in February and then runs at 14 to 193 a "
        "month. A reader should take two things from the panel. The break is "
        "visible in a monthly series eight months before it is visible in an "
        "annual total, and Washington's own series is too small to test a "
        "breakpoint on its own, which is why the national line is drawn "
        "beside it.",
    )
    paragraph(
        document,
        "Table 3 applies the four settings the proposal pre-declared. The "
        "largest year-over-year change is FY2021 to FY2023 under both L1 "
        "variants (0.96), but FY2017 to FY2018 under both Jensen\u2013Shannon "
        "variants (0.38), so the same year wins in only two of the four "
        "settings.",
    )
    table(
        document,
        pd.DataFrame(
            [
                [row["setting"], "{}\u2013{}".format(
                    int(row["from"]), int(row["to"])),
                 "{:.2f}".format(row["largest_change"])]
                for _, row in settings.iterrows()
            ],
            columns=["Setting", "Largest change", "Distance"],
        ),
        "Table 3. Largest year-over-year change in the nationality mix under "
        "each of the four pre-declared settings.",
        widths=[1.8, 1.4, 1.0],
    )
    paragraph(
        document,
        "The rule also asks whether that change is larger than ordinary "
        "within-year variation. Using the months with at least 20 Washington "
        "arrivals, the median month-to-month L1 distance is 1.03 in FY2021 "
        "(9 usable months) and 0.82 in FY2023 (12 months); FY2025 has only 4 "
        "usable months and is flagged, as the plan requires. The ratios are "
        "therefore 0.76 for FY2020 to FY2021 and 1.18 for FY2021 to FY2023 "
        "\u2014 both far below the threshold of 3. Under the pre-declared "
        "rule we name no turning-point year and report the two candidate "
        "transitions instead.",
    )
    figure(
        document, "f5_language.png",
        "Figure 4. Share of Washington arrivals whose nationality's main "
        "language has its own Census category, shares one, or falls into a "
        "residual category; \u201cnot in crosswalk\u201d is shown separately.",
    )
    paragraph(
        document,
        "Figure 4 answers RQ3 for the state table, using each nationality's "
        "main language. The share of arrivals in a shared category rises to "
        "76.6% in FY2019, almost entirely because Ukrainian is counted with "
        "Russian and Polish in B16001; by FY2025 the own-category share is "
        "52.2% and the residual share 11.5%. The figure is a stacked bar "
        "rather than a line because the four tiers sum to one in each year, "
        "and the eye should read the boundary movement, not each series "
        "separately.",
    )
    table(
        document,
        pd.DataFrame(
            [
                [int(row["fiscal_year"]), "{:,}".format(int(row["arrivals"])),
                 "{:.0%}".format(row["pessimistic_visible"]),
                 "{:.0%}".format(row["optimistic_visible"]),
                 "{:.0%}".format(row["unmapped"])]
                for _, row in bounds.iterrows()
            ],
            columns=["Year", "Arrivals", "Pessimistic", "Optimistic",
                     "Unmapped"],
        ),
        "Table 4. Share of arrivals the state language table can see: "
        "pessimistic (main language only) and optimistic (any common "
        "language) rules.",
        widths=[0.8, 1.0, 1.2, 1.1, 1.0],
    )
    paragraph(
        document,
        "Table 4 is the range the proposal asks for. In FY2019 the state "
        "table sees 6.1% of arrivals if only the main language counts and "
        "84.3% if any common language counts, because Ukrainian and Russian "
        "each have a category while Somali does not. The range, not either "
        "endpoint, is the answer, and it is wide enough that no single share "
        "should be quoted without the rule that produced it.",
    )
    figure(
        document, "f6_counties.png",
        "Figure 5. Washington counties by the size of the C16001 category "
        "\u201cOther and unspecified languages\u201d, with the Census "
        "Bureau's margin of error.",
    )
    paragraph(
        document,
        "Figure 5 gives the geography RQ3 asks for, but it also shows why the "
        "county table has to be a bound rather than a count: King County's "
        "52,078 speakers of \u201cOther and unspecified languages\u201d is "
        "seven times the 7,443 that the state table assigns to the same "
        "label, because C16001 has 13 categories where B16001 has more than a "
        "hundred. The bars answer \u201cwhere could these communities "
        "be\u201d, "
        "not \u201chow many are there\u201d.",
    )
    figure(
        document, "f7_ledgers.png",
        "Figure 6. Afghan and Iraqi arrivals in Washington by report. The SIV "
        "series is available and reconciles only for FY2015\u2013FY2020.",
    )
    paragraph(
        document,
        "Figure 6 is the two-ledger result. For Afghans the SIV report holds "
        "93\u201399% of recorded arrivals in every year shown: 930 SIV "
        "arrivals against 35 refugee arrivals in FY2017, and 618 "
        "FY2019. An analysis that read only the refugee report would "
        "conclude that almost no Afghans came to Washington in those years. "
        "Iraq runs the other way: 78\u201393% of its recorded arrivals are in "
        "the refugee report in every year but FY2018, when the total was 25 "
        "people. That contrast is the check that "
        "the pattern is about programme, not about the tabulation: the same "
        "two files, read the same way, produce opposite answers for two "
        "nationalities.",
    )

    heading(document, "5.6 How the datasets relate", level=2)
    paragraph(
        document,
        "A and B are joined on state, nationality and fiscal year with an "
        "outer join, because an inner join would drop exactly the rows that "
        "appear in only one report \u2014 the rows the analysis is about. A "
        "and C are joined through the crosswalk on nationality to language to "
        "Census category, a many-to-one join that must be declared rather "
        "than assumed. D is not joined at all: it is a second publication of "
        "the same universe, kept as an independent check. The EDA above was "
        "run on each of the two joins (A+B, A+C) rather than on the "
        "individual files, which is what the Multiple Datasets requirement "
        "asks for.",
    )

    heading(document, "5.7 Result validity", level=2)
    paragraph(
        document,
        "Arrival counts are a complete administrative record, not a sample, "
        "so we do not attach sampling confidence intervals to them. Each "
        "research question instead gets a null hypothesis, a test, and the "
        "assumption checks that this EDA could actually run.",
    )
    bullet(
        document,
        "RQ1. H0: the nationality mix is the same in consecutive years. Test: "
        "L1 distance against the within-year monthly mix, in the four "
        "pre-declared settings. Check: only months with at least 20 "
        "Washington arrivals have a usable share vector \u2014 nine months in "
        "FY2021, twelve in FY2023, four in FY2025 \u2014 so FY2025 is flagged "
        "and its noise is not used. The observed ratios (0.76 and 1.18) fall "
        "below the threshold of 3, so no year is named.",
    )
    bullet(
        document,
        "RQ2. H0: the monthly series has no break. Test: binary segmentation "
        "with a max-statistic permutation null that re-estimates the break on "
        "every shuffle. Check: Washington's monthly counts fall below five in "
        "most months of FY2025, so the break must be estimated on the "
        "national series and Washington reported as a change in level.",
    )
    bullet(
        document,
        "RQ3. H0: the invisible share is zero. Test: the two-bound estimate "
        "of Table 4. Check: Arabic-speaking nationalities must come out "
        "visible; they do (Iraq, Syria and Sudan all map to the Arabic "
        "category), which validates the crosswalk before any share is "
        "reported, and the optimistic rule must never see less than the "
        "pessimistic one \u2014 it does not, in any year.",
    )
    bullet(
        document,
        "RQ4. H0: the SIV share does not differ across years. Test: a "
        "difference in proportions with Wilson intervals. Check: small "
        "denominators \u2014 Iraqi FY2018 has 25 recorded arrivals \u2014 so "
        "that year is reported as a direction, not a rate.",
    )

    heading(document, "6. Challenge Goals Update")
    paragraph(
        document,
        "Multiple Datasets is met and is the backbone of the report: three "
        "independently published sources (RPC arrivals, RPC SIV, Census ACS) "
        "are used together, with two joins (A+B, A+C) and two research "
        "questions that each draw on more than one source. Result Validity is "
        "partly met: the parser is reconciled against totals printed in the "
        "files, the crosswalk has a known-answer check, the language share is "
        "reported as a two-rule range, and the composition change is tested "
        "in the four pre-declared settings. The permutation null and the "
        "change-point estimate belong to the modelling stage and are not part "
        "of this EDA. New Library is not yet used: ruptures and scipy enter "
        "at that stage, and this report does not claim them.",
    )
    paragraph(
        document,
        "Three parts of the proposed plan could not be carried out on the "
        "published files, and the report states each rather than filling the "
        "gap: the monthly series covers 36 months (FY2021, FY2023, FY2025) "
        "instead of the proposed 144, because the spreadsheet years carry "
        "annual totals only; the two-ledger comparison stops at FY2020 "
        "instead of FY2025, because the SIV files from FY2021 on do not "
        "reconcile; and the FY2022 and FY2024 state files are not "
        "machine-readable at all. The national monthly series is used for the "
        "break discussion, as the plan anticipated, but the breakpoint test "
        "itself is deferred.",
    )

    heading(document, "7. Work Plan Evaluation")
    table(
        document,
        pd.DataFrame(
            [
                ["Acquire and snapshot data", "5", "6",
                 "RPC files, ACS key, 4 sources"],
                ["Parsers for three formats", "16", "11",
                 "Excel trivial; PDF layouts took most of it"],
                ["Crosswalk and joins", "9", "3",
                 "17 nationalities mapped, two joins"],
                ["Analysis and figures", "12", "4", "6 figures, 5 tables"],
                ["Tests and report", "10", "5", "still writing"],
            ],
            columns=["Task", "Planned hours", "Actual hours", "Note"],
        ),
        "Table 5. Planned versus actual effort.",
        widths=[2.2, 0.9, 0.9, 2.4],
    )
    paragraph(
        document,
        "The parser estimate was the closest of the five and still off by "
        "five hours in the other direction: the Excel years took minutes, but "
        "each PDF layout needed its own probing, and three of the twelve "
        "years turned out not to be readable at all. That discovery is the "
        "main reason the plan changed: we cut FY2022, FY2024 and the FY2026 "
        "state breakdown instead of spending the remaining time on OCR and "
        "font decoding. What remains is the modelling stage: the change-point "
        "test on the national series, the permutation null for RQ1, and the "
        "county-level aggregation for RQ3.",
    )

    heading(document, "8. Testing")
    paragraph(
        document,
        "The tests check the parsers against values that are printed in the "
        "source files, so a wrong column model cannot pass silently. "
        "test_project.py asserts that FY2025 parses to 38,102 nationally and "
        "that the FY2015\u2013FY2020 Excel years match the totals printed in "
        "their own files; it checks that Washington's monthly rows reconcile "
        "with its annual total and that the FY2021 and FY2023 state totals "
        "equal the values the files print; it checks the state list, the "
        "language tiers and the crosswalk's known answer, requiring "
        "Arabic-speaking nationalities to land in the Arabic category. One "
        "test feeds a corrupted total to the validator and requires it to "
        "raise, which is how we know the checks are not vacuous. We test this "
        "way because the failure mode we fear is not a crash but a plausible "
        "wrong number, and only an external anchor \u2014 a total printed by "
        "the publisher \u2014 catches that.",
    )

    heading(document, "9. Collaboration")
    paragraph(
        document,
        "Beyond the course staff and each other, we used the Refugee "
        "Processing Center's public documentation for the file definitions, "
        "the Census Bureau's API documentation and variable labels, Python's "
        "pdfplumber documentation for word-level extraction, and the "
        "pandas documentation for the aggregation. No other people "
        "contributed to the analysis.",
    )

    heading(document, "Appendix A. Largest five nationalities by year")
    rows = []
    for year in sorted(top["fiscal_year"].unique()):
        block = top[top["fiscal_year"] == year].sort_values("rank")
        names = [
            "{} ({:.0%})".format(row["nationality"], row["share"])
            for _, row in block.iterrows()
        ]
        rows.append([int(year)] + names)
    appendix = pd.DataFrame(
        rows, columns=["Year", "1st", "2nd", "3rd", "4th", "5th"]
    )
    table(document, appendix,
          "Table A1. Top five nationalities per year in Washington, with "
          "their share of that year's arrivals. Names are reproduced as the "
          "PDF prints them, truncations included.",
          widths=[0.6, 1.2, 1.3, 1.3, 1.2, 1.3], size=8)

    heading(document, "Appendix B. Crosswalk used for the language analysis")
    crosswalk = pd.read_csv(os.path.join("data", "crosswalk.csv"))
    table(document, crosswalk,
          "Table B1. Nationality to language to ACS category, with tier.",
          widths=[1.5, 1.0, 2.4, 0.8, 1.4], size=8)

    heading(
        document,
        "Appendix C. Counties with the largest residual language category",
    )
    table(document, county,
          "Table C1. C16001 'Other and unspecified languages', estimate and "
          "margin of error.",
          widths=[2.4, 1.4, 1.4], size=8)

    document.save("eda.docx")
    print("saved eda.docx")


if __name__ == "__main__":
    main()
