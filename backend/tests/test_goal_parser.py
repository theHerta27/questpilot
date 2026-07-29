from __future__ import annotations

import pytest

from questpilot.goal_parser import (
    NaturalLanguageGoalParser,
    build_character_resolution_registry,
    build_goal_proposal_registry,
)
from questpilot.harness.context import ExecutionContext
from questpilot.harness.events import InMemoryEventSink
from questpilot.harness.gateway import FakeModel, ModelResponse, ModelToolCall
from questpilot.repositories import GameRepository
from questpilot.services import GameService


@pytest.mark.asyncio
async def test_fake_model_parses_multiple_goals_and_preserves_ambiguity(seeded_session):
    service = GameService(GameRepository(seeded_session))
    model = FakeModel(
        [
            ModelResponse(
                tool_calls=[
                    ModelToolCall(
                        id="proposal-1",
                        name="propose_training_goals",
                        arguments={
                            "goals": [
                                {
                                    "character_query": "蓝呆",
                                    "skill_number": 1,
                                    "current_level": 8,
                                    "target_level": 9,
                                },
                                {
                                    "character_query": "玛修",
                                    "skill_number": 2,
                                    "current_level": 3,
                                    "target_level": 6,
                                },
                            ]
                        },
                    )
                ]
            )
        ]
    )
    sink = InMemoryEventSink()
    context = ExecutionContext(event_sink=sink)
    result = await NaturalLanguageGoalParser(
        model,
        build_goal_proposal_registry(),
        build_character_resolution_registry(service),
    ).run("蓝呆一技能8到9，玛修二技能3到6", context)

    assert len(result.resolved_goals) == 2
    assert not result.candidate_groups
    assert [step["name"] for step in result.tool_steps] == [
        "propose_training_goals",
        "search_character",
        "search_character",
    ]
    assert result.event_count == len(sink.events_for(context.run_id))


@pytest.mark.asyncio
async def test_fake_model_requires_selection_for_low_confidence_candidate(seeded_session):
    service = GameService(GameRepository(seeded_session))
    model = FakeModel(
        [
            ModelResponse(
                tool_calls=[
                    ModelToolCall(
                        id="proposal-2",
                        name="propose_training_goals",
                        arguments={
                            "goals": [
                                {
                                    "character_query": "阿尔托莉亚",
                                    "skill_number": 1,
                                    "current_level": 1,
                                    "target_level": 6,
                                }
                            ]
                        },
                    )
                ]
            )
        ]
    )
    result = await NaturalLanguageGoalParser(
        model,
        build_goal_proposal_registry(),
        build_character_resolution_registry(service),
    ).run("阿尔托莉亚一技能1到6", ExecutionContext())
    assert not result.resolved_goals
    assert len(result.candidate_groups) == 1
    assert result.candidate_groups[0].candidates
    assert all(
        candidate.requires_selection
        for candidate in result.candidate_groups[0].candidates
    )
