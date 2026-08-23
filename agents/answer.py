"""Answer natural-language questions using the curated 13F dataset."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

from agents.data_access import (
    available_managers,
    available_quarters,
    load_dataset,
)
from agents.planner import plan_question
from agents.query_engine import execute_plan, null_answer


ALLOWED_UNITS = {
    "USD",
    "SHARES",
    "COUNT",
    "PERCENT",
    "NAME",
    "DATE",
    "NONE",
}

ACCESSION_PATTERN = re.compile(
    r"^\d{10}-\d{2}-\d{6}$"
)


def validate_answer(
    result: Any,
) -> dict[str, object]:
    """Validate model-facing output before returning it."""
    if not isinstance(result, dict):
        raise ValueError("Answer must be a dictionary.")

    answer = result.get("answer")
    unit = result.get("unit")
    sources = result.get("sources")

    valid_scalar = (
        answer is None
        or isinstance(answer, (str, int, float))
        and not isinstance(answer, bool)
    )

    valid_list = (
        isinstance(answer, list)
        and all(
            isinstance(item, (str, int, float))
            and not isinstance(item, bool)
            for item in answer
        )
    )

    if not valid_scalar and not valid_list:
        raise ValueError("Answer has an invalid type.")

    if unit not in ALLOWED_UNITS:
        raise ValueError("Answer has an invalid unit.")

    if not isinstance(sources, list):
        raise ValueError("Sources must be a list.")

    if not all(
        isinstance(source, str)
        and ACCESSION_PATTERN.fullmatch(source)
        for source in sources
    ):
        raise ValueError("One or more sources are invalid.")

    return {
        "answer": answer,
        "unit": unit,
        "sources": sorted(set(sources)),
    }


def main(question: str) -> dict[str, object]:
    """Answer one question without allowing failures to crash."""
    if not isinstance(question, str) or not question.strip():
        print("Question is empty.", file=sys.stderr)
        return null_answer()

    try:
        filings, holdings = load_dataset()

        plan = plan_question(
            question.strip(),
            available_managers(filings),
            available_quarters(filings),
        )

        result = execute_plan(
            plan,
            filings,
            holdings,
        )

        validated = validate_answer(result)

        if validated["answer"] is None:
            print(
                "The question is unsupported or the dataset "
                "does not contain enough information.",
                file=sys.stderr,
            )

        return validated

    except Exception as exc:
        print(
            f"Unable to answer safely: {exc}",
            file=sys.stderr,
        )
        return null_answer()


def cli() -> int:
    """Command-line entry point."""
    if len(sys.argv) < 2:
        print(
            "Usage: python -m agents.answer \"question\"",
            file=sys.stderr,
        )
        result = null_answer()
    else:
        question = " ".join(sys.argv[1:])
        result = main(question)

    # stdout contains JSON and nothing else.
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())