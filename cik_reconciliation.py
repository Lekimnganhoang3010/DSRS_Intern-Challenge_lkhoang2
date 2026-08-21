"""Reconcile supplied manager CIKs against the official SEC lookup."""

from __future__ import annotations

import csv
import re
from pathlib import Path


LEGAL_SUFFIXES = {
    "CO",
    "COMPANY",
    "CORP",
    "CORPORATION",
    "INC",
    "INCORPORATED",
    "LLC",
    "LP",
    "LTD",
    "LIMITED",
    "PLC",
}

MANUAL_CIK_OVERRIDES = {
    # SEC lookup has multiple Tudor entities; CIK 923093 is the 13F filer.
    "Tudor Investment Corp": "923093",
}


def normalize_name(name: str) -> str:
    """Normalize harmless differences without using fuzzy matching."""
    normalized = name.upper()

    # Remove explanatory labels such as "(Greenlight)" from the supplied roster.
    normalized = re.sub(r"\([^)]*\)", " ", normalized)

    # Remove SEC jurisdiction suffixes such as "/MA" or "/DE".
    normalized = re.sub(r"/[A-Z]{2}\b", " ", normalized)
    
    # Treat "&" and "AND" consistently.
    normalized = normalized.replace("&", " AND ")

    # Remove punctuation but retain letters, numbers, and spaces.
    normalized = re.sub(r"[^A-Z0-9\s]", "", normalized)

    tokens = normalized.split()

    # SEC sometimes appends "ET AL" to a filing-manager name.
    if len(tokens) >= 2 and tokens[-2:] == ["ET", "AL"]:
        tokens = tokens[:-2]

    # "The Baupost Group" and "Baupost Group" refer to the same name here.
    if tokens and tokens[0] == "THE":
        tokens = tokens[1:]

    # Legal suffix differences should not determine the match.
    while tokens and tokens[-1] in LEGAL_SUFFIXES:
        tokens.pop()

    return " ".join(tokens)


def reconcile_ciks(
    filers: list[dict[str, str]],
    lookup_records: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Verify supplied CIKs and correct uniquely identifiable mismatches."""
    supplied_ciks = {
        str(int(filer["cik"]))
        for filer in filers
    }

    target_names = {
        normalize_name(filer["fund_name"])
        for filer in filers
    }

    names_by_cik: dict[str, list[str]] = {
        cik: []
        for cik in supplied_ciks
    }

    candidate_ciks_by_name: dict[str, set[str]] = {
        name: set()
        for name in target_names
    }

    for record in lookup_records:
        record_cik = record["cik"]
        record_name = record["sec_name"]

        if record_cik in names_by_cik:
            names_by_cik[record_cik].append(record_name)

        normalized_record_name = normalize_name(record_name)

        if normalized_record_name in candidate_ciks_by_name:
            candidate_ciks_by_name[normalized_record_name].add(
                record_cik
            )

    reconciled: list[dict[str, str]] = []

    for filer in filers:
        fund_name = filer["fund_name"]
        supplied_cik = str(int(filer["cik"]))
        normalized_fund_name = normalize_name(fund_name)

        supplied_cik_names = names_by_cik.get(supplied_cik, [])

        supplied_cik_matches = any(
            normalize_name(sec_name) == normalized_fund_name
            for sec_name in supplied_cik_names
        )

        if supplied_cik_matches:
            final_cik = supplied_cik
            cik_source = "given"

        elif fund_name in MANUAL_CIK_OVERRIDES:
            final_cik = MANUAL_CIK_OVERRIDES[fund_name]
            cik_source = "corrected"

        else:
            candidates = candidate_ciks_by_name[
                normalized_fund_name
            ]

            if len(candidates) != 1:
                raise ValueError(
                    "Could not uniquely reconcile "
                    f"{fund_name!r}. Supplied CIK: {supplied_cik}. "
                    f"SEC names for supplied CIK: {supplied_cik_names}. "
                    f"Candidate CIKs: {sorted(candidates)}"
                )

            final_cik = next(iter(candidates))
            cik_source = "corrected"

        reconciled.append(
            {
                "fund_name": fund_name,
                "cik": final_cik,
                "cik_source": cik_source,
            }
        )

    reconciled.sort(key=lambda row: int(row["cik"]))
    return reconciled


def write_reconciled_filers(
    records: list[dict[str, str]],
    output_path: Path,
) -> None:
    """Write the reconciled 20-manager roster deterministically."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(".csv.tmp")

    with temporary_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=["fund_name", "cik", "cik_source"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(records)

    temporary_path.replace(output_path)