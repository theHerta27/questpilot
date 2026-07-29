from __future__ import annotations

from copy import deepcopy

from questpilot.planning_validation import DeterministicPlanValidator
from questpilot.schemas import (
    FarmingStep,
    MaterialGapItem,
    MaterialGapResult,
    PlanRequest,
    PlanResult,
    SkillGoal,
)


def _request_and_result():
    goal = SkillGoal(
        character_id=1,
        skill_number=1,
        current_level=8,
        target_level=9,
    )
    request = PlanRequest(
        goals=[goal],
        current_ap=100,
        daily_minutes=60,
        minutes_per_run=3,
    )
    result = PlanResult(
        plan_id="plan",
        run_id="run",
        material_gap=MaterialGapResult(
            user_id="demo",
            goals=[goal],
            items=[
                MaterialGapItem(
                    material_id=7,
                    material_game_id=6503,
                    material_name="英雄之证",
                    image_url="/api/v1/assets/materials/6503.png",
                    required=2,
                    owned=0,
                    gap=2,
                )
            ],
        ),
        steps=[
            FarmingStep(
                quest_id=100,
                quest_name="验证关卡",
                runs=2,
                ap_cost=10,
                expected_drops={7: 2.0},
                sample_runs=1000,
            )
        ],
        total_ap=20,
        available_ap=100,
        completion_ratio=1,
        status="complete",
        dataset_version="v1",
        candidate_scope="1 个测试关卡",
        verified=True,
    )
    return request, result


def test_validator_accepts_consistent_plan():
    request, result = _request_and_result()
    report = DeterministicPlanValidator().validate(
        request,
        result,
        allowed_quest_ids={100},
        dataset_version="v1",
    )
    assert report.valid
    assert report.evidence["calculated_ap"] == 20


def test_validator_rejects_material_ap_and_candidate_tampering():
    request, result = _request_and_result()
    tampered = deepcopy(result)
    tampered.total_ap = 5
    tampered.steps[0].quest_id = 999
    tampered.steps[0].expected_drops = {7: 0.5}
    tampered.material_gap.items[0].gap = 9
    report = DeterministicPlanValidator().validate(
        request,
        tampered,
        allowed_quest_ids={100},
        dataset_version="v1",
    )
    assert not report.valid
    assert len(report.errors) >= 4
