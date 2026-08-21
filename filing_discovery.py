"""Discover in-scope 13F filings through the SEC submissions API."""

from __future__ import annotations

from collections import Counter

from sec_client import SecClient


FORMS_IN_SCOPE = {
    "13F-HR",
    "13F-HR/A",
    "13F-NT",
    "13F-NT/A",
}


def discover_filings(
    client: SecClient,
    filers: list[dict[str, str]],
    report_periods: tuple[str, ...],
    filing_date_cutoff: str,
) -> list[dict[str, str]]:
    """Find the required filings for every manager and report period."""
    discovered: list[dict[str, str]] = []

    for filer in filers:
        cik = filer["cik"]
        padded_cik = cik.zfill(10)

        submissions_url = (
            "https://data.sec.gov/submissions/"
            f"CIK{padded_cik}.json"
        )

        submissions = client.get_json(
            submissions_url,
            f"sec/submissions/CIK{padded_cik}.json",
        )

        recent = submissions["filings"]["recent"]

        for index, form_type in enumerate(recent["form"]):
            report_date = recent["reportDate"][index]
            filing_date = recent["filingDate"][index]

            if form_type not in FORMS_IN_SCOPE:
                continue

            if report_date not in report_periods:
                continue

            if filing_date > filing_date_cutoff:
                continue

            discovered.append(
                {
                    "fund_name": filer["fund_name"],
                    "cik": cik,
                    "cik_padded": padded_cik,
                    "accession_number": recent[
                        "accessionNumber"
                    ][index],
                    "form_type": form_type,
                    "report_date": report_date,
                    "filing_date": filing_date,
                    "primary_document": recent[
                        "primaryDocument"
                    ][index],
                }
            )

    discovered.sort(
        key=lambda filing: (
            int(filing["cik"]),
            filing["report_date"],
            filing["filing_date"],
            filing["accession_number"],
        )
    )

    validate_filing_counts(
        discovered,
        filers,
        report_periods,
    )
    return discovered


def validate_filing_counts(
    filings: list[dict[str, str]],
    filers: list[dict[str, str]],
    report_periods: tuple[str, ...],
) -> None:
    """Require one filing for every manager-period combination."""
    counts = Counter(
        (filing["cik"], filing["report_date"])
        for filing in filings
    )

    expected_pairs = {
        (filer["cik"], report_period)
        for filer in filers
        for report_period in report_periods
    }

    missing = sorted(
        pair
        for pair in expected_pairs
        if counts[pair] == 0
    )

    duplicates = sorted(
        (pair, count)
        for pair, count in counts.items()
        if count > 1
    )

    expected_total = len(filers) * len(report_periods)

    if (
        len(filings) != expected_total
        or missing
        or duplicates
    ):
        raise ValueError(
            "Unexpected filing discovery result. "
            f"Expected {expected_total}, found {len(filings)}. "
            f"Missing manager-periods: {missing}. "
            f"Duplicate manager-periods: {duplicates}."
        )