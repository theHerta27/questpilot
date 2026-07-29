from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from questpilot.harness.context import ExecutionContext
from questpilot.harness.gateway import ModelGateway, ModelMessage, ModelRequest
from questpilot.harness.policy import BudgetExceeded, ExecutionBudget, ExecutionPolicy, LoopDetected
from questpilot.harness.tools import ToolRegistry
from questpilot.schemas import AgentQueryResponse

SYSTEM_PROMPT = """你是 QuestPilot。精确游戏事实与材料数量必须通过工具获取。
禁止口算或猜测材料数量。角色必须先通过 search_character 解析，再使用返回的内部 ID。
查询结果要求用户选择时，不得自行挑选角色。材料需求使用 get_skill_materials；
包含库存或“缺口”的请求使用 calculate_material_gap。最终用简洁中文解释工具结果。"""


class AgentRuntime:
    def __init__(
        self,
        gateway: ModelGateway,
        registry: ToolRegistry,
        *,
        max_rounds: int = 6,
    ) -> None:
        self.gateway = gateway
        self.registry = registry
        self.max_rounds = max_rounds

    async def run(self, query: str, context: ExecutionContext) -> AgentQueryResponse:
        context.emit(
            "run.started",
            "AgentRuntime",
            "started",
            payload_summary={"query": query[:200]},
        )
        messages = [
            ModelMessage(role="system", content=SYSTEM_PROMPT),
            ModelMessage(role="user", content=query),
        ]
        tool_results: list[dict[str, Any]] = []
        seen_calls: set[str] = set()
        budget = context.metadata.setdefault(
            "budget", ExecutionBudget(context.policy or ExecutionPolicy())
        )
        try:
            for _ in range(self.max_rounds):
                budget.before_model(context.elapsed_seconds)
                response = await self.gateway.invoke(
                    ModelRequest(messages=messages, tools=self.registry.model_schemas()),
                    context,
                )
                budget.after_model(response.usage)
                if not response.tool_calls:
                    context.emit(
                        "run.completed",
                        "AgentRuntime",
                        "completed",
                        payload_summary={
                            "tool_result_count": len(tool_results),
                            "budget": budget.snapshot(),
                        },
                        finished=True,
                    )
                    return AgentQueryResponse(
                        run_id=context.run_id,
                        answer=response.text,
                        tool_results=tool_results,
                        event_count=len(context.event_sink.events_for(context.run_id)),
                    )
                messages.append(
                    ModelMessage(
                        role="assistant",
                        content=response.text or None,
                        tool_calls=[
                            {
                                "id": call.id,
                                "type": "function",
                                "function": {
                                    "name": call.name,
                                    "arguments": json.dumps(
                                        call.arguments, ensure_ascii=False
                                    ),
                                },
                            }
                            for call in response.tool_calls
                        ],
                    )
                )
                for call in response.tool_calls:
                    signature = f"{call.name}:{json.dumps(call.arguments, sort_keys=True)}"
                    if signature in seen_calls:
                        raise LoopDetected(f"repeated tool call detected: {call.name}")
                    seen_calls.add(signature)
                    result = await self.registry.execute(call.name, call.arguments, context)
                    item = {
                        "id": call.id or str(uuid4()),
                        "name": call.name,
                        "result": result.model_dump(mode="json"),
                    }
                    tool_results.append(item)
                    messages.append(
                        ModelMessage(
                            role="tool",
                            name=call.name,
                            tool_call_id=call.id,
                            content=json.dumps(item["result"], ensure_ascii=False),
                        )
                    )
                    if call.name == "search_character":
                        candidates = item["result"].get("characters") or []
                        if any(candidate.get("requires_selection") for candidate in candidates):
                            choices = "；".join(
                                (
                                    f"{candidate['name_zh_cn']} "
                                    f"({candidate['class_name']}, "
                                    f"No.{candidate['collection_no']})"
                                )
                                for candidate in candidates
                            )
                            answer = (
                                f"找到需要确认的角色候选：{choices}。"
                                "请明确选择后，我再查询材料或计算缺口。"
                            )
                            context.emit(
                                "verification.completed",
                                "entity_resolution",
                                "requires_selection",
                                payload_summary={
                                    "candidate_count": len(candidates),
                                    "collection_numbers": [
                                        candidate["collection_no"]
                                        for candidate in candidates
                                    ],
                                },
                                finished=True,
                            )
                            context.emit(
                                "run.completed",
                                "AgentRuntime",
                                "completed",
                                payload_summary={
                                    "tool_result_count": len(tool_results),
                                    "requires_selection": True,
                                    "budget": budget.snapshot(),
                                },
                                finished=True,
                            )
                            return AgentQueryResponse(
                                run_id=context.run_id,
                                answer=answer,
                                tool_results=tool_results,
                                event_count=len(
                                    context.event_sink.events_for(context.run_id)
                                ),
                            )
        except (BudgetExceeded, LoopDetected) as exc:
            context.emit(
                "run.failed",
                "AgentRuntime",
                "failed",
                error={"type": type(exc).__name__, "message": str(exc)},
                payload_summary={"budget": budget.snapshot()},
                finished=True,
            )
            raise
        context.emit(
            "run.failed",
            "AgentRuntime",
            "failed",
            error={"type": "RoundLimit", "message": str(self.max_rounds)},
            finished=True,
        )
        raise RuntimeError("agent round limit reached")
