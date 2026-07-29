from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from questpilot.schemas import PlanRequest, PlanResult


@dataclass(frozen=True)
class ValidationReport:
    valid: bool
    errors: list[str]
    evidence: dict[str, object]


class DeterministicPlanValidator:
    def validate(
        self,
        request: PlanRequest,
        result: PlanResult,
        *,
        allowed_quest_ids: set[int],
        dataset_version: str | None,
    ) -> ValidationReport:
        errors: list[str] = []
        expected_available_ap = self._available_ap(request)
        run_limit = self._run_limit(request)
        calculated_ap = sum(step.runs * step.ap_cost for step in result.steps)
        calculated_runs = sum(step.runs for step in result.steps)
        if result.total_ap != calculated_ap:
            errors.append("total_ap does not equal the sum of route steps")
        if result.available_ap != expected_available_ap:
            errors.append("available_ap does not match request resources and deadline")
        if calculated_ap > expected_available_ap:
            errors.append("route exceeds available AP")
        if calculated_runs > run_limit:
            errors.append("route exceeds the time-derived run limit")
        outside_scope = sorted(
            {step.quest_id for step in result.steps}.difference(allowed_quest_ids)
        )
        if outside_scope:
            errors.append(f"route contains quests outside the fixed dataset: {outside_scope}")
        if result.dataset_version != dataset_version:
            errors.append("plan dataset version does not match the validated dataset")
        for item in result.material_gap.items:
            if item.gap != max(item.required - item.owned, 0):
                errors.append(f"material gap arithmetic is invalid for {item.material_name}")
        coverage: dict[int, float] = {}
        for step in result.steps:
            for material_id, amount in step.expected_drops.items():
                coverage[material_id] = coverage.get(material_id, 0) + amount
        if result.status == "complete":
            for item in result.material_gap.items:
                if coverage.get(item.material_id, 0) + 1e-9 < item.gap:
                    errors.append(f"complete route does not cover {item.material_name}")
        evidence = {
            "calculated_ap": calculated_ap,
            "available_ap": expected_available_ap,
            "calculated_runs": calculated_runs,
            "run_limit": run_limit,
            "candidate_quest_count": len(allowed_quest_ids),
            "dataset_version": dataset_version,
            "covered_material_count": len(
                [
                    item
                    for item in result.material_gap.items
                    if coverage.get(item.material_id, 0) + 1e-9 >= item.gap
                ]
            ),
            "target_material_count": len(result.material_gap.items),
        }
        return ValidationReport(valid=not errors, errors=errors, evidence=evidence)

    @staticmethod
    def _available_ap(request: PlanRequest) -> int:
        result = request.current_ap + request.golden_apples * request.ap_per_apple
        if request.deadline:
            deadline = request.deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=UTC)
            minutes = max(0, int((deadline - datetime.now(UTC)).total_seconds() / 60))
            result += minutes // 5
        return result

    @staticmethod
    def _run_limit(request: PlanRequest) -> int:
        days = 1
        if request.deadline:
            deadline = request.deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=UTC)
            seconds = max(0, (deadline - datetime.now(UTC)).total_seconds())
            days = max(1, math.ceil(seconds / 86_400))
        return (days * request.daily_minutes) // request.minutes_per_run
