from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


class BudgetExceeded(RuntimeError):
    pass


class LoopDetected(RuntimeError):
    pass


class ExecutionPolicy(BaseModel):
    max_model_calls: int = Field(default=12, ge=1)
    max_tool_calls: int = Field(default=24, ge=1)
    max_tokens: int = Field(default=20_000, ge=1)
    max_runtime_seconds: float = Field(default=120, gt=0)
    max_steps: int = Field(default=40, ge=1)
    max_identical_tool_calls: int = Field(default=2, ge=1)
    max_node_visits: int = Field(default=4, ge=1)


@dataclass
class ExecutionBudget:
    policy: ExecutionPolicy
    model_calls: int = 0
    tool_calls: int = 0
    tokens: int = 0
    steps: int = 0
    node_visits: Counter[str] = field(default_factory=Counter)
    tool_signatures: Counter[str] = field(default_factory=Counter)

    def _check_runtime(self, elapsed_seconds: float) -> None:
        if elapsed_seconds > self.policy.max_runtime_seconds:
            raise BudgetExceeded(
                f"runtime budget exceeded: {elapsed_seconds:.2f}s > "
                f"{self.policy.max_runtime_seconds:.2f}s"
            )

    def before_model(self, elapsed_seconds: float) -> None:
        self._check_runtime(elapsed_seconds)
        self.model_calls += 1
        self.step()
        if self.model_calls > self.policy.max_model_calls:
            raise BudgetExceeded("model call budget exceeded")

    def after_model(self, usage: dict[str, Any]) -> None:
        consumed = int(usage.get("total_tokens") or 0)
        self.tokens += consumed
        if self.tokens > self.policy.max_tokens:
            raise BudgetExceeded("token budget exceeded")

    def before_tool(self, signature: str, elapsed_seconds: float) -> None:
        self._check_runtime(elapsed_seconds)
        self.tool_calls += 1
        self.step()
        if self.tool_calls > self.policy.max_tool_calls:
            raise BudgetExceeded("tool call budget exceeded")
        self.tool_signatures[signature] += 1
        if self.tool_signatures[signature] > self.policy.max_identical_tool_calls:
            raise LoopDetected(f"repeated tool call detected: {signature}")

    def visit_node(self, node_name: str, elapsed_seconds: float) -> None:
        self._check_runtime(elapsed_seconds)
        self.node_visits[node_name] += 1
        self.step()
        if self.node_visits[node_name] > self.policy.max_node_visits:
            raise LoopDetected(f"node visit limit exceeded: {node_name}")

    def step(self) -> None:
        self.steps += 1
        if self.steps > self.policy.max_steps:
            raise BudgetExceeded("total step budget exceeded")

    def snapshot(self) -> dict[str, Any]:
        return {
            "model_calls": self.model_calls,
            "tool_calls": self.tool_calls,
            "tokens": self.tokens,
            "steps": self.steps,
            "node_visits": dict(self.node_visits),
        }


class ContextBuilder:
    """Build a bounded model context from deterministic state."""

    def __init__(self, *, max_history_items: int = 6, max_tool_results: int = 6) -> None:
        self.max_history_items = max_history_items
        self.max_tool_results = max_tool_results

    def build(
        self,
        *,
        goal: dict[str, Any],
        account_snapshot: dict[str, Any],
        history: list[dict[str, Any]] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "goal": goal,
            "account_snapshot": account_snapshot,
            "history": (history or [])[-self.max_history_items :],
            "tool_results": (tool_results or [])[-self.max_tool_results :],
        }
