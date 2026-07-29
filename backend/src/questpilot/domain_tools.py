from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from questpilot.harness import ExecutionContext, ToolRegistry, ToolSpec
from questpilot.schemas import (
    CharacterSummary,
    MaterialGapRequest,
    MaterialGapResult,
    SkillCostItem,
)
from questpilot.services import GameService


class CharacterSearchInput(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=30)


class CharacterSearchOutput(BaseModel):
    characters: list[CharacterSummary]


class SkillMaterialsInput(BaseModel):
    character_id: int


class SkillMaterialsOutput(BaseModel):
    costs: list[SkillCostItem]


def build_tool_registry(service: GameService) -> ToolRegistry:
    registry = ToolRegistry()

    def search_character(
        payload: CharacterSearchInput, _: ExecutionContext
    ) -> CharacterSearchOutput:
        return CharacterSearchOutput(
            characters=service.search_characters(payload.query, payload.limit)
        )

    def get_skill_materials(
        payload: SkillMaterialsInput, _: ExecutionContext
    ) -> SkillMaterialsOutput:
        return SkillMaterialsOutput(costs=service.skill_costs(payload.character_id))

    def calculate_material_gap(
        payload: MaterialGapRequest, _: ExecutionContext
    ) -> MaterialGapResult:
        return service.material_gap(payload)

    registry.register(
        ToolSpec(
            name="search_character",
            description="按中文名、日文名或别名查询角色。",
            input_model=CharacterSearchInput,
            output_model=CharacterSearchOutput,
        ),
        search_character,
    )
    registry.register(
        ToolSpec(
            name="get_skill_materials",
            description="查询指定角色三个技能从 1 到 10 级的逐级材料消耗。",
            input_model=SkillMaterialsInput,
            output_model=SkillMaterialsOutput,
        ),
        get_skill_materials,
    )
    registry.register(
        ToolSpec(
            name="calculate_material_gap",
            description="根据目标技能等级和用户库存确定性计算材料缺口。",
            input_model=MaterialGapRequest,
            output_model=MaterialGapResult,
        ),
        calculate_material_gap,
    )
    return registry


def tool_result_message(name: str, result: BaseModel) -> dict[str, Any]:
    return {"tool": name, "result": result.model_dump(mode="json")}

