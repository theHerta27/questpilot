from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from questpilot.models import (
    Character,
    DropDatasetVersion,
    Material,
    QuestDropRate,
    SkillLevelCost,
    SourceSnapshot,
    UserMaterialInventory,
)


def normalize_character_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[\s\-—·・.（）()【】\[\]_]+", "", normalized)


@dataclass(frozen=True)
class CharacterMatch:
    character: Character
    match_type: str
    confidence: float


class GameRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search_character_matches(self, query: str, limit: int = 20) -> list[CharacterMatch]:
        normalized_query = normalize_character_name(query)
        if not normalized_query:
            return []
        characters = list(
            self.session.scalars(
                select(Character)
                .options(joinedload(Character.aliases))
                .order_by(Character.collection_no)
            ).unique()
        )
        matches: list[CharacterMatch] = []
        for character in characters:
            canonical_names = [
                normalize_character_name(character.name_zh_cn),
                normalize_character_name(character.name_ja or ""),
            ]
            alias_names = [normalize_character_name(alias.alias) for alias in character.aliases]
            canonical_names = [name for name in canonical_names if name]
            alias_names = [name for name in alias_names if name and name not in canonical_names]
            if normalized_query in canonical_names:
                matches.append(CharacterMatch(character, "exact_name", 1.0))
                continue
            if normalized_query in alias_names:
                matches.append(CharacterMatch(character, "exact_alias", 0.99))
                continue
            if any(len(name) >= 2 and name in normalized_query for name in canonical_names):
                matches.append(CharacterMatch(character, "exact_name", 0.97))
                continue
            if any(len(name) >= 2 and name in normalized_query for name in alias_names):
                matches.append(CharacterMatch(character, "exact_alias", 0.96))
                continue
            candidates = canonical_names + alias_names
            score = max(
                (
                    max(
                        SequenceMatcher(None, normalized_query, name).ratio(),
                        min(len(normalized_query), len(name))
                        / max(len(normalized_query), len(name))
                        if normalized_query in name or name in normalized_query
                        else 0,
                    )
                    for name in candidates
                ),
                default=0,
            )
            if score >= 0.45:
                matches.append(CharacterMatch(character, "fuzzy", round(score, 3)))
        exact_matches = [match for match in matches if match.match_type != "fuzzy"]
        if exact_matches:
            matches = exact_matches
        priority = {"exact_name": 0, "exact_alias": 1, "fuzzy": 2}
        matches.sort(
            key=lambda item: (
                priority[item.match_type],
                -item.confidence,
                item.character.collection_no,
            )
        )
        return matches[:limit]

    def search_characters(self, query: str, limit: int = 20) -> list[Character]:
        return [match.character for match in self.search_character_matches(query, limit)]

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

    def latest_atlas_snapshot(self) -> SourceSnapshot | None:
        return self.session.scalar(
            select(SourceSnapshot)
            .where(
                SourceSnapshot.source == "atlas",
                SourceSnapshot.region == "CN",
                SourceSnapshot.published.is_(True),
            )
            .order_by(SourceSnapshot.fetched_at.desc())
        )

    def atlas_counts(self) -> tuple[int, int, int]:
        character_count = self.session.scalar(select(func.count()).select_from(Character)) or 0
        material_count = self.session.scalar(select(func.count()).select_from(Material)) or 0
        snapshot_count = (
            self.session.scalar(
                select(func.count())
                .select_from(SourceSnapshot)
                .where(
                    SourceSnapshot.source == "atlas",
                    SourceSnapshot.region == "CN",
                    SourceSnapshot.published.is_(True),
                )
            )
            or 0
        )
        return character_count, material_count, snapshot_count

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
    ) -> dict[int, tuple[str, int, int]]:
        totals: dict[int, int] = defaultdict(int)
        names: dict[int, str] = {}
        game_ids: dict[int, int] = {}
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
                game_ids[row.material_id] = row.material.game_id
        return {
            material_id: (names[material_id], amount, game_ids[material_id])
            for material_id, amount in totals.items()
        }

    def latest_drop_dataset(self) -> tuple[DropDatasetVersion, int] | None:
        dataset = self.session.scalar(
            select(DropDatasetVersion)
            .options(joinedload(DropDatasetVersion.source))
            .order_by(DropDatasetVersion.fetched_at.desc())
        )
        if not dataset:
            return None
        rate_count = int(
            self.session.scalar(
                select(func.count(QuestDropRate.id)).where(
                    QuestDropRate.dataset_version_id == dataset.id
                )
            )
            or 0
        )
        return dataset, rate_count
