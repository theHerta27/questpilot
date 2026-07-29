from __future__ import annotations

from questpilot.repositories import GameRepository
from questpilot.schemas import (
    CharacterSummary,
    DataSourceStatus,
    InventoryItemView,
    InventoryReplaceRequest,
    MaterialGapItem,
    MaterialGapRequest,
    MaterialGapResult,
    SkillCostItem,
    SkillGoal,
)


class GameService:
    def __init__(self, repository: GameRepository) -> None:
        self.repository = repository

    def search_characters(self, query: str, limit: int = 20) -> list[CharacterSummary]:
        matches = self.repository.search_character_matches(query, limit)
        multiple_candidates = len(matches) > 1
        return [
            CharacterSummary(
                id=match.character.id,
                game_id=match.character.game_id,
                collection_no=match.character.collection_no,
                name_zh_cn=match.character.name_zh_cn,
                name_ja=match.character.name_ja,
                rarity=match.character.rarity,
                class_name=match.character.class_name,
                aliases=sorted({alias.alias for alias in match.character.aliases}),
                source=match.character.source,
                source_version=match.character.source_version,
                fetched_at=match.character.fetched_at,
                match_type=match.match_type,
                confidence=match.confidence,
                requires_selection=multiple_candidates or match.match_type == "fuzzy",
            )
            for match in matches
        ]

    def data_source_status(self) -> DataSourceStatus | None:
        snapshot = self.repository.latest_atlas_snapshot()
        if not snapshot:
            return None
        character_count, material_count, snapshot_count = self.repository.atlas_counts()
        return DataSourceStatus(
            source="Atlas Academy",
            region="CN",
            version=snapshot.upstream_hash or snapshot.content_sha256[:12],
            server_hash=snapshot.server_hash,
            data_ver=snapshot.data_ver,
            fetched_at=snapshot.fetched_at,
            source_url="https://api.atlasacademy.io/",
            character_count=character_count,
            material_count=material_count,
            snapshot_count=snapshot_count,
        )

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
        merged: dict[tuple[int, int], SkillGoal] = {}
        for goal in request.goals:
            key = (goal.character_id, goal.skill_number)
            if key in merged:
                del merged[key]
            merged[key] = goal
        merged_goals = list(merged.values())
        goals = [
            (
                goal.character_id,
                goal.skill_number,
                goal.current_level,
                goal.target_level,
            )
            for goal in merged_goals
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
            goals=merged_goals,
            items=items,
            verification_notes=[
                "同一角色与技能的重复目标以后一次输入完整覆盖",
                "需求由技能等级消耗逐级汇总",
                "缺口使用 max(需求-库存, 0) 计算",
            ],
        )
