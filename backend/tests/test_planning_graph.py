from __future__ import annotations

from sqlalchemy import select

from questpilot.agent_graph import PlanningGraph
from questpilot.harness.context import ExecutionContext
from questpilot.harness.events import InMemoryEventSink
from questpilot.harness.persistence import CheckpointStore
from questpilot.models import AgentCheckpoint
from questpilot.planner import LocalPlanner
from questpilot.repositories import GameRepository
from questpilot.schemas import PlanRequest, SkillGoal
from questpilot.services import GameService


def test_graph_builds_verified_local_plan_and_checkpoints(seeded_session):
    repository = GameRepository(seeded_session)
    service = GameService(repository)
    character = repository.search_characters("蓝呆")[0]
    request = PlanRequest(
        goals=[
            SkillGoal(
                character_id=character.id,
                skill_number=1,
                current_level=1,
                target_level=4,
            )
        ],
        current_ap=10_000,
        daily_minutes=600,
    )
    sink = InMemoryEventSink()
    context = ExecutionContext(event_sink=sink)
    graph = PlanningGraph(
        LocalPlanner(seeded_session, service),
        service,
        CheckpointStore(seeded_session),
    )
    result = graph.invoke(request, context)
    assert result.verified
    assert result.status == "complete"
    assert result.dataset_version == "demo-2026.07"
    assert result.total_ap <= result.available_ap
    assert "局部最优" in " ".join(result.warnings)
    checkpoints = list(
        seeded_session.scalars(
            select(AgentCheckpoint).where(AgentCheckpoint.run_id == context.run_id)
        )
    )
    assert len(checkpoints) >= 9
    dataset_checkpoint = next(
        checkpoint for checkpoint in checkpoints if checkpoint.node_name == "load_drop_dataset"
    )
    assert dataset_checkpoint.state_json["dataset_version"] == "demo-2026.07"
    assert dataset_checkpoint.state_json["planner_version"] == "p3b-v1"
    assert any(
        event.component == "DeterministicPlanValidator"
        and event.event_type == "verification.completed"
        for event in sink.events_for(context.run_id)
    )


def test_planner_never_exceeds_available_ap(seeded_session):
    repository = GameRepository(seeded_session)
    service = GameService(repository)
    character = repository.search_characters("玛修")[0]
    result = LocalPlanner(seeded_session, service).create(
        PlanRequest(
            goals=[
                SkillGoal(
                    character_id=character.id,
                    skill_number=1,
                    current_level=1,
                    target_level=10,
                )
            ],
            current_ap=5,
            daily_minutes=3,
        ),
        ExecutionContext(),
    )
    assert result.total_ap <= 5
    assert result.status in {"partial", "no_verified_route"}


def test_planner_returns_best_so_far_when_search_node_limit_is_hit(seeded_session):
    repository = GameRepository(seeded_session)
    service = GameService(repository)
    character = repository.search_characters("蓝呆")[0]
    result = LocalPlanner(seeded_session, service).create(
        PlanRequest(
            goals=[
                SkillGoal(
                    character_id=character.id,
                    skill_number=1,
                    current_level=1,
                    target_level=4,
                )
            ],
            current_ap=10_000,
            daily_minutes=600,
            planner_node_limit=1,
        ),
        ExecutionContext(),
    )
    assert result.status == "complete"
    assert result.search_limit_hit
    assert result.optimality == "best_so_far"
    assert result.degraded


def test_graph_can_resume_from_persisted_checkpoint(seeded_session):
    repository = GameRepository(seeded_session)
    service = GameService(repository)
    character = repository.search_characters("蓝呆")[0]
    request = PlanRequest(
        goals=[
            SkillGoal(
                character_id=character.id,
                skill_number=1,
                current_level=1,
                target_level=2,
            )
        ],
        current_ap=1_000,
    )
    store = CheckpointStore(seeded_session)
    store.save(
        "interrupted-run",
        "calculate_gap",
        {
            "request": request.model_dump(mode="json"),
            "parsed_goal": request.model_dump(mode="json"),
            "character_ids": [character.id],
            "account": {"inventory": []},
            "gap": {},
        },
    )
    context = ExecutionContext(run_id="interrupted-run")
    graph = PlanningGraph(LocalPlanner(seeded_session, service), service, store)
    result = graph.resume("interrupted-run", context)
    assert result.verified
    assert result.steps
