from __future__ import annotations

from questpilot.repositories import GameRepository
from questpilot.schemas import (
    CharacterSummary,
    InventoryItemView,
    InventoryReplaceRequest,
    MaterialGapItem,
    MaterialGapRequest,
    MaterialGapResult,
    SkillCostItem,
)


class GameService:
    def __init__(self, repository: GameRepository) -> None:
        self.repository = repository

    def search_characters(self, query: str, limit: int = 20) -> list[CharacterSummary]:
        return [
            CharacterSummary(
                id=row.id,
                game_id=row.game_id,
                collection_no=row.collection_no,
                name_zh_cn=row.name_zh_cn,
                name_ja=row.name_ja,
                rarity=row.rarity,
                class_name=row.class_name,
                aliases=sorted({alias.alias for alias in row.aliases}),
            )
            for row in self.repository.search_characters(query, limit)
        ]

    def skill_costs(self, character_id: int) -> list[SkillCostItem]:
        return [
            SkillCostItem(
                skill_number=row.skill_number,
                from_level=row.from_level,
                to_level=row.to_level,
                material_id=row.material_id,
                material_name=row.material.name,
                amount=row.amount,
            )
            for row in self.repository.skill_costs(character_id)
        ]

    def inventory(self, user_id: str) -> list[InventoryItemView]:
        return [
            InventoryItemView(
                material_id=row.material_id,
                material_name=row.material.name,
                quantity=row.quantity,
            )
            for row in self.repository.inventory(user_id).values()
        ]

    def update_inventory(self, request: InventoryReplaceRequest) -> list[InventoryItemView]:
        data = {item.material_id: item.quantity for item in request.items}
        if request.mode == "replace":
            self.repository.replace_inventory(request.user_id, data)
        else:
            self.repository.increment_inventory(request.user_id, data)
        return self.inventory(request.user_id)

    def material_gap(self, request: MaterialGapRequest) -> MaterialGapResult:
        goals = [
            (
                goal.character_id,
                goal.skill_number,
                goal.current_level,
                goal.target_level,
            )
            for goal in request.goals
        ]
        requirements = self.repository.aggregate_requirements(goals)
        inventory = self.repository.inventory(request.user_id)
        items = []
        for material_id, (name, required) in sorted(
            requirements.items(), key=lambda pair: pair[1][0]
        ):
            owned = inventory.get(material_id).quantity if material_id in inventory else 0
            items.append(
                MaterialGapItem(
                    material_id=material_id,
                    material_name=name,
                    required=required,
                    owned=owned,
                    gap=max(required - owned, 0),
                )
            )
        return MaterialGapResult(
            user_id=request.user_id,
            goals=request.goals,
            items=items,
            verification_notes=["需求由技能等级消耗逐级汇总", "缺口使用 max(需求-库存, 0) 计算"],
        )

