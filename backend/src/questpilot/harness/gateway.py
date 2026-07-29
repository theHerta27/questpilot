from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import AsyncIterator
from typing import Any

import httpx
from pydantic import BaseModel, Field

from questpilot.harness.context import ExecutionContext


class ModelMessage(BaseModel):
    role: str
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ModelToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class ModelRequest(BaseModel):
    messages: list[ModelMessage]
    tools: list[dict[str, Any]] = Field(default_factory=list)
    model: str | None = None
    temperature: float = 0


class ModelResponse(BaseModel):
    text: str = ""
    tool_calls: list[ModelToolCall] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)
    model: str = "unknown"
    raw: dict[str, Any] = Field(default_factory=dict)


class ModelChunk(BaseModel):
    text: str
    done: bool = False


class ModelGateway(ABC):
    @abstractmethod
    async def invoke(self, request: ModelRequest, context: ExecutionContext) -> ModelResponse:
        raise NotImplementedError

    async def stream(
        self, request: ModelRequest, context: ExecutionContext
    ) -> AsyncIterator[ModelChunk]:
        response = await self.invoke(request, context)
        yield ModelChunk(text=response.text, done=True)


class FakeModel(ModelGateway):
    def __init__(self, responses: list[ModelResponse | dict[str, Any]] | None = None) -> None:
        self.responses = deque(
            response
            if isinstance(response, ModelResponse)
            else ModelResponse.model_validate(response)
            for response in (responses or [])
        )
        self.requests: list[ModelRequest] = []

    def queue(self, *responses: ModelResponse | dict[str, Any]) -> None:
        for response in responses:
            self.responses.append(
                response
                if isinstance(response, ModelResponse)
                else ModelResponse.model_validate(response)
            )

    async def invoke(self, request: ModelRequest, context: ExecutionContext) -> ModelResponse:
        self.requests.append(request)
        context.emit(
            "model.requested",
            "FakeModel",
            "started",
            payload_summary={
                "message_count": len(request.messages),
                "tool_count": len(request.tools),
            },
        )
        if not self.responses:
            response = ModelResponse(
                text="FakeModel 没有预设响应。请配置真实模型或在测试中加入响应队列。",
                model="fake",
            )
        else:
            response = self.responses.popleft()
        context.emit(
            "model.completed",
            "FakeModel",
            "completed",
            payload_summary={
                "text_length": len(response.text),
                "tool_calls": [call.name for call in response.tool_calls],
            },
            usage=response.usage,
            finished=True,
        )
        return response


class OpenAICompatibleGateway(ModelGateway):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 60,
        thinking_enabled: bool | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.thinking_enabled = thinking_enabled

    def build_payload(self, request: ModelRequest) -> dict[str, Any]:
        model_name = request.model or self.model
        payload: dict[str, Any] = {
            "model": model_name,
            "messages": [message.model_dump(exclude_none=True) for message in request.messages],
            "temperature": request.temperature,
        }
        if self.thinking_enabled is not None:
            payload["thinking"] = {
                "type": "enabled" if self.thinking_enabled else "disabled"
            }
        if request.tools:
            payload["tools"] = request.tools
        return payload

    async def invoke(self, request: ModelRequest, context: ExecutionContext) -> ModelResponse:
        model_name = request.model or self.model
        context.emit(
            "model.requested",
            model_name,
            "started",
            payload_summary={
                "message_count": len(request.messages),
                "tool_count": len(request.tools),
            },
        )
        payload = self.build_payload(request)
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", headers=headers, json=payload
                )
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            context.emit(
                "model.failed",
                model_name,
                "failed",
                error={"type": type(exc).__name__, "message": str(exc)},
                finished=True,
            )
            raise
        choice = data["choices"][0]["message"]
        calls: list[ModelToolCall] = []
        for call in choice.get("tool_calls") or []:
            arguments = call["function"].get("arguments") or "{}"
            calls.append(
                ModelToolCall(
                    id=call["id"],
                    name=call["function"]["name"],
                    arguments=json.loads(arguments) if isinstance(arguments, str) else arguments,
                )
            )
        result = ModelResponse(
            text=choice.get("content") or "",
            tool_calls=calls,
            usage=data.get("usage") or {},
            model=data.get("model") or model_name,
            raw=data,
        )
        context.emit(
            "model.completed",
            result.model,
            "completed",
            payload_summary={"tool_calls": [call.name for call in calls]},
            usage=result.usage,
            finished=True,
        )
        return result


class FallbackGateway(ModelGateway):
    def __init__(self, gateways: list[ModelGateway]) -> None:
        if not gateways:
            raise ValueError("at least one gateway is required")
        self.gateways = gateways

    async def invoke(self, request: ModelRequest, context: ExecutionContext) -> ModelResponse:
        errors: list[str] = []
        for index, gateway in enumerate(self.gateways):
            try:
                return await gateway.invoke(request, context)
            except Exception as exc:
                errors.append(f"{type(gateway).__name__}: {exc}")
                context.emit(
                    "model.fallback",
                    type(gateway).__name__,
                    "failed",
                    payload_summary={"next_gateway": index + 1},
                    error={"message": str(exc)},
                    finished=True,
                )
        raise RuntimeError("all model gateways failed: " + " | ".join(errors))
