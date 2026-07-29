from __future__ import annotations

import asyncio
import inspect
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from questpilot.harness.context import ExecutionContext
from questpilot.harness.policy import ExecutionBudget


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=1, ge=1, le=5)
    backoff_seconds: float = Field(default=0, ge=0, le=30)


ToolHandler = Callable[[BaseModel, ExecutionContext], BaseModel | Awaitable[BaseModel]]


class ToolSpec(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    version: str = "1.0.0"
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    read_only: bool = True
    idempotent: bool = True
    timeout_seconds: float = Field(default=15, gt=0, le=300)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    confirmation_policy: Literal["never", "always", "write"] = "never"

    model_config = {"arbitrary_types_allowed": True}

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema(),
            },
        }


@dataclass
class RegisteredTool:
    spec: ToolSpec
    handler: ToolHandler


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[tuple[str, str], RegisteredTool] = {}
        self._latest: dict[str, str] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        key = (spec.name, spec.version)
        if key in self._tools:
            raise ValueError(f"tool already registered: {spec.name}@{spec.version}")
        self._tools[key] = RegisteredTool(spec=spec, handler=handler)
        self._latest[spec.name] = spec.version

    def get(self, name: str, version: str | None = None) -> RegisteredTool:
        resolved = version or self._latest.get(name)
        if resolved is None or (name, resolved) not in self._tools:
            raise KeyError(f"unknown tool: {name}{'@' + version if version else ''}")
        return self._tools[(name, resolved)]

    def list(self) -> list[ToolSpec]:
        return [tool.spec for tool in self._tools.values()]

    def model_schemas(self) -> list[dict[str, Any]]:
        return [self.get(name).spec.openai_schema() for name in sorted(self._latest)]

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any] | BaseModel,
        context: ExecutionContext,
        *,
        version: str | None = None,
    ) -> BaseModel:
        tool = self.get(name, version)
        payload = (
            arguments
            if isinstance(arguments, tool.spec.input_model)
            else tool.spec.input_model.model_validate(arguments)
        )
        budget = context.metadata.get("budget")
        if isinstance(budget, ExecutionBudget):
            signature = f"{name}:{json.dumps(payload.model_dump(mode='json'), sort_keys=True)}"
            budget.before_tool(signature, context.elapsed_seconds)
        context.emit(
            "tool.started",
            name,
            "started",
            payload_summary={"version": tool.spec.version, "arguments": payload.model_dump()},
        )
        attempts = tool.spec.retry_policy.max_attempts if tool.spec.idempotent else 1
        try:
            validated = None
            for attempt in range(1, attempts + 1):
                try:
                    if inspect.iscoroutinefunction(tool.handler):
                        result = await asyncio.wait_for(
                            tool.handler(payload, context), timeout=tool.spec.timeout_seconds
                        )
                    else:
                        result = await asyncio.wait_for(
                            asyncio.to_thread(tool.handler, payload, context),
                            timeout=tool.spec.timeout_seconds,
                        )
                    validated = tool.spec.output_model.model_validate(result)
                    break
                except Exception:
                    if attempt >= attempts:
                        raise
                    context.emit(
                        "tool.retrying",
                        name,
                        "retrying",
                        payload_summary={"attempt": attempt + 1, "max_attempts": attempts},
                    )
                    if tool.spec.retry_policy.backoff_seconds:
                        await asyncio.sleep(tool.spec.retry_policy.backoff_seconds)
            assert validated is not None
        except Exception as exc:
            context.emit(
                "tool.failed",
                name,
                "failed",
                error={"type": type(exc).__name__, "message": str(exc)},
                finished=True,
            )
            raise
        context.emit(
            "tool.completed",
            name,
            "completed",
            payload_summary={"result": validated.model_dump(mode="json")},
            finished=True,
        )
        return validated
