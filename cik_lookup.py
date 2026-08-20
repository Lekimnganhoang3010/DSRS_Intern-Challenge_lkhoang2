"""Download and parse the SEC's official company-name-to-CIK lookup."""

from __future__ import annotations

import csv
from pathlib import Path

from sec_client import SecClient


CIK_LOOKUP_URL = (
    "https://www.sec.gov/Archives/edgar/cik-lookup-data.txt"
)


def load_cik_lookup(
    client: SecClient,
    csv_path: Path,
) -> list[dict[str, str]]:
    """Return the SEC CIK lookup and save a normalized CSV copy."""
    lookup_text = client.get_text(
        CIK_LOOKUP_URL,
        "sec/cik-lookup-data.txt",
    )

    records: list[dict[str, str]] = []

    for line_number, raw_line in enumerate(
        lookup_text.splitlines(),
        start=1,
    ):
        line = raw_line.strip()

        if not line:
            continue

        try:
            sec_name, cik, trailing = line.rsplit(":", 2)
        except ValueError as exc:
            raise ValueError(
                f"Malformed CIK lookup record on line {line_number}"
            ) from exc

        if trailing != "" or not cik.isdigit():
            raise ValueError(
                f"Malformed CIK lookup record on line {line_number}"
            )

        records.append(
            {
                "sec_name": sec_name.strip(),
                "cik": str(int(cik)),
            }
        )

    records.sort(
        key=lambda row: (int(row["cik"]), row["sec_name"])
    )

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = csv_path.with_suffix(".csv.tmp")

    with temporary_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=["sec_name", "cik"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(records)

    temporary_path.replace(csv_path)
    return records