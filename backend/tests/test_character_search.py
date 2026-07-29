from __future__ import annotations

from questpilot.models import Character, CharacterAlias
from questpilot.repositories import GameRepository
from questpilot.services import GameService


def test_exact_alias_is_selected_with_high_confidence(seeded_session):
    result = GameService(GameRepository(seeded_session)).search_characters("蓝呆")
    assert len(result) == 1
    assert result[0].name_zh_cn == "阿尔托莉雅·潘德拉贡"
    assert result[0].match_type == "exact_alias"
    assert result[0].confidence == 0.99
    assert not result[0].requires_selection


def test_alias_embedded_in_natural_language_is_still_exact(seeded_session):
    result = GameService(GameRepository(seeded_session)).search_characters(
        "帮我查蓝呆三个技能的升级材料"
    )
    assert len(result) == 1
    assert result[0].match_type == "exact_alias"
    assert result[0].confidence == 0.96
    assert not result[0].requires_selection


def test_exact_alias_discards_other_fuzzy_candidates(seeded_session):
    similar = Character(
        game_id=203,
        collection_no=203,
        name_zh_cn="阿尔托莉雅",
        rarity=4,
        class_name="Lancer",
        source="atlas",
        source_version="test",
    )
    seeded_session.add(similar)
    seeded_session.commit()
    result = GameService(GameRepository(seeded_session)).search_characters("蓝呆")
    assert [item.collection_no for item in result] == [2]
    assert result[0].match_type == "exact_alias"
    assert not result[0].requires_selection


def test_fuzzy_match_never_silently_selects(seeded_session):
    result = GameService(GameRepository(seeded_session)).search_characters("阿尔托利雅")
    assert result
    assert result[0].match_type == "fuzzy"
    assert result[0].requires_selection


def test_duplicate_canonical_names_require_user_selection(seeded_session):
    other = Character(
        game_id=202,
        collection_no=202,
        name_zh_cn="阿尔托莉雅·潘德拉贡",
        name_ja="アルトリア",
        rarity=4,
        class_name="Lancer",
        source="atlas",
        source_version="test",
    )
    seeded_session.add(other)
    seeded_session.flush()
    seeded_session.add(CharacterAlias(character_id=other.id, alias="枪呆"))
    seeded_session.commit()

    result = GameService(GameRepository(seeded_session)).search_characters(
        "阿尔托莉雅·潘德拉贡"
    )
    assert len(result) == 2
    assert all(item.match_type == "exact_name" for item in result)
    assert all(item.requires_selection for item in result)
