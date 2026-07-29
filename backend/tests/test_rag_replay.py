from __future__ import annotations

import pytest

from questpilot.domain_tools import build_tool_registry
from questpilot.harness.gateway import ModelResponse, ModelToolCall
from questpilot.models import AgentRun
from questpilot.rag import MooncellIndex
from questpilot.replay import PromptRegistry, ReplayService
from questpilot.repositories import GameRepository
from questpilot.services import GameService


def test_rag_answer_contains_traceable_citation(seeded_session):
    answer = MooncellIndex(seeded_session).answer("技能强化")
    assert answer.citations
    assert answer.citations[0].source_url.startswith("https://")
    assert answer.citations[0].heading


def test_prompt_versions_are_immutable(seeded_session):
    registry = PromptRegistry(seeded_session)
    registry.register("test.prompt", "1.0.0", "node", "alpha")
    try:
        registry.register("test.prompt", "1.0.0", "node", "beta")
    except ValueError:
        pass
    else:
        raise AssertionError("released prompt content must be immutable")


def test_replay_classifies_model_and_input_drift(seeded_session):
    run = AgentRun(
        id="run-1",
        request_id="request-1",
        trace_id="trace-1",
        input_json={"query": "A"},
        output_json={"answer": "A"},
        model_name="fake",
        prompt_id="agent.system",
        prompt_version="1.0.0",
    )
    seeded_session.add(run)
    seeded_session.commit()
    replay = ReplayService(seeded_session)
    original = replay.bundle("run-1")
    changed = {**original, "input": {"query": "B"}, "model": "other"}
    report = replay.compare(original, changed)
    assert report.input_drift
    assert report.model_drift
    assert not report.prompt_drift


@pytest.mark.asyncio
async def test_fake_replay_is_deterministic(seeded_session):
    repository = GameRepository(seeded_session)
    character = repository.search_characters("蓝呆")[0]
    service = GameService(repository)
    recorded = service.search_characters("蓝呆", 10)
    run = AgentRun(
        id="replay-run",
        request_id="request-2",
        trace_id="trace-2",
        input_json={"query": "找蓝呆", "user_id": "demo"},
        output_json={
            "answer": "找到。",
            "tool_results": [
                {
                    "id": "call-1",
                    "name": "search_character",
                    "result": {
                        "characters": [item.model_dump(mode="json") for item in recorded]
                    },
                }
            ],
        },
        model_name="fake",
    )
    seeded_session.add(run)
    seeded_session.commit()
    script = [
        ModelResponse(
            tool_calls=[
                ModelToolCall(
                    id="call-1",
                    name="search_character",
                    arguments={"query": "蓝呆", "limit": 10},
                )
            ],
            model="fake",
        ),
        ModelResponse(text="找到。", model="fake"),
    ]
    replay = ReplayService(seeded_session)
    registry = build_tool_registry(service)
    first = await replay.replay_fake("replay-run", script, registry)
    second = await replay.replay_fake("replay-run", script, registry)
    assert first.answer == second.answer == "找到。"
    assert first.tool_results == second.tool_results
    assert first.tool_results[0]["result"]["characters"][0]["id"] == character.id
