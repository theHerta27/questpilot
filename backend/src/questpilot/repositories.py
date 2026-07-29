from __future__ import annotations

from collections import defaultdict

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, joinedload

from questpilot.models import (
    Character,
    CharacterAlias,
    Material,
    SkillLevelCost,
    UserMaterialInventory,
)


class GameRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search_characters(self, query: str, limit: int = 20) -> list[Character]:
        pattern = f"%{query.strip()}%"
        statement = (
            select(Character)
            .outerjoin(CharacterAlias)
            .options(joinedload(Character.aliases))
            .where(
                or_(
                    Character.name_zh_cn.ilike(pattern),
                    Character.name_ja.ilike(pattern),
                    CharacterAlias.alias.ilike(pattern),
                )
            )
            .distinct()
            .limit(limit)
        )
        return list(self.session.scalars(statement).unique())

    def get_character(self, character_id: int) -> Character | None:
        return self.session.scalar(
            select(Character)
            .options(joinedload(Character.aliases))
            .where(Character.id == character_id)
        )

    def skill_costs(self, character_id: int) -> list[SkillLevelCost]:
        return list(
            self.session.scalars(
                select(SkillLevelCost)
                .options(joinedload(SkillLevelCost.material))
                .where(SkillLevelCost.character_id == character_id)
                .order_by(
                    SkillLevelCost.skill_number,
                    SkillLevelCost.from_level,
                    SkillLevelCost.material_id,
                )
            )
        )

    def materials(self) -> list[Material]:
        return list(self.session.scalars(select(Material).order_by(Material.name)))

    def inventory(self, user_id: str) -> dict[int, UserMaterialInventory]:
        rows = self.session.scalars(
            select(UserMaterialInventory)
            .options(joinedload(UserMaterialInventory.material))
            .where(UserMaterialInventory.user_id == user_id)
        )
        return {row.material_id: row for row in rows}

    def replace_inventory(self, user_id: str, items: dict[int, int]) -> None:
        self.session.execute(
            delete(UserMaterialInventory).where(UserMaterialInventory.user_id == user_id)
        )
        for material_id, quantity in items.items():
            self.session.add(
                UserMaterialInventory(
                    user_id=user_id, material_id=material_id, quantity=max(0, quantity)
                )
            )
        self.session.commit()

    def increment_inventory(self, user_id: str, items: dict[int, int]) -> None:
        existing = self.inventory(user_id)
        for material_id, amount in items.items():
            if material_id in existing:
                existing[material_id].quantity = max(0, existing[material_id].quantity + amount)
            else:
                self.session.add(
                    UserMaterialInventory(
                        user_id=user_id, material_id=material_id, quantity=max(0, amount)
                    )
                )
        self.session.commit()

    def aggregate_requirements(
        self, goals: list[tuple[int, int, int, int]]
    ) -> dict[int, tuple[str, int]]:
        totals: dict[int, int] = defaultdict(int)
        names: dict[int, str] = {}
        for character_id, skill_number, current_level, target_level in goals:
            rows = self.session.scalars(
                select(SkillLevelCost)
                .options(joinedload(SkillLevelCost.material))
                .where(
                    SkillLevelCost.character_id == character_id,
                    SkillLevelCost.skill_number == skill_number,
                    SkillLevelCost.from_level >= current_level,
                    SkillLevelCost.to_level <= target_level,
                )
            )
            for row in rows:
                totals[row.material_id] += row.amount
                names[row.material_id] = row.material.name
        return {material_id: (names[material_id], amount) for material_id, amount in totals.items()}

