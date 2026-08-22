from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from lxml import etree


def local_name(element: etree._Element) -> str:
    """Return an XML element's name without its namespace."""
    return etree.QName(element).localname


def find_elements(
    root: etree._Element,
    name: str,
) -> list[etree._Element]:
    """Find every descendant having the requested local name."""
    return root.xpath(f'.//*[local-name()="{name}"]')


def find_first(
    root: etree._Element,
    name: str,
) -> etree._Element | None:
    """Find the first descendant having the requested local name."""
    matches = find_elements(root, name)
    return matches[0] if matches else None


def find_text(
    root: etree._Element,
    name: str,
    required: bool = False,
) -> str | None:
    """Extract and clean text from the first matching element."""
    element = find_first(root, name)

    if element is None or element.text is None:
        if required:
            raise ValueError(f"Required XML element is missing: {name}")
        return None

    value = element.text.strip()

    if not value:
        if required:
            raise ValueError(f"Required XML element is empty: {name}")
        return None

    return value


def parse_integer(
    value: str | None,
    field_name: str,
    required: bool = False,
) -> int | None:
    """Convert XML text into an integer."""
    if value is None:
        if required:
            raise ValueError(f"Required integer is missing: {field_name}")
        return None

    try:
        return int(value.replace(",", ""))
    except ValueError as exc:
        raise ValueError(
            f"Invalid integer for {field_name}: {value!r}"
        ) from exc


def find_integer(
    root: etree._Element,
    name: str,
    required: bool = False,
) -> int | None:
    """Find an XML field and convert its text to an integer."""
    value = find_text(root, name, required=required)
    return parse_integer(value, name, required=required)


def parse_sec_date(value: str) -> date:
    """Convert an SEC MM-DD-YYYY date into a Python date."""
    try:
        return datetime.strptime(value, "%m-%d-%Y").date()
    except ValueError as exc:
        raise ValueError(f"Invalid SEC date: {value!r}") from exc


def make_report_quarter(report_period: date) -> str:
    """Convert a reporting date into YYYYQN format."""
    quarter = ((report_period.month - 1) // 3) + 1
    return f"{report_period.year}Q{quarter}"


def parse_holdings(
    xml_path: Path,
    accession_number: str,
    cik: str,
    report_quarter: str,
) -> list[dict[str, object]]:
    """Parse every position from one filing's information-table XML."""
    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    rows: list[dict[str, object]] = []

    # XPath returns elements in their original XML order.
    for position in find_elements(root, "infoTable"):
        cusip = find_text(position, "cusip", required=True)

        if len(cusip) != 9:
            raise ValueError(
                f"Invalid CUSIP length in {accession_number}: {cusip!r}"
            )

        row = {
            "accession_number": accession_number,
            "cik": cik.zfill(10),
            "report_quarter": report_quarter,
            "name_of_issuer": find_text(
                position, "nameOfIssuer", required=True
            ),
            "title_of_class": find_text(
                position, "titleOfClass", required=True
            ),
            "cusip": cusip,
            "figi": find_text(position, "figi"),
            "value": find_integer(position, "value", required=True),
            "ssh_prnamt": find_integer(
                position, "sshPrnamt", required=True
            ),
            "ssh_prnamt_type": find_text(
                position, "sshPrnamtType", required=True
            ),
            "put_call": find_text(position, "putCall"),
            "investment_discretion": find_text(
                position, "investmentDiscretion", required=True
            ),
            "other_manager": find_text(position, "otherManager"),
            "voting_sole": find_integer(
                position, "Sole", required=True
            ),
            "voting_shared": find_integer(
                position, "Shared", required=True
            ),
            "voting_none": find_integer(
                position, "None", required=True
            ),
        }

        rows.append(row)

    return rows


def parse_filing(
    primary_xml_path: Path,
    accession_number: str,
    fund_name: str,
    filing_date: str,
) -> dict[str, object]:
    """Parse one filing's cover-page information."""
    tree = etree.parse(str(primary_xml_path))
    root = tree.getroot()

    cover_page = find_first(root, "coverPage")
    filing_manager = find_first(root, "filingManager")
    summary_page = find_first(root, "summaryPage")

    if cover_page is None:
        raise ValueError(
            f"Missing cover page: {accession_number}"
        )

    if filing_manager is None:
        raise ValueError(
            f"Missing filing manager: {accession_number}"
        )

    form_type = find_text(root, "submissionType", required=True)
    cik = find_text(root, "cik", required=True).zfill(10)

    report_period_text = find_text(
        cover_page,
        "reportCalendarOrQuarter",
        required=True,
    )
    report_period = parse_sec_date(report_period_text)

    is_amendment = form_type.endswith("/A")

    amendment_no = find_integer(root, "amendmentNo")
    amendment_type = find_text(root, "amendmentType")

    # Notice filings do not contain holdings totals.
    is_notice = form_type in {"13F-NT", "13F-NT/A"}

    if summary_page is None:
        other_manager_count = None
        table_entry_total = None
        table_value_total = None
    else:
        other_manager_count = find_integer(
            summary_page,
            "otherIncludedManagersCount",
        )
        table_entry_total = (
            None
            if is_notice
            else find_integer(summary_page, "tableEntryTotal")
        )
        table_value_total = (
            None
            if is_notice
            else find_integer(summary_page, "tableValueTotal")
        )

    return {
        "accession_number": accession_number,
        "cik": cik,
        "fund_name": fund_name,
        "filing_manager": find_text(
            filing_manager,
            "name",
            required=True,
        ),
        "form_type": form_type,
        "report_period": report_period,
        "report_quarter": make_report_quarter(report_period),
        "filing_date": date.fromisoformat(filing_date),
        "is_amendment": is_amendment,
        "amendment_no": amendment_no,
        "amendment_type": amendment_type,
        "report_type": find_text(
            cover_page,
            "reportType",
            required=True,
        ),
        "form_13f_file_number": find_text(
            cover_page,
            "form13FFileNumber",
        ),
        "crd_number": find_text(cover_page, "crdNumber"),
        "sec_file_number": find_text(
            cover_page,
            "secFileNumber",
        ),
        "other_included_managers_count": other_manager_count,
        "table_entry_total": table_entry_total,
        "table_value_total": table_value_total,
    }


def parse_dataset(
    filings: list[dict[str, str]],
) -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
]:
    """Parse all discovered filings and holdings."""
    filing_rows: list[dict[str, object]] = []
    holding_rows: list[dict[str, object]] = []

    for filing in filings:
        filing_row = parse_filing(
            primary_xml_path=Path(filing["primary_xml_path"]),
            accession_number=filing["accession_number"],
            fund_name=filing["fund_name"],
            filing_date=filing["filing_date"],
        )

        # Confirm that the XML agrees with the submissions API.
        if filing_row["cik"] != filing["cik_padded"]:
            raise ValueError(
                f"CIK mismatch: {filing['accession_number']}"
            )

        if filing_row["form_type"] != filing["form_type"]:
            raise ValueError(
                f"Form-type mismatch: {filing['accession_number']}"
            )

        if (
            filing_row["report_period"].isoformat()
            != filing["report_date"]
        ):
            raise ValueError(
                f"Report-period mismatch: "
                f"{filing['accession_number']}"
            )

        filing_rows.append(filing_row)

        # Notices have a filing row but no holdings rows.
        if filing["form_type"].startswith("13F-NT"):
            continue

        information_path = filing["information_table_xml_path"]

        if not information_path:
            raise ValueError(
                f"Missing information table: "
                f"{filing['accession_number']}"
            )

        rows = parse_holdings(
            xml_path=Path(information_path),
            accession_number=filing["accession_number"],
            cik=filing["cik"],
            report_quarter=filing_row["report_quarter"],
        )

        declared_count = filing_row["table_entry_total"]
        actual_count = len(rows)

        if declared_count != actual_count:
            raise ValueError(
                f"Holding-count mismatch for "
                f"{filing['accession_number']}: "
                f"declared {declared_count}, parsed {actual_count}"
            )

        declared_value = filing_row["table_value_total"]
        actual_value = sum(row["value"] for row in rows)

        if declared_value != actual_value:
            raise ValueError(
                f"Holding-value mismatch for "
                f"{filing['accession_number']}: "
                f"declared {declared_value}, parsed {actual_value}"
            )

        holding_rows.extend(rows)

    return filing_rows, holding_rows