"""Run the documented example questions and record LLM usage."""

from __future__ import annotations

import json
import time
from pathlib import Path

from agents.answer import main as answer_question
from agents.llm import usage


ROOT = Path(__file__).resolve().parents[1]
USAGE_PATH = ROOT / "output" / "agent_usage.json"

QUESTIONS = [
    "Which manager held the largest Apple position in 2026 Q2?",
    "Which manager added the most Nvidia shares between 2026 Q1 and 2026 Q2?",
    "How many distinct issuers did Renaissance Technologies LLC report in 2026 Q2?",
    "What was the total reported value of Citadel Advisors LLC's holdings in 2026 Q1?",
    "Which managers in the roster filed a 13F-NT instead of a 13F-HR for 2026 Q2?",
    "Did Pershing Square Capital Management report any Microsoft holdings directly in 2026 Q2?",
    "Which manager reported the most call options in 2026 Q2?",
    "What was Third Point LLC's largest position by value in 2026 Q1, and what was it?",
    "Which manager held Tesla in both 2026 Q1 and 2026 Q2, and did the position grow or shrink?",
    "What was the average portfolio value across all managers in 2026 Q3?",
]


def difference(
    after: dict[str, int],
    before: dict[str, int],
    key: str,
) -> int:
    """Calculate one usage counter's increase."""
    return int(after.get(key, 0)) - int(before.get(key, 0))


def main() -> int:
    question_usage: list[dict[str, object]] = []
    totals_before = usage()

    for question in QUESTIONS:
        before = usage()
        started = time.perf_counter()

        answer = answer_question(question)

        elapsed = time.perf_counter() - started
        after = usage()

        question_usage.append(
            {
                "question": question,
                "calls": difference(after, before, "calls"),
                "prompt_tokens": difference(
                    after, before, "prompt_tokens"
                ),
                "completion_tokens": difference(
                    after, before, "completion_tokens"
                ),
                "elapsed_seconds": round(elapsed, 3),
            }
        )

        print(question)
        print(json.dumps(answer, ensure_ascii=False))
        print()

    totals_after = usage()

    manifest = {
        "questions": question_usage,
        "totals": {
            "calls": difference(
                totals_after, totals_before, "calls"
            ),
            "prompt_tokens": difference(
                totals_after, totals_before, "prompt_tokens"
            ),
            "completion_tokens": difference(
                totals_after, totals_before, "completion_tokens"
            ),
        },
    }

    USAGE_PATH.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {USAGE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())