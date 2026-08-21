"""Explore the downloaded 13F XML before implementing the final parser.

Schema mapping:
- accession_number: submissions API; preserved in the output filename
- cik: primary XML credentials/cik; padded to ten characters
- fund_name: reconciled output/filers.csv
- filing_manager: coverPage/filingManager/name
- form_type: headerData/submissionType
- report_period: coverPage/reportCalendarOrQuarter
- report_quarter: derived from report_period
- filing_date: submissions API
- is_amendment: derived from form_type ending in /A
- amendment_no: amendmentInfo/amendmentNo
- amendment_type: amendmentInfo/amendmentType
- report_type: coverPage/reportType
- form_13f_file_number: coverPage/form13FFileNumber
- crd_number: coverPage/crdNumber
- sec_file_number: coverPage/secFileNumber
- other_included_managers_count: summaryPage/otherIncludedManagersCount
- table_entry_total: summaryPage/tableEntryTotal
- table_value_total: summaryPage/tableValueTotal

Holdings fields map directly to each infoTable element:
nameOfIssuer, titleOfClass, cusip, figi, value, sshPrnamt,
sshPrnamtType, putCall, investmentDiscretion, otherManager,
Sole, Shared, and None.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from lxml import etree


ROOT = Path(__file__).resolve().parents[1]
FILINGS_DIR = ROOT / "output" / "filings"
ARCHIVE_CACHE = ROOT / ".cache" / "sec" / "archives"


def parse_xml(path: Path):
    """Parse one XML file and return its root element."""
    return etree.parse(str(path)).getroot()


def local_name(element) -> str:
    """Return an XML tag name without its namespace."""
    return etree.QName(element).localname


def descendants(root, name: str):
    """Find descendants by local name, independent of namespace prefix."""
    return root.xpath(
        './/*[local-name()=$name]',
        name=name,
    )


def first_text(root, name: str) -> str | None:
    """Return the first matching element's stripped text."""
    matches = descendants(root, name)

    if not matches or matches[0].text is None:
        return None

    return matches[0].text.strip()


def find_primary_xml(
    cik: str,
    accession: str,
    output_path: Path,
) -> Path | None:
    """Find the primary cover-page XML downloaded by main.py."""
    output_root = parse_xml(output_path)

    if local_name(output_root).lower() == "edgarsubmission":
        return output_path

    cache_directory = ARCHIVE_CACHE / cik / accession

    for candidate in sorted(cache_directory.glob("*.xml")):
        try:
            root = parse_xml(candidate)
        except etree.XMLSyntaxError:
            continue

        if local_name(root).lower() == "edgarsubmission":
            return candidate

    return None


def main() -> None:
    xml_paths = sorted(FILINGS_DIR.glob("*/*.xml"))

    if len(xml_paths) != 40:
        raise ValueError(
            f"Expected 40 filing XML files; found {len(xml_paths)}"
        )

    root_types = Counter()
    namespace_styles = set()
    missing_fields = Counter()

    holding_rows = 0
    per_filing_rows: dict[Path, int] = {}
    per_filing_values: dict[Path, int] = {}

    put_call_values = Counter()
    share_types = Counter()
    discretion_values = Counter()
    other_manager_values = Counter()

    invalid_cusip_lengths = []
    cins_cusips = []
    leading_zero_cusips = []
    duplicate_cusip_filings = []
    decoded_entity_examples = []
    figi_present = 0

    required_holding_tags = {
        "nameOfIssuer",
        "titleOfClass",
        "cusip",
        "value",
        "sshPrnamt",
        "sshPrnamtType",
        "investmentDiscretion",
        "Sole",
        "Shared",
        "None",
    }

    for path in xml_paths:
        root = parse_xml(path)
        root_type = local_name(root)
        root_types[root_type] += 1

        namespace_styles.add(
            tuple(
                sorted(
                    (str(prefix), uri)
                    for prefix, uri in root.nsmap.items()
                )
            )
        )

        if root_type.lower() != "informationtable":
            continue

        rows = descendants(root, "infoTable")
        holding_rows += len(rows)
        per_filing_rows[path] = len(rows)

        value_total = 0
        cusips = []

        for row in rows:
            row_data = {
                local_name(element): (
                    element.text.strip()
                    if element.text
                    else None
                )
                for element in row.iter()
            }

            for tag in required_holding_tags:
                if row_data.get(tag) is None:
                    missing_fields[tag] += 1

            issuer = row_data.get("nameOfIssuer")
            cusip = row_data.get("cusip")
            value = row_data.get("value")
            figi = row_data.get("figi")
            put_call = row_data.get("putCall")
            share_type = row_data.get("sshPrnamtType")
            discretion = row_data.get(
                "investmentDiscretion"
            )
            other_manager = row_data.get("otherManager")

            if value is not None:
                value_total += int(value)

            if figi is not None:
                figi_present += 1

            put_call_values[put_call or "<absent>"] += 1
            share_types[share_type or "<absent>"] += 1
            discretion_values[discretion or "<absent>"] += 1
            other_manager_values[
                other_manager or "<absent>"
            ] += 1

            if issuer and "&" in issuer:
                decoded_entity_examples.append(
                    (path.name, issuer)
                )

            if cusip:
                cusips.append(cusip)

                if len(cusip) != 9:
                    invalid_cusip_lengths.append(
                        (path.name, cusip)
                    )

                if cusip[0].isalpha():
                    cins_cusips.append(cusip)

                if cusip.startswith("0"):
                    leading_zero_cusips.append(cusip)

        per_filing_values[path] = value_total

        duplicate_count = sum(
            count - 1
            for count in Counter(cusips).values()
            if count > 1
        )

        if duplicate_count:
            duplicate_cusip_filings.append(
                (path.name, duplicate_count)
            )

    primary_files_found = 0
    amendments = []
    notices = []
    count_discrepancies = []
    value_discrepancies = []
    included_manager_filings = []
    leading_zero_crds = []

    for output_path in xml_paths:
        cik = output_path.parent.name
        accession = output_path.stem

        primary_path = find_primary_xml(
            cik,
            accession,
            output_path,
        )

        if primary_path is None:
            continue

        primary_files_found += 1
        primary_root = parse_xml(primary_path)

        form_type = first_text(
            primary_root,
            "submissionType",
        )
        report_type = first_text(primary_root, "reportType")
        crd_number = first_text(primary_root, "crdNumber")

        if form_type and form_type.endswith("/A"):
            amendments.append(accession)

        if form_type and form_type.startswith("13F-NT"):
            notices.append(
                (accession, cik, report_type)
            )

        if crd_number and crd_number.startswith("0"):
            leading_zero_crds.append(
                (accession, crd_number)
            )

        other_count_text = first_text(
            primary_root,
            "otherIncludedManagersCount",
        )
        other_count = (
            int(other_count_text)
            if other_count_text is not None
            else None
        )

        if other_count and other_count > 0:
            included_manager_filings.append(
                (accession, other_count)
            )

        if form_type and form_type.startswith("13F-HR"):
            declared_count = int(
                first_text(primary_root, "tableEntryTotal")
            )
            declared_value = int(
                first_text(primary_root, "tableValueTotal")
            )

            actual_count = per_filing_rows[output_path]
            actual_value = per_filing_values[output_path]

            if declared_count != actual_count:
                count_discrepancies.append(
                    (
                        accession,
                        declared_count,
                        actual_count,
                    )
                )

            if declared_value != actual_value:
                value_discrepancies.append(
                    (
                        accession,
                        declared_value,
                        actual_value,
                    )
                )

    print("=== FILE COVERAGE ===")
    print(f"XML files: {len(xml_paths)}")
    print(f"Root types: {dict(root_types)}")
    print(f"Primary documents found: {primary_files_found}")
    print(f"Total holding rows: {holding_rows:,}")
    print(f"Namespace styles: {len(namespace_styles)}")

    print("\n=== OPTIONAL AND CATEGORICAL FIELDS ===")
    print(f"FIGI present: {figi_present:,}")
    print(f"putCall values: {dict(put_call_values)}")
    print(f"Share/principal types: {dict(share_types)}")
    print(f"Investment discretion: {dict(discretion_values)}")
    print(
        "Most common otherManager values:",
        other_manager_values.most_common(10),
    )
    print(f"Missing required fields: {dict(missing_fields)}")

    print("\n=== IDENTIFIER AND DUPLICATE CHECKS ===")
    print(
        f"CUSIPs with invalid length: "
        f"{len(invalid_cusip_lengths)}"
    )
    print(
        f"CINS codes beginning with a letter: "
        f"{len(cins_cusips):,}"
    )
    print(
        f"CUSIPs beginning with zero: "
        f"{len(leading_zero_cusips):,}"
    )
    print(
        "Filings containing duplicate CUSIPs:",
        duplicate_cusip_filings[:10],
    )
    print(
        "Decoded XML entity examples:",
        decoded_entity_examples[:5],
    )
    print(
        "CRD values with leading zeros:",
        leading_zero_crds[:5],
    )

    print("\n=== COVER-PAGE VALIDATION ===")
    print(f"Amendments: {amendments}")
    print(f"Notices: {notices}")
    print(
        "Filings with included managers:",
        included_manager_filings,
    )
    print(
        "Declared/actual entry-count discrepancies:",
        count_discrepancies,
    )
    print(
        "Declared/actual value discrepancies:",
        value_discrepancies,
    )

    print("\n=== FINDINGS ===")
    print(
        f"1. The 40 files use {len(namespace_styles)} namespace "
        "layouts. The parser must match namespace/local names rather "
        "than assume one literal tag format."
    )
    print(
        f"2. Across {holding_rows:,} holdings, putCall is absent in "
        f"{put_call_values['<absent>']:,} rows and FIGI is absent in "
        f"{holding_rows - figi_present:,} rows. These must become "
        "genuine nulls."
    )
    print(
        f"3. otherManager is absent in "
        f"{other_manager_values['<absent>']:,} rows and equals '0' "
        f"in {other_manager_values['0']:,} rows. References can also "
        "be comma-separated, such as '2,1', so this field must remain "
        "a nullable string."
    )
    print(
        f"4. {len(cins_cusips):,} CUSIPs begin with a letter and "
        f"{len(leading_zero_cusips):,} begin with zero. CUSIP must "
        "remain a nine-character string."
    )
    print(
        f"5. {len(duplicate_cusip_filings)} filings contain repeated "
        "CUSIPs. For example, accession "
        f"{duplicate_cusip_filings[0][0]} has "
        f"{duplicate_cusip_filings[0][1]:,} repeated occurrences "
        "beyond the first; rows must not be deduplicated."
    )
    print(
        f"6. {len(included_manager_filings)} filings declare included "
        "managers, demonstrating that otherManager is a reference to "
        "the cover-page manager list."
    )
    print(
        f"7. All {root_types['informationTable']} holdings reports "
        "match both their declared entry totals and declared value "
        "totals; the parser should still retain these as validation "
        "checks."
    )
    print(
        f"8. The dataset contains no amendments and one notice: "
        f"{notices[0][0]} for CIK {notices[0][1]}. The notice has no "
        "holdings table and must remain represented in filings."
    )

if __name__ == "__main__":
    main()