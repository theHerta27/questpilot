from __future__ import annotations

import pytest
from pydantic import ValidationError

from questpilot.repositories import GameRepository
from questpilot.schemas import (
    InventoryItemInput,
    InventoryReplaceRequest,
    MaterialGapRequest,
    SkillGoal,
)
from questpilot.services import GameService


def test_material_gap_is_deterministic_and_non_negative(seeded_session):
    repository = GameRepository(seeded_session)
    service = GameService(repository)
    character = repository.search_characters("阿尔托莉雅")[0]
    costs = service.skill_costs(character.id)
    first_material = costs[0].material_id
    service.update_inventory(
        InventoryReplaceRequest(
            items=[InventoryItemInput(material_id=first_material, quantity=999)]
        )
    )
    result = service.material_gap(
        MaterialGapRequest(
            goals=[
                SkillGoal(
                    character_id=character.id,
                    skill_number=1,
                    current_level=1,
                    target_level=4,
                ),
                SkillGoal(
                    character_id=character.id,
                    skill_number=2,
                    current_level=1,
                    target_level=3,
                ),
            ]
        )
    )
    assert result.verified
    assert all(item.gap == max(item.required - item.owned, 0) for item in result.items)
    assert next(item for item in result.items if item.material_id == first_material).gap == 0


def test_zero_length_goal_adds_no_cost(seeded_session):
    repository = GameRepository(seeded_session)
    character = repository.search_characters("玛修")[0]
    result = GameService(repository).material_gap(
        MaterialGapRequest(
            goals=[
                SkillGoal(
                    character_id=character.id,
                    skill_number=1,
                    current_level=5,
                    target_level=5,
                )
            ]
        )
    )
    assert result.items == []


def test_duplicate_skill_goals_are_fully_replaced_by_last_input(seeded_session):
    repository = GameRepository(seeded_session)
    character = repository.search_characters("阿尔托莉雅")[0]
    service = GameService(repository)
    merged = service.material_gap(
        MaterialGapRequest(
            goals=[
                SkillGoal(
                    character_id=character.id,
                    skill_number=1,
                    current_level=1,
                    target_level=4,
                ),
                SkillGoal(
                    character_id=character.id,
                    skill_number=1,
                    current_level=3,
                    target_level=5,
                ),
            ]
        )
    )
    direct = service.material_gap(
        MaterialGapRequest(
            goals=[
                SkillGoal(
                    character_id=character.id,
                    skill_number=1,
                    current_level=3,
                    target_level=5,
                )
            ]
        )
    )
    assert merged.goals == direct.goals
    assert merged.items == direct.items
    assert merged.verification_notes[0] == "同一角色与技能的重复目标以后一次输入完整覆盖"


@pytest.mark.parametrize(
    ("current_level", "target_level"),
    [(0, 1), (1, 11), (6, 5)],
)
def test_skill_goal_rejects_invalid_level_ranges(current_level, target_level):
    with pytest.raises(ValidationError):
        SkillGoal(
            character_id=1,
            skill_number=1,
            current_level=current_level,
            target_level=target_level,
        )
