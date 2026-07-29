from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select

from questpilot.drop_rates import DropDatasetPublisher
from questpilot.models import DropDatasetVersion, GameQuest, QuestDropRate


def _real_scope_fixture(seeded_session, *, quest_count: int = 10, ap_mismatch: bool = False):
    quest_ids = list(range(93010001, 93010001 + quest_count))
    item_ids = [6501, 6503, 6532]
    for index, quest_id in enumerate(quest_ids):
        seeded_session.add(
            GameQuest(
                game_id=quest_id,
                name=f"自由关卡 {index + 1}",
                war_id=100,
                war_name="测试章节",
                spot_name=f"地点 {index + 1}",
                ap_cost=20,
                is_permanent=True,
                quest_type="free",
                flags_json=["displayLoopmark"],
                source_version="atlas-fixture",
            )
        )
    seeded_session.commit()
    rates = [
        {
            "quest_id": quest_id,
            "quest_name": str(quest_id),
            "item_id": item_id,
            "drop_rate_percent": 20.0 + item_index,
            "sample_runs": 1000,
            "ap_cost": 21 if ap_mismatch and quest_index == 0 else 20,
        }
        for quest_index, quest_id in enumerate(quest_ids)
        for item_index, item_id in enumerate(item_ids)
    ]
    return (
        json.dumps(
            {
                "domusVer": f"verified-subset-{quest_count}-{ap_mismatch}",
                "rates": rates,
            }
        ).encode(),
        set(quest_ids),
        set(item_ids),
    )


def test_verified_subset_publishes_only_fixed_scope(seeded_session):
    raw, quest_ids, item_ids = _real_scope_fixture(seeded_session)
    dataset = DropDatasetPublisher(seeded_session).publish(
        raw,
        source_url="https://example.test/pinned/dropData.json",
        upstream_commit="a" * 40,
        allowed_quest_ids=quest_ids,
        allowed_item_ids=item_ids,
        minimum_sample_runs=100,
        license_status="unverified-local-only",
        enforce_demo_scope=True,
    )
    count = seeded_session.scalar(
        select(func.count(QuestDropRate.id)).where(
            QuestDropRate.dataset_version_id == dataset.id
        )
    )
    assert dataset.metadata_json["candidate_quest_count"] == 10
    assert dataset.metadata_json["material_count"] == 3
    assert count == 30


def test_verified_subset_rejects_atlas_ap_mismatch_and_rolls_back(seeded_session):
    raw, quest_ids, item_ids = _real_scope_fixture(seeded_session, ap_mismatch=True)
    before = seeded_session.scalar(select(func.count(DropDatasetVersion.id)))
    with pytest.raises(ValueError, match="AP mismatch"):
        DropDatasetPublisher(seeded_session).publish(
            raw,
            source_url="https://example.test/pinned/dropData.json",
            upstream_commit="a" * 40,
            allowed_quest_ids=quest_ids,
            allowed_item_ids=item_ids,
            minimum_sample_runs=100,
            license_status="unverified-local-only",
            enforce_demo_scope=True,
        )
    seeded_session.rollback()
    assert seeded_session.scalar(select(func.count(DropDatasetVersion.id))) == before


def test_verified_subset_rejects_too_few_quests(seeded_session):
    raw, quest_ids, item_ids = _real_scope_fixture(seeded_session, quest_count=9)
    with pytest.raises(ValueError, match="10 to 20"):
        DropDatasetPublisher(seeded_session).publish(
            raw,
            source_url="https://example.test/pinned/dropData.json",
            upstream_commit="a" * 40,
            allowed_quest_ids=quest_ids,
            allowed_item_ids=item_ids,
            enforce_demo_scope=True,
        )
