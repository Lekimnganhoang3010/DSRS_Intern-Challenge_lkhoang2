"""Read-only access to the curated 13F Parquet dataset."""

from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
FILINGS_PATH = OUTPUT / "filings.parquet"
HOLDINGS_PATH = OUTPUT / "holdings.parquet"


def load_dataset() -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
]:
    """Load both Parquet tables without modifying them."""
    if not FILINGS_PATH.exists():
        raise FileNotFoundError(f"Missing dataset: {FILINGS_PATH}")

    if not HOLDINGS_PATH.exists():
        raise FileNotFoundError(f"Missing dataset: {HOLDINGS_PATH}")

    filings = pq.read_table(FILINGS_PATH).to_pylist()
    holdings = pq.read_table(HOLDINGS_PATH).to_pylist()

    return filings, holdings


def build_filing_index(
    filings: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Index filings by accession number for fast lookup."""
    return {
        str(filing["accession_number"]): filing
        for filing in filings
    }


def available_managers(
    filings: list[dict[str, object]],
) -> list[str]:
    """Return the manager names in stable alphabetical order."""
    return sorted(
        {
            str(filing["fund_name"])
            for filing in filings
        }
    )


def available_quarters(
    filings: list[dict[str, object]],
) -> list[str]:
    """Return the reporting quarters in stable order."""
    return sorted(
        {
            str(filing["report_quarter"])
            for filing in filings
        }
    )