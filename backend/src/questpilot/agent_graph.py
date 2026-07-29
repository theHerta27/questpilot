from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from questpilot.harness.context import ExecutionContext
from questpilot.harness.persistence import CheckpointStore
from questpilot.harness.policy import ContextBuilder, ExecutionBudget, ExecutionPolicy
from questpilot.models import DropDatasetVersion, GeneratedPlan, QuestDropRate
from questpilot.planner import LocalPlanner
from questpilot.planning_validation import DeterministicPlanValidator
from questpilot.schemas import MaterialGapRequest, PlanRequest, PlanResult
from questpilot.services import GameService


class PlanState(TypedDict, total=False):
    request: PlanRequest
    context: ExecutionContext
    parsed_goal: dict[str, Any]
    character_ids: list[int]
    account: dict[str, Any]
    bounded_context: dict[str, Any]
    gap: dict[str, Any]
    dataset_loaded: bool
    candidate_count: int
    atlas_version: str | None
    dataset_version: str | None
    planner_version: str
    candidate_filter: dict[str, Any]
    result: PlanResult
    route: str
    validation_evidence: dict[str, Any]
    validation_errors: list[str]


class PlanningGraph:
    NODE_ORDER = [
        "parse_goal",
        "resolve_entities",
        "load_account",
        "calculate_gap",
        "load_drop_dataset",
        "search_candidates",
        "generate_plan",
        "validate_plan",
    ]

    def __init__(
        self,
        planner: LocalPlanner,
        game_service: GameService,
        checkpoints: CheckpointStore,
    ) -> None:
        self.planner = planner
        self.game_service = game_service
        self.checkpoints = checkpoints
        graph = StateGraph(PlanState)
        for name in self.NODE_ORDER:
            graph.add_node(name, self._wrap(name, getattr(self, name)))
        graph.add_node("fallback", self._wrap("fallback", self.fallback))
        graph.add_node("complete", self._wrap("complete", self.complete))
        graph.set_entry_point("parse_goal")
        for left, right in zip(self.NODE_ORDER[:-1], self.NODE_ORDER[1:], strict=True):
            graph.add_edge(left, right)
        graph.add_conditional_edges(
            "validate_plan",
            lambda state: state["route"],
            {"fallback": "fallback", "complete": "complete"},
        )
        graph.add_edge("fallback", END)
        graph.add_edge("complete", END)
        self.graph = graph.compile()

    def _wrap(self, name: str, handler):
        def node(state: PlanState) -> PlanState:
            context = state["context"]
            budget = context.metadata.setdefault(
                "budget", ExecutionBudget(context.policy or ExecutionPolicy())
            )
            budget.visit_node(name, context.elapsed_seconds)
            context.emit("run.node.started", name, "started")
            try:
                update = handler(state)
                serializable = self._serializable_state({**state, **update})
                self.checkpoints.save(context.run_id, name, serializable)
            except Exception as exc:
                context.emit(
                    "run.node.failed",
                    name,
                    "failed",
                    error={"type": type(exc).__name__, "message": str(exc)},
                    finished=True,
                )
                raise
            context.emit(
                "run.node.completed",
                name,
                "completed",
                payload_summary={"checkpoint": True},
                finished=True,
            )
            return update

        return node

    @staticmethod
    def _serializable_state(state: PlanState) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in state.items():
            if key == "context":
                continue
            if hasattr(value, "model_dump"):
                result[key] = value.model_dump(mode="json")
            else:
                result[key] = value
        return result

    def invoke(self, request: PlanRequest, context: ExecutionContext) -> PlanResult:
        context.emit(
            "run.started",
            "PlanningGraph",
            "started",
            payload_summary={"goal_count": len(request.goals)},
        )
        final = self.graph.invoke({"request": request, "context": context})
        result = final["result"]
        context.emit(
            "run.completed",
            "PlanningGraph",
            "completed",
            payload_summary={"plan_id": result.plan_id, "status": result.status},
            finished=True,
        )
        return result

    def resume(self, run_id: str, context: ExecutionContext) -> PlanResult:
        checkpoint = self.checkpoints.latest(run_id)
        if not checkpoint:
            raise KeyError(f"no checkpoint found for run: {run_id}")
        saved = dict(checkpoint.state_json)
        saved["request"] = PlanRequest.model_validate(saved["request"])
        if saved.get("result"):
            saved["result"] = PlanResult.model_validate(saved["result"])
        saved["context"] = context
        context.emit(
            "run.resumed",
            "PlanningGraph",
            "started",
            payload_summary={"checkpoint_node": checkpoint.node_name},
        )
        if checkpoint.node_name in {"complete", "fallback"}:
            return saved["result"]
        start_index = self.NODE_ORDER.index(checkpoint.node_name) + 1
        state: PlanState = saved
        for name in self.NODE_ORDER[start_index:]:
            state.update(self._wrap(name, getattr(self, name))(state))
        branch = state["route"]
        state.update(self._wrap(branch, getattr(self, branch))(state))
        context.emit(
            "run.completed",
            "PlanningGraph",
            "completed",
            payload_summary={"resumed": True, "plan_id": state["result"].plan_id},
            finished=True,
        )
        return state["result"]

    def parse_goal(self, state: PlanState) -> PlanState:
        request = state["request"]
        return {"parsed_goal": request.model_dump(mode="json")}

    def resolve_entities(self, state: PlanState) -> PlanState:
        return {"character_ids": sorted({goal.character_id for goal in state["request"].goals})}

    def load_account(self, state: PlanState) -> PlanState:
        inventory = self.game_service.inventory(state["request"].user_id)
        account = {"inventory": [item.model_dump() for item in inventory]}
        bounded = ContextBuilder().build(
            goal=state["parsed_goal"],
            account_snapshot=account,
        )
        return {"account": account, "bounded_context": bounded}

    def calculate_gap(self, state: PlanState) -> PlanState:
        request = state["request"]
        gap = self.game_service.material_gap(
            MaterialGapRequest(user_id=request.user_id, goals=request.goals)
        )
        return {"gap": gap.model_dump(mode="json")}

    def load_drop_dataset(self, _: PlanState) -> PlanState:
        from sqlalchemy import select

        dataset = self.planner.session.scalar(
            select(DropDatasetVersion).order_by(DropDatasetVersion.fetched_at.desc())
        )
        atlas = self.game_service.repository.latest_atlas_snapshot()
        return {
            "dataset_loaded": dataset is not None,
            "dataset_version": dataset.version if dataset else None,
            "atlas_version": (
                atlas.upstream_hash or atlas.content_sha256[:12] if atlas else None
            ),
            "planner_version": "p3b-v1",
        }

    def search_candidates(self, _: PlanState) -> PlanState:
        from sqlalchemy import func, select

        dataset = self.planner.session.scalar(
            select(DropDatasetVersion).order_by(DropDatasetVersion.fetched_at.desc())
        )
        count = (
            self.planner.session.scalar(
                select(func.count(func.distinct(QuestDropRate.quest_id))).where(
                    QuestDropRate.dataset_version_id == dataset.id
                )
            )
            if dataset
            else 0
        )
        metadata = dataset.metadata_json if dataset else {}
        return {
            "candidate_count": int(count or 0),
            "candidate_filter": {
                "permanent_free_only": True,
                "random_enemy_excluded": True,
                "minimum_sample_runs": int(
                    (metadata or {}).get("minimum_sample_runs", 0)
                ),
                "fixed_manifest_scope": True,
            },
        }

    def generate_plan(self, state: PlanState) -> PlanState:
        return {"result": self.planner.create(state["request"], state["context"])}

    def validate_plan(self, state: PlanState) -> PlanState:
        from sqlalchemy import select

        result = state["result"]
        dataset = self.planner.session.scalar(
            select(DropDatasetVersion).order_by(DropDatasetVersion.fetched_at.desc())
        )
        allowed_quest_ids = (
            set(
                self.planner.session.scalars(
                    select(QuestDropRate.quest_id)
                    .where(QuestDropRate.dataset_version_id == dataset.id)
                    .distinct()
                )
            )
            if dataset
            else set()
        )
        context = state["context"]
        context.emit(
            "verification.started",
            "DeterministicPlanValidator",
            "started",
            payload_summary={"plan_id": result.plan_id},
        )
        report = DeterministicPlanValidator().validate(
            state["request"],
            result,
            allowed_quest_ids=allowed_quest_ids,
            dataset_version=dataset.version if dataset else None,
        )
        if not report.valid:
            result.verified = False
            result.warnings.extend(f"验证失败：{error}" for error in report.errors)
            row = self.planner.session.get(GeneratedPlan, result.plan_id)
            if row:
                row.result_json = result.model_dump(mode="json")
                row.status = "validation_failed"
                self.planner.session.commit()
        context.emit(
            "verification.completed" if report.valid else "verification.failed",
            "DeterministicPlanValidator",
            "completed" if report.valid else "failed",
            payload_summary=report.evidence,
            error=None if report.valid else {"errors": report.errors},
            finished=True,
        )
        route = (
            "complete"
            if report.valid and result.verified and result.status == "complete"
            else "fallback"
        )
        return {
            "route": route,
            "validation_evidence": report.evidence,
            "validation_errors": report.errors,
        }

    def fallback(self, state: PlanState) -> PlanState:
        result = state["result"]
        if not any("降级方案" in warning for warning in result.warnings):
            result.warnings.append("已进入降级分支；不会猜测未验证的掉落路线。")
        return {"result": result}

    def complete(self, state: PlanState) -> PlanState:
        return {"result": state["result"]}
