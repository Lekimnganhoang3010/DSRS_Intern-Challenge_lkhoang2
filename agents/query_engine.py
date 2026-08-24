"""Execute validated query plans against the read-only dataset."""

from __future__ import annotations

import re

from agents.data_access import build_filing_index


def normalize_text(value: str) -> str:
    """Normalize free text for case-insensitive matching."""
    return re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()


def issuer_matches(
    filed_name: str,
    search_term: str,
) -> bool:
    """Check whether an issuer name contains the requested term."""
    normalized_name = normalize_text(filed_name)
    normalized_term = normalize_text(search_term)

    return bool(
        normalized_term
        and normalized_term in normalized_name
    )


def null_answer() -> dict[str, object]:
    """Return the required shape for an unsupported question."""
    return {
        "answer": None,
        "unit": "NONE",
        "sources": [],
    }


def largest_position(
    quarter: str,
    issuer: str,
    filings: list[dict[str, object]],
    holdings: list[dict[str, object]],
) -> dict[str, object]:
    """Find the manager with the largest issuer position by value."""
    filing_index = build_filing_index(filings)

    # Total matching position value for each manager.
    totals: dict[str, int] = {}
    sources: dict[str, set[str]] = {}

    for holding in holdings:
        if holding["report_quarter"] != quarter:
            continue

        if not issuer_matches(
            str(holding["name_of_issuer"]),
            issuer,
        ):
            continue

        accession = str(holding["accession_number"])
        filing = filing_index[accession]                                                   
        manager = str(filing["fund_name"])

        totals[manager] = (
            totals.get(manager, 0)
            + int(holding["value"])
        )

        sources.setdefault(manager, set()).add(accession)

    if not totals:
        return null_answer()

    # Alphabetical manager name breaks an exact-value tie.
    winner = sorted(
        totals,
        key=lambda manager: (
            -totals[manager],
            manager,
        ),
    )[0]

    return {
        "answer": winner,
        "unit": "NAME",
        "sources": sorted(sources[winner]),
    }

def resolve_manager(
    requested_name: str,
    filings: list[dict[str, object]],
) -> str | None:
    """Resolve a requested manager to its exact roster name."""
    requested = normalize_text(requested_name)

    matches = sorted(
        {
            str(filing["fund_name"])
            for filing in filings
            if normalize_text(str(filing["fund_name"])) == requested
        }
    )

    return matches[0] if len(matches) == 1 else None


def manager_filing(
    manager: str,
    quarter: str,
    filings: list[dict[str, object]],
) -> dict[str, object] | None:
    """Find one manager's filing for one quarter."""
    matches = [
        filing
        for filing in filings
        if filing["fund_name"] == manager
        and filing["report_quarter"] == quarter
    ]

    return matches[0] if len(matches) == 1 else None


def distinct_issuer_count(
    manager_name: str,
    quarter: str,
    filings: list[dict[str, object]],
    holdings: list[dict[str, object]],
) -> dict[str, object]:
    """Count distinct filed issuer names for a manager-quarter."""
    manager = resolve_manager(manager_name, filings)

    if manager is None:
        return null_answer()

    filing = manager_filing(manager, quarter, filings)

    if filing is None:
        return null_answer()

    accession = str(filing["accession_number"])

    issuers = {
        normalize_text(str(holding["name_of_issuer"]))
        for holding in holdings
        if holding["accession_number"] == accession
    }

    return {
        "answer": len(issuers),
        "unit": "COUNT",
        "sources": [accession],
    }


def total_portfolio_value(
    manager_name: str,
    quarter: str,
    filings: list[dict[str, object]],
) -> dict[str, object]:
    """Return the value declared on the filing cover page."""
    manager = resolve_manager(manager_name, filings)

    if manager is None:
        return null_answer()

    filing = manager_filing(manager, quarter, filings)

    if filing is None:
        return null_answer()

    value = filing["table_value_total"]

    if value is None:
        return null_answer()

    return {
        "answer": int(value),
        "unit": "USD",
        "sources": [str(filing["accession_number"])],
    }


def managers_by_form(
    quarter: str,
    form_type: str,
    filings: list[dict[str, object]],
) -> dict[str, object]:
    """List managers that filed a requested form in one quarter."""
    matches = [
        filing
        for filing in filings
        if filing["report_quarter"] == quarter
        and filing["form_type"] == form_type
    ]

    return {
        "answer": sorted(
            str(filing["fund_name"])
            for filing in matches
        ),
        "unit": "NAME",
        "sources": sorted(
            str(filing["accession_number"])
            for filing in matches
        ),
    }


def manager_has_issuer(
    manager_name: str,
    quarter: str,
    issuer: str,
    filings: list[dict[str, object]],
    holdings: list[dict[str, object]],
) -> dict[str, object]:
    """Check whether a manager directly reported an issuer."""
    manager = resolve_manager(manager_name, filings)

    if manager is None:
        return null_answer()

    filing = manager_filing(manager, quarter, filings)

    if filing is None:
        return null_answer()

    accession = str(filing["accession_number"])

    found = any(
        holding["accession_number"] == accession
        and issuer_matches(
            str(holding["name_of_issuer"]),
            issuer,
        )
        for holding in holdings
    )

    return {
        "answer": "Yes" if found else "No",
        "unit": "NONE",
        "sources": [accession],
    }


def most_option_positions(
    quarter: str,
    option_type: str,
    filings: list[dict[str, object]],
    holdings: list[dict[str, object]],
) -> dict[str, object]:
    """Find the manager reporting the most option entries."""
    filing_index = build_filing_index(filings)
    counts: dict[str, int] = {}
    sources: dict[str, set[str]] = {}

    for holding in holdings:
        if holding["report_quarter"] != quarter:
            continue

        put_call = holding["put_call"]

        if put_call is None:
            continue

        if str(put_call).upper() != option_type:
            continue

        accession = str(holding["accession_number"])
        manager = str(filing_index[accession]["fund_name"])

        counts[manager] = counts.get(manager, 0) + 1
        sources.setdefault(manager, set()).add(accession)

    if not counts:
        return null_answer()

    winner = sorted(
        counts,
        key=lambda manager: (-counts[manager], manager),
    )[0]

    return {
        "answer": winner,
        "unit": "NAME",
        "sources": sorted(sources[winner]),
    }


def largest_share_increase(
    later_quarter: str,
    earlier_quarter: str,
    issuer: str,
    filings: list[dict[str, object]],
    holdings: list[dict[str, object]],
) -> dict[str, object]:
    """Find the manager with the largest increase in direct shares."""
    filing_index = build_filing_index(filings)

    totals: dict[tuple[str, str], int] = {}

    for holding in holdings:
        quarter = str(holding["report_quarter"])

        if quarter not in {earlier_quarter, later_quarter}:
            continue

        if not issuer_matches(
            str(holding["name_of_issuer"]),
            issuer,
        ):
            continue

        # Exclude options and principal amounts.
        if holding["put_call"] is not None:
            continue

        if holding["ssh_prnamt_type"] != "SH":
            continue

        accession = str(holding["accession_number"])
        manager = str(filing_index[accession]["fund_name"])
        key = (manager, quarter)

        totals[key] = (
            totals.get(key, 0)
            + int(holding["ssh_prnamt"])
        )

    managers = {
        manager
        for manager, _quarter in totals
    }

    if not managers:
        return null_answer()

    changes = {
        manager: (
            totals.get((manager, later_quarter), 0)
            - totals.get((manager, earlier_quarter), 0)
        )
        for manager in managers
    }

    winner = sorted(
        changes,
        key=lambda manager: (-changes[manager], manager),
    )[0]

    supporting_filings = [
        filing
        for filing in filings
        if filing["fund_name"] == winner
        and filing["report_quarter"]
        in {earlier_quarter, later_quarter}
    ]

    return {
        "answer": winner,
        "unit": "NAME",
        "sources": sorted(
            str(filing["accession_number"])
            for filing in supporting_filings
        ),
    }


def manager_largest_position(
    manager_name: str,
    quarter: str,
    filings: list[dict[str, object]],
    holdings: list[dict[str, object]],
) -> dict[str, object]:
    """Return one manager's largest individual position by value."""
    manager = resolve_manager(manager_name, filings)

    if manager is None:
        return null_answer()

    filing = manager_filing(manager, quarter, filings)

    if filing is None:
        return null_answer()

    accession = str(filing["accession_number"])

    matches = [
        holding
        for holding in holdings
        if holding["accession_number"] == accession
    ]

    if not matches:
        return null_answer()

    largest = sorted(
        matches,
        key=lambda holding: (
            -int(holding["value"]),
            normalize_text(str(holding["name_of_issuer"])),
            str(holding["cusip"]),
        ),
    )[0]

    return {
        "answer": [
            str(largest["name_of_issuer"]),
            int(largest["value"]),
        ],
        "unit": "USD",
        "sources": [accession],
    }


def issuer_quarter_change(
    later_quarter: str,
    earlier_quarter: str,
    issuer: str,
    filings: list[dict[str, object]],
    holdings: list[dict[str, object]],
) -> dict[str, object]:
    """Describe share changes for managers holding an issuer in both quarters."""
    filing_index = build_filing_index(filings)
    totals: dict[tuple[str, str], int] = {}

    for holding in holdings:
        quarter = str(holding["report_quarter"])

        if quarter not in {earlier_quarter, later_quarter}:
            continue

        if not issuer_matches(
            str(holding["name_of_issuer"]),
            issuer,
        ):
            continue

        if holding["put_call"] is not None:
            continue

        if holding["ssh_prnamt_type"] != "SH":
            continue

        accession = str(holding["accession_number"])
        manager = str(filing_index[accession]["fund_name"])
        key = (manager, quarter)

        totals[key] = (
            totals.get(key, 0)
            + int(holding["ssh_prnamt"])
        )

    managers_in_both = sorted(
        {
            manager
            for manager, _quarter in totals
            if totals.get((manager, earlier_quarter), 0) > 0
            and totals.get((manager, later_quarter), 0) > 0
        }
    )

    if not managers_in_both:
        return null_answer()

    answers: list[str] = []
    source_accessions: set[str] = set()

    for manager in managers_in_both:
        earlier = totals[(manager, earlier_quarter)]
        later = totals[(manager, later_quarter)]

        if later > earlier:
            direction = "grew"
        elif later < earlier:
            direction = "shrank"
        else:
            direction = "was unchanged"

        answers.append(f"{manager}: {direction}")

        for filing in filings:
            if (
                filing["fund_name"] == manager
                and filing["report_quarter"]
                in {earlier_quarter, later_quarter}
            ):
                source_accessions.add(
                    str(filing["accession_number"])
                )

    return {
        "answer": answers,
        "unit": "NONE",
        "sources": sorted(source_accessions),
    }


def execute_plan(
    plan: dict[str, object],
    filings: list[dict[str, object]],
    holdings: list[dict[str, object]],
) -> dict[str, object]:
    """Execute only approved query operations."""
    intent = plan.get("intent")
    quarter = plan.get("quarter")
    manager = plan.get("manager")
    issuer = plan.get("issuer")
    form_type = plan.get("form_type")

    if intent == "largest_position":
        if not isinstance(quarter, str):
            return null_answer()
        if not isinstance(issuer, str):
            return null_answer()

        return largest_position(
            quarter,
            issuer,
            filings,
            holdings,
        )

    if intent == "distinct_issuer_count":
        if not isinstance(manager, str):
            return null_answer()
        if not isinstance(quarter, str):
            return null_answer()

        return distinct_issuer_count(
            manager,
            quarter,
            filings,
            holdings,
        )

    if intent == "total_portfolio_value":
        if not isinstance(manager, str):
            return null_answer()
        if not isinstance(quarter, str):
            return null_answer()

        return total_portfolio_value(
            manager,
            quarter,
            filings,
        )

    if intent == "managers_by_form":
        if not isinstance(quarter, str):
            return null_answer()
        if not isinstance(form_type, str):
            return null_answer()

        return managers_by_form(
            quarter,
            form_type,
            filings,
        )

    if intent == "manager_has_issuer":
        if not isinstance(manager, str):
            return null_answer()
        if not isinstance(quarter, str):
            return null_answer()
        if not isinstance(issuer, str):
            return null_answer()

        return manager_has_issuer(
            manager,
            quarter,
            issuer,
            filings,
            holdings,
        )

    if intent == "most_option_positions":
        option_type = plan.get("option_type")

        if not isinstance(quarter, str):
            return null_answer()
        if not isinstance(option_type, str):
            return null_answer()

        return most_option_positions(
            quarter,
            option_type,
            filings,
            holdings,
        )

    if intent == "largest_share_increase":
        comparison_quarter = plan.get("comparison_quarter")

        if not isinstance(quarter, str):
            return null_answer()
        if not isinstance(comparison_quarter, str):
            return null_answer()
        if not isinstance(issuer, str):
            return null_answer()

        return largest_share_increase(
            later_quarter=quarter,
            earlier_quarter=comparison_quarter,
            issuer=issuer,
            filings=filings,
            holdings=holdings,
        )

    if intent == "manager_largest_position":
        if not isinstance(manager, str):
            return null_answer()
        if not isinstance(quarter, str):
            return null_answer()

        return manager_largest_position(
            manager,
            quarter,
            filings,
            holdings,
        )

    if intent == "issuer_quarter_change":
        comparison_quarter = plan.get("comparison_quarter")

        if not isinstance(quarter, str):
            return null_answer()
        if not isinstance(comparison_quarter, str):
            return null_answer()
        if not isinstance(issuer, str):
            return null_answer()

        return issuer_quarter_change(
            later_quarter=quarter,
            earlier_quarter=comparison_quarter,
            issuer=issuer,
            filings=filings,
            holdings=holdings,
        )

    return null_answer()