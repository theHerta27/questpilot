from __future__ import annotations

from questpilot.domain_tools import CharacterSearchInput, CharacterSearchOutput
from questpilot.harness.context import ExecutionContext
from questpilot.harness.gateway import ModelGateway, ModelMessage, ModelRequest
from questpilot.harness.tools import ToolRegistry, ToolSpec
from questpilot.schemas import (
    GoalCandidateGroup,
    GoalParseResponse,
    ResolvedTrainingGoal,
    TrainingGoalProposal,
)
from questpilot.services import GameService

GOAL_PARSE_PROMPT = """你是 QuestPilot 的培养目标解析器。
把用户输入中的一个或多个培养目标提取为 propose_training_goals 工具参数。
每个目标必须包含角色名称或别名、技能编号、当前等级、目标等级。
技能“一/二/三”分别转为 1/2/3。等级必须满足 1<=当前<=目标<=10。
不要计算材料、掉落率、AP 或路线；必须调用工具，不要只输出文字。"""


def build_goal_proposal_registry() -> ToolRegistry:
    registry = ToolRegistry()

    def propose(
        payload: TrainingGoalProposal, _: ExecutionContext
    ) -> TrainingGoalProposal:
        return payload

    registry.register(
        ToolSpec(
            name="propose_training_goals",
            description="提交从自然语言中提取的一个或多个培养目标。",
            input_model=TrainingGoalProposal,
            output_model=TrainingGoalProposal,
            read_only=True,
            idempotent=True,
        ),
        propose,
    )
    return registry


def build_character_resolution_registry(service: GameService) -> ToolRegistry:
    registry = ToolRegistry()

    def search(
        payload: CharacterSearchInput, _: ExecutionContext
    ) -> CharacterSearchOutput:
        return CharacterSearchOutput(
            characters=service.search_characters(payload.query, payload.limit)
        )

    registry.register(
        ToolSpec(
            name="search_character",
            description="按名称或别名解析角色；模糊和同名结果必须由用户选择。",
            input_model=CharacterSearchInput,
            output_model=CharacterSearchOutput,
            read_only=True,
            idempotent=True,
        ),
        search,
    )
    return registry


class NaturalLanguageGoalParser:
    def __init__(
        self,
        gateway: ModelGateway,
        proposal_registry: ToolRegistry,
        resolution_registry: ToolRegistry,
    ) -> None:
        self.gateway = gateway
        self.proposal_registry = proposal_registry
        self.resolution_registry = resolution_registry

    async def run(self, query: str, context: ExecutionContext) -> GoalParseResponse:
        context.emit(
            "run.started",
            "NaturalLanguageGoalParser",
            "started",
            payload_summary={"query": query[:200]},
        )
        response = await self.gateway.invoke(
            ModelRequest(
                messages=[
                    ModelMessage(role="system", content=GOAL_PARSE_PROMPT),
                    ModelMessage(role="user", content=query),
                ],
                tools=self.proposal_registry.model_schemas(),
            ),
            context,
        )
        proposal_call = next(
            (
                call
                for call in response.tool_calls
                if call.name == "propose_training_goals"
            ),
            None,
        )
        if not proposal_call:
            raise ValueError("model did not return propose_training_goals")
        proposal = await self.proposal_registry.execute(
            proposal_call.name,
            proposal_call.arguments,
            context,
        )
        if not isinstance(proposal, TrainingGoalProposal):
            raise TypeError("goal proposal tool returned an unexpected schema")
        tool_steps: list[dict[str, object]] = [
            {
                "name": "propose_training_goals",
                "status": "completed",
                "summary": f"解析 {len(proposal.goals)} 个目标",
            }
        ]
        resolved: list[ResolvedTrainingGoal] = []
        candidate_groups: list[GoalCandidateGroup] = []
        for index, draft in enumerate(proposal.goals):
            result = await self.resolution_registry.execute(
                "search_character",
                {"query": draft.character_query, "limit": 10},
                context,
            )
            if not isinstance(result, CharacterSearchOutput):
                raise TypeError("character search returned an unexpected schema")
            tool_steps.append(
                {
                    "name": "search_character",
                    "status": "requires_selection"
                    if not result.characters
                    or any(character.requires_selection for character in result.characters)
                    else "completed",
                    "summary": (
                        f"{draft.character_query}：{len(result.characters)} 个候选"
                    ),
                }
            )
            if (
                len(result.characters) == 1
                and not result.characters[0].requires_selection
            ):
                character = result.characters[0]
                resolved.append(
                    ResolvedTrainingGoal(
                        character=character,
                        character_id=character.id,
                        skill_number=draft.skill_number,
                        current_level=draft.current_level,
                        target_level=draft.target_level,
                    )
                )
            else:
                candidate_groups.append(
                    GoalCandidateGroup(
                        draft_index=index,
                        character_query=draft.character_query,
                        skill_number=draft.skill_number,
                        current_level=draft.current_level,
                        target_level=draft.target_level,
                        candidates=result.characters,
                    )
                )
        explanation = (
            f"模型解析了 {len(proposal.goals)} 个培养目标；"
            f"{len(resolved)} 个已精确解析，"
            f"{len(candidate_groups)} 个需要你选择角色。"
        )
        context.emit(
            "verification.completed",
            "goal_entity_resolution",
            "requires_selection" if candidate_groups else "completed",
            payload_summary={
                "draft_count": len(proposal.goals),
                "resolved_count": len(resolved),
                "candidate_group_count": len(candidate_groups),
            },
            finished=True,
        )
        context.emit(
            "run.completed",
            "NaturalLanguageGoalParser",
            "completed",
            payload_summary={
                "resolved_count": len(resolved),
                "requires_selection": bool(candidate_groups),
            },
            finished=True,
        )
        return GoalParseResponse(
            run_id=context.run_id,
            drafts=proposal.goals,
            resolved_goals=resolved,
            candidate_groups=candidate_groups,
            tool_steps=tool_steps,
            explanation=explanation,
            event_count=len(context.event_sink.events_for(context.run_id)),
        )
