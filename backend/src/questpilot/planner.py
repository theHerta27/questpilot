from __future__ import annotations

import math
from collections import defaultdict
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from questpilot.harness.context import ExecutionContext
from questpilot.models import DropDatasetVersion, GeneratedPlan, QuestDropRate
from questpilot.schemas import FarmingStep, MaterialGapRequest, PlanRequest, PlanResult
from questpilot.services import GameService


class LocalPlanner:
    def __init__(self, session: Session, game_service: GameService) -> None:
        self.session = session
        self.game_service = game_service

    def create(self, request: PlanRequest, context: ExecutionContext) -> PlanResult:
        gap = self.game_service.material_gap(
            MaterialGapRequest(user_id=request.user_id, goals=request.goals)
        )
        dataset = self.session.scalar(
            select(DropDatasetVersion).order_by(DropDatasetVersion.fetched_at.desc())
        )
        plan_id = str(uuid4())
        if not dataset:
            return self._persist(
                request,
                PlanResult(
                    plan_id=plan_id,
                    run_id=context.run_id,
                    material_gap=gap,
                    steps=[],
                    total_ap=0,
                    available_ap=self._available_ap(request),
                    completion_ratio=0 if any(item.gap for item in gap.items) else 1,
                    status="no_verified_route",
                    dataset_version=None,
                    candidate_scope="未加载社区掉落率数据集",
                    warnings=["无已验证路线：请先导入固定版本的社区掉落率数据。"],
                    verified=True,
                ),
            )
        rates = list(
            self.session.scalars(
                select(QuestDropRate)
                .options(joinedload(QuestDropRate.dataset_version))
                .where(QuestDropRate.dataset_version_id == dataset.id)
            )
        )
        by_item: dict[int, list[QuestDropRate]] = defaultdict(list)
        for rate in rates:
            by_item[rate.item_id].append(rate)
        desired: list[tuple[QuestDropRate, int, int]] = []
        warnings = [
            "仅在固定的 10–20 个永久自由关卡候选集内比较，结果为局部最优。",
            "掉落率是社区观测值，期望值不保证单次实际掉落。",
        ]
        total_gap = sum(item.gap for item in gap.items)
        uncovered = 0
        for item in gap.items:
            if item.gap <= 0:
                continue
            candidates = by_item.get(item.material_id, [])
            if not candidates:
                uncovered += item.gap
                warnings.append(f"{item.material_name}：无已验证路线。")
                continue
            best = min(
                candidates,
                key=lambda row: (
                    row.ap_cost / (row.drop_rate_percent / 100),
                    -row.sample_runs,
                    row.quest_id,
                ),
            )
            runs = math.ceil(item.gap / (best.drop_rate_percent / 100))
            desired.append((best, runs, item.material_id))
        available_ap = self._available_ap(request)
        run_limit = self._available_runs(request)
        remaining_ap = available_ap
        remaining_runs = run_limit
        grouped: dict[int, FarmingStep] = {}
        expected_covered = 0.0
        for rate, wanted_runs, item_id in desired:
            allowed = min(wanted_runs, remaining_ap // rate.ap_cost, remaining_runs)
            if allowed <= 0:
                continue
            if rate.quest_id not in grouped:
                grouped[rate.quest_id] = FarmingStep(
                    quest_id=rate.quest_id,
                    quest_name=rate.quest_name,
                    runs=0,
                    ap_cost=rate.ap_cost,
                    expected_drops={},
                    sample_runs=rate.sample_runs,
                )
            step = grouped[rate.quest_id]
            step.runs += allowed
            expected = allowed * rate.drop_rate_percent / 100
            step.expected_drops[item_id] = step.expected_drops.get(item_id, 0) + expected
            item_gap = next(i.gap for i in gap.items if i.material_id == item_id)
            expected_covered += min(expected, item_gap)
            remaining_ap -= allowed * rate.ap_cost
            remaining_runs -= allowed
        steps = sorted(grouped.values(), key=lambda item: item.quest_id)
        total_ap = sum(step.runs * step.ap_cost for step in steps)
        ratio = 1.0 if total_gap == 0 else min(1.0, expected_covered / total_gap)
        if uncovered == total_gap and total_gap:
            status = "no_verified_route"
        elif ratio >= 0.999 and uncovered == 0:
            status = "complete"
        else:
            status = "partial"
            warnings.append("当前体力、时间或数据覆盖不足，已给出不越界的降级方案。")
        result = PlanResult(
            plan_id=plan_id,
            run_id=context.run_id,
            material_gap=gap,
            steps=steps,
            total_ap=total_ap,
            available_ap=available_ap,
            completion_ratio=round(ratio, 4),
            status=status,
            dataset_version=dataset.version,
            candidate_scope=f"{len({row.quest_id for row in rates})} 个版本固定的永久自由关卡",
            warnings=warnings,
            verified=total_ap <= available_ap and sum(step.runs for step in steps) <= run_limit,
        )
        context.emit(
            "verification.completed",
            "LocalPlanner",
            "completed" if result.verified else "failed",
            payload_summary={
                "total_ap": total_ap,
                "available_ap": available_ap,
                "run_limit": run_limit,
                "dataset_version": dataset.version,
            },
            finished=True,
        )
        return self._persist(request, result)

    def _available_ap(self, request: PlanRequest) -> int:
        result = request.current_ap + request.golden_apples * request.ap_per_apple
        if request.deadline:
            deadline = request.deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=UTC)
            minutes = max(0, int((deadline - datetime.now(UTC)).total_seconds() / 60))
            result += minutes // 5
        return result

    def _available_runs(self, request: PlanRequest) -> int:
        days = 1
        if request.deadline:
            deadline = request.deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=UTC)
            seconds = max(0, (deadline - datetime.now(UTC)).total_seconds())
            days = max(1, math.ceil(seconds / 86_400))
        return (days * request.daily_minutes) // request.minutes_per_run

    def _persist(self, request: PlanRequest, result: PlanResult) -> PlanResult:
        self.session.add(
            GeneratedPlan(
                id=result.plan_id,
                run_id=result.run_id,
                user_id=request.user_id,
                request_json=request.model_dump(mode="json"),
                result_json=result.model_dump(mode="json"),
                status=result.status,
            )
        )
        self.session.commit()
        return result

    def get(self, plan_id: str) -> PlanResult | None:
        row = self.session.get(GeneratedPlan, plan_id)
        return PlanResult.model_validate(row.result_json) if row else None
