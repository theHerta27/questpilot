from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel

from questpilot.harness.context import ExecutionContext
from questpilot.harness.events import InMemoryEventSink
from questpilot.harness.persistence import CheckpointStore
from questpilot.harness.policy import (
    BudgetExceeded,
    ExecutionBudget,
    ExecutionPolicy,
    LoopDetected,
)
from questpilot.harness.tools import ToolRegistry, ToolSpec


class Empty(BaseModel):
    pass


def test_budget_and_loop_limits_are_enforced():
    budget = ExecutionBudget(
        ExecutionPolicy(
            max_model_calls=1,
            max_identical_tool_calls=1,
            max_steps=10,
        )
    )
    budget.before_model(0)
    with pytest.raises(BudgetExceeded):
        budget.before_model(0)
    fresh = ExecutionBudget(
        ExecutionPolicy(max_identical_tool_calls=1, max_steps=10)
    )
    fresh.before_tool("same:{}", 0)
    with pytest.raises(LoopDetected):
        fresh.before_tool("same:{}", 0)


@pytest.mark.asyncio
async def test_tool_timeout_emits_clear_failure_event():
    async def slow(_, __):
        await asyncio.sleep(0.05)
        return Empty()

    registry = ToolRegistry()
    registry.register(
        ToolSpec(
            name="slow",
            description="A deliberately slow tool",
            input_model=Empty,
            output_model=Empty,
            timeout_seconds=0.01,
        ),
        slow,
    )
    sink = InMemoryEventSink()
    context = ExecutionContext(event_sink=sink)
    with pytest.raises(TimeoutError):
        await registry.execute("slow", {}, context)
    assert sink.events_for(context.run_id)[-1].event_type == "tool.failed"


def test_checkpoint_latest_supports_recovery(session):
    store = CheckpointStore(session)
    store.save("run", "node", {"value": 1})
    store.save("run", "node", {"value": 2})
    latest = store.latest("run", "node")
    assert latest is not None
    assert latest.version == 2
    assert latest.state_json == {"value": 2}
