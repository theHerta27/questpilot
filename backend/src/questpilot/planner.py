from __future__ import annotations

import math
from collections import defaultdict
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from questpilot.harness.context import ExecutionContext
from questpilot.models import DropDatasetVersion, GeneratedPlan, QuestDropRate
from questpilot.optimization import (
    BoundedBranchAndBoundPlanner,
    CandidateQuest,
    GreedyBaselinePlanner,
)
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
                    solver="none",
                    optimality="no_solution",
                    degraded=True,
                ),
            )
        rates = list(
            self.session.scalars(
                select(QuestDropRate)
                .options(joinedload(QuestDropRate.dataset_version))
                .where(QuestDropRate.dataset_version_id == dataset.id)
            )
        )
        by_quest: dict[int, list[QuestDropRate]] = defaultdict(list)
        for rate in rates:
            by_quest[rate.quest_id].append(rate)
        candidates = [
            CandidateQuest(
                quest_id=quest_id,
                quest_name=rows[0].quest_name,
                ap_cost=rows[0].ap_cost,
                rates={
                    row.item_id: row.drop_rate_percent / 100
                    for row in rows
                },
                sample_runs=min(row.sample_runs for row in rows),
            )
            for quest_id, rows in sorted(by_quest.items())
        ]
        gaps = {item.material_id: item.gap for item in gap.items if item.gap > 0}
        warnings = [
            f"仅在固定的 {len(candidates)} 个永久自由关卡候选集内比较。",
            "掉落率是社区观测值，期望值不保证单次实际掉落。",
        ]
        total_gap = sum(item.gap for item in gap.items)
        uncovered_ids = []
        for item in gap.items:
            if item.gap > 0 and not any(
                candidate.rates.get(item.material_id, 0) > 0
                for candidate in candidates
            ):
                uncovered_ids.append(item.material_id)
                warnings.append(f"{item.material_name}：无已验证路线。")

        baseline = GreedyBaselinePlanner().solve(gaps, candidates)
        optimized = BoundedBranchAndBoundPlanner().solve(
            gaps,
            candidates,
            baseline,
            node_limit=request.planner_node_limit,
            timeout_ms=request.planner_timeout_ms,
        )
        available_ap = self._available_ap(request)
        run_limit = self._available_runs(request)
        if (
            optimized.complete
            and optimized.total_ap <= available_ap
            and optimized.total_runs <= run_limit
        ):
            chosen = optimized
        else:
            chosen = GreedyBaselinePlanner().solve(
                gaps,
                candidates,
                max_ap=available_ap,
                max_runs=run_limit,
            )
            if optimized.complete:
                warnings.append("资源边界不足以执行完整路线，已返回受约束的基线方案。")

        candidate_by_id = {candidate.quest_id: candidate for candidate in candidates}
        steps = [
            FarmingStep(
                quest_id=quest_id,
                quest_name=candidate_by_id[quest_id].quest_name,
                runs=runs,
                ap_cost=candidate_by_id[quest_id].ap_cost,
                expected_drops={
                    item_id: round(runs * rate, 4)
                    for item_id, rate in candidate_by_id[quest_id].rates.items()
                    if item_id in gaps
                },
                sample_runs=candidate_by_id[quest_id].sample_runs,
                image_url=f"/api/v1/assets/quests/{quest_id}.png",
            )
            for quest_id, runs in sorted(chosen.counts.items())
            if runs > 0
        ]
        total_ap = chosen.total_ap
        expected_covered = sum(
            min(chosen.coverage.get(item.material_id, 0), item.gap)
            for item in gap.items
        )
        ratio = 1.0 if total_gap == 0 else min(1.0, expected_covered / total_gap)
        if not steps and total_gap:
            status = "no_verified_route"
        elif chosen.complete and not uncovered_ids:
            status = "complete"
        else:
            status = "partial"
            warnings.append("当前体力、时间或数据覆盖不足，已给出不越界的降级方案。")
        if chosen.limit_hit:
            warnings.append(
                "搜索达到节点或时间上限；返回 best-so-far，不声明已证明局部最优。"
            )
        elif chosen.optimality == "local_optimal":
            warnings.append(
                "已在固定候选集内证明局部最优：最小期望 AP；同 AP 时刷取次数更少。"
            )

        metadata = dataset.metadata_json or {}
        verified = (
            total_ap <= available_ap
            and chosen.total_runs <= run_limit
            and (
                status != "complete"
                or all(
                    chosen.coverage.get(material_id, 0) + 1e-9 >= wanted
                    for material_id, wanted in gaps.items()
                )
            )
        )
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
            candidate_scope=f"{len(candidates)} 个版本固定的永久自由关卡",
            warnings=warnings,
            verified=verified,
            solver=chosen.solver,
            optimality=chosen.optimality,
            search_nodes=chosen.search_nodes,
            search_limit_hit=chosen.limit_hit,
            degraded=status != "complete" or chosen.limit_hit,
            dataset_fetched_at=dataset.fetched_at,
            dataset_source_url=dataset.source.source_url,
            dataset_license_status=dataset.source.license_status,
            minimum_sample_runs=int(metadata.get("minimum_sample_runs", 0)),
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
                "solver": result.solver,
                "optimality": result.optimality,
                "search_nodes": result.search_nodes,
                "search_limit_hit": result.search_limit_hit,
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
