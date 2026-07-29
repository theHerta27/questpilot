from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    input: dict[str, Any]
    expected: dict[str, Any]


class EvaluationRunner:
    def run(
        self,
        cases: list[EvaluationCase],
        handler: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        results = []
        for case in cases:
            actual = handler(case.input)
            passed = all(actual.get(key) == value for key, value in case.expected.items())
            results.append(
                {
                    "case_id": case.case_id,
                    "passed": passed,
                    "expected": case.expected,
                    "actual": actual,
                }
            )
        passed_count = sum(item["passed"] for item in results)
        return {
            "total": len(results),
            "passed": passed_count,
            "pass_rate": passed_count / len(results) if results else 1,
            "results": results,
        }

    def compare(self, baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
        baseline_results = {item["case_id"]: item for item in baseline.get("results", [])}
        current_results = {item["case_id"]: item for item in current.get("results", [])}
        regressions = [
            case_id
            for case_id, item in current_results.items()
            if not item["passed"] and baseline_results.get(case_id, {}).get("passed")
        ]
        improvements = [
            case_id
            for case_id, item in current_results.items()
            if item["passed"] and baseline_results.get(case_id, {}).get("passed") is False
        ]
        return {
            "baseline_pass_rate": baseline.get("pass_rate", 0),
            "current_pass_rate": current.get("pass_rate", 0),
            "regressions": regressions,
            "improvements": improvements,
        }


def default_gap_cases() -> list[EvaluationCase]:
    return [
        EvaluationCase(
            case_id=f"gap-{required:02d}-{owned:02d}",
            input={"required": required, "owned": owned},
            expected={"gap": max(required - owned, 0)},
        )
        for required in range(5, 55, 5)
        for owned in range(0, 25, 5)
    ]
