from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from questpilot.drop_rates import DropDatasetPublisher
from questpilot.models import Character, CharacterAlias, Material, SkillLevelCost
from questpilot.rag import MooncellIndex
from questpilot.replay import PromptRegistry

DEMO_MATERIALS = [
    (6501, "英雄之证", "skillLvUp"),
    (6503, "虚影之尘", "skillLvUp"),
    (6532, "大骑士勋章", "skillLvUp"),
]

DEMO_CHARACTERS = [
    (2, 2, "阿尔托莉雅·潘德拉贡", "アルトリア・ペンドラゴン", 5, "Saber", ["呆毛王", "蓝呆"]),
    (1, 1, "玛修·基列莱特", "マシュ・キリエライト", 4, "Shielder", ["学妹", "玛修"]),
]


def seed_demo(session: Session) -> dict[str, int]:
    materials: list[Material] = []
    for game_id, name, item_type in DEMO_MATERIALS:
        material = session.scalar(select(Material).where(Material.game_id == game_id))
        if not material:
            material = Material(
                game_id=game_id,
                name=name,
                item_type=item_type,
                source_version="synthetic-1",
            )
            session.add(material)
            session.flush()
        materials.append(material)
    for game_id, collection_no, name, original_name, rarity, class_name, aliases in DEMO_CHARACTERS:
        character = session.scalar(
            select(Character).where(Character.collection_no == collection_no)
        )
        if not character:
            character = Character(
                game_id=game_id,
                collection_no=collection_no,
                name_zh_cn=name,
                name_ja=original_name,
                rarity=rarity,
                class_name=class_name,
                source="synthetic",
                source_version="synthetic-1",
            )
            session.add(character)
            session.flush()
        for alias in aliases:
            if not session.scalar(
                select(CharacterAlias).where(
                    CharacterAlias.character_id == character.id,
                    CharacterAlias.alias == alias,
                )
            ):
                session.add(CharacterAlias(character_id=character.id, alias=alias))
        if not session.scalar(
            select(SkillLevelCost).where(SkillLevelCost.character_id == character.id)
        ):
            for skill_number in range(1, 4):
                for from_level in range(1, 10):
                    material = materials[(from_level + skill_number - 2) % len(materials)]
                    session.add(
                        SkillLevelCost(
                            character_id=character.id,
                            skill_number=skill_number,
                            from_level=from_level,
                            to_level=from_level + 1,
                            material_id=material.id,
                            amount=(from_level + skill_number) * (2 if rarity == 5 else 1),
                        )
                    )
    session.commit()
    drop_fixture = {
        "domusVer": "demo-2026.07",
        "rates": [
            {
                "quest_id": 930001,
                "quest_name": "冬木 X-C",
                "item_id": 6501,
                "drop_rate_percent": 64.0,
                "sample_runs": 12400,
                "ap_cost": 4,
            },
            {
                "quest_id": 930002,
                "quest_name": "夏洛特",
                "item_id": 6503,
                "drop_rate_percent": 72.0,
                "sample_runs": 18300,
                "ap_cost": 20,
            },
            {
                "quest_id": 930003,
                "quest_name": "王城",
                "item_id": 6532,
                "drop_rate_percent": 54.0,
                "sample_runs": 7600,
                "ap_cost": 21,
            },
        ],
    }
    DropDatasetPublisher(session).publish(
        json.dumps(drop_fixture, ensure_ascii=False, sort_keys=True).encode("utf-8"),
        source_url="synthetic://questpilot/drop-fixture",
        upstream_commit="synthetic-1",
        minimum_sample_runs=100,
    )
    MooncellIndex(session).ingest(
        source_url="https://fgo.wiki/w/QuestPilot演示/技能强化",
        revision="synthetic-1",
        html="""<html><head><title>技能强化演示</title></head><body>
        <h1>技能强化</h1><p>技能从当前等级逐级提升到目标等级，每一级消耗独立累计。</p>
        <h2>规划提示</h2><p>先核对库存，再根据材料缺口选择关卡。</p></body></html>""",
    )
    prompts = PromptRegistry(session)
    prompts.register(
        "agent.system",
        "1.0.0",
        "agent",
        "精确游戏事实与材料数量必须通过已注册工具获取。",
    )
    prompts.register(
        "planner.workflow",
        "1.0.0",
        "planning_graph",
        "只在版本固定的候选关卡内生成可验证的局部规划。",
    )
    return {
        "materials": len(materials),
        "characters": len(DEMO_CHARACTERS),
        "drop_quests": len(drop_fixture["rates"]),
    }
