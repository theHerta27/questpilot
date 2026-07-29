from __future__ import annotations

import pytest
from pydantic import BaseModel, Field, ValidationError

from questpilot.agent_runtime import AgentRuntime
from questpilot.domain_tools import build_tool_registry
from questpilot.harness.context import ExecutionContext
from questpilot.harness.events import InMemoryEventSink
from questpilot.harness.gateway import FakeModel, ModelResponse, ModelToolCall
from questpilot.harness.tools import RetryPolicy, ToolRegistry, ToolSpec
from questpilot.repositories import GameRepository
from questpilot.services import GameService


class NumberInput(BaseModel):
    value: int = Field(ge=0)


class NumberOutput(BaseModel):
    value: int


@pytest.mark.asyncio
async def test_fake_model_drives_complete_tool_call(seeded_session):
    character = GameRepository(seeded_session).search_characters("蓝呆")[0]
    gateway = FakeModel(
        [
            ModelResponse(
                tool_calls=[
                    ModelToolCall(
                        id="call-1",
                        name="get_skill_materials",
                        arguments={"character_id": character.id},
                    )
                ],
                model="fake",
            ),
            ModelResponse(text="已查询技能材料。", model="fake"),
        ]
    )
    sink = InMemoryEventSink()
    context = ExecutionContext(event_sink=sink)
    runtime = AgentRuntime(
        gateway,
        build_tool_registry(GameService(GameRepository(seeded_session))),
    )
    result = await runtime.run("查询蓝呆技能材料", context)
    assert result.answer == "已查询技能材料。"
    assert result.tool_results[0]["name"] == "get_skill_materials"
    events = sink.events_for(context.run_id)
    assert [event.sequence for event in events] == list(range(1, len(events) + 1))
    assert "tool.started" in [event.event_type for event in events]
    assert "tool.completed" in [event.event_type for event in events]


def test_registry_rejects_duplicates_and_invalid_input():
    registry = ToolRegistry()
    spec = ToolSpec(
        name="double",
        description="Double a number",
        input_model=NumberInput,
        output_model=NumberOutput,
    )
    registry.register(spec, lambda payload, _: NumberOutput(value=payload.value * 2))
    with pytest.raises(ValueError):
        registry.register(spec, lambda payload, _: payload)
    with pytest.raises(ValidationError):
        NumberInput(value=-1)
    with pytest.raises(KeyError):
        registry.get("missing")


@pytest.mark.asyncio
async def test_retry_only_runs_for_idempotent_tool():
    attempts = {"count": 0}

    async def flaky(payload, _):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("temporary")
        return NumberOutput(value=payload.value)

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="flaky",
            description="A retryable test tool",
            input_model=NumberInput,
            output_model=NumberOutput,
            idempotent=True,
            retry_policy=RetryPolicy(max_attempts=2),
        ),
        flaky,
    )
    result = await registry.execute("flaky", {"value": 3}, ExecutionContext())
    assert result.value == 3
    assert attempts["count"] == 2

    attempts["count"] = 0
    registry.register(
        ToolSpec(
            name="write_once",
            description="A non-idempotent test tool",
            input_model=NumberInput,
            output_model=NumberOutput,
            read_only=False,
            idempotent=False,
            retry_policy=RetryPolicy(max_attempts=3),
        ),
        flaky,
    )
    with pytest.raises(RuntimeError):
        await registry.execute("write_once", {"value": 3}, ExecutionContext())
    assert attempts["count"] == 1
