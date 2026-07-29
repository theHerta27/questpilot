from __future__ import annotations

from questpilot.data_pipeline import AtlasAdapter
from questpilot.drop_rates import CommunityDropAdapter


def test_atlas_skill_material_adapter_handles_level_rows():
    raw = {
        "skillMaterials": {
            "1": [
                {
                    "lv": 2,
                    "items": [{"item": {"id": 6501}, "amount": 5}],
                },
                {
                    "lv": 3,
                    "items": [{"itemId": 6503, "amount": 8}],
                },
            ]
        }
    }
    assert AtlasAdapter.skill_cost_rows(raw) == [
        {
            "skill_number": 1,
            "from_level": 1,
            "to_level": 2,
            "material_game_id": 6501,
            "amount": 5,
        },
        {
            "skill_number": 1,
            "from_level": 2,
            "to_level": 3,
            "material_game_id": 6503,
            "amount": 8,
        },
    ]


def test_drop_sparse_matrix_preserves_indexes_and_samples():
    raw = {
        "domusVer": "test-1",
        "itemIds": [6501, 6503],
        "questIds": [100, 200],
        "questNames": {"100": "A", "200": "B"},
        "apCosts": [10, 20],
        "runs": [500, 800],
        "sparseMatrix": {"0": [[1, 42.5]], "1": [[0, 61.0]]},
    }
    rows = CommunityDropAdapter.parse(raw)
    assert [(row.item_id, row.quest_id) for row in rows] == [(6501, 200), (6503, 100)]
    assert rows[0].sample_runs == 800
    assert rows[0].ap_cost == 20


def test_drop_adapter_unwraps_real_domus_aurea_shape():
    raw = {
        "domusVer": 1779642278,
        "domusAurea": {
            "itemIds": [6501],
            "questIds": [93000001],
            "apCosts": [7],
            "runs": [1200],
            "sparseMatrix": [[[0, 55.5]]],
        },
        "freeDrops": {},
        "fixedDrops": {},
    }
    rows = CommunityDropAdapter.parse(raw)
    assert len(rows) == 1
    assert rows[0].item_id == 6501
    assert rows[0].quest_id == 93000001
    assert rows[0].sample_runs == 1200


def test_atlas_war_and_event_adapters_preserve_facts():
    quests = AtlasAdapter.quest_rows(
        [
            {
                "id": 10,
                "name": "序章",
                "spots": [
                    {
                        "name": "冬木",
                        "quests": [{"id": 100, "name": "X-C", "consume": 4}],
                    }
                ],
            }
        ],
        "v1",
    )
    assert quests[0]["game_id"] == 100
    assert quests[0]["ap_cost"] == 4
    assert quests[0]["war_name"] == "序章"
    events = AtlasAdapter.event_rows(
        [{"id": 20, "name": "演示活动", "startedAt": 1, "endedAt": 2}],
        "v1",
    )
    assert events[0]["started_at"] is not None
