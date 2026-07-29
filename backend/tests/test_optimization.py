from __future__ import annotations

from itertools import product

import pytest

from questpilot.optimization import (
    BoundedBranchAndBoundPlanner,
    CandidateQuest,
    GreedyBaselinePlanner,
)


def _problem():
    gaps = {1: 2, 2: 2}
    candidates = [
        CandidateQuest(1, "材料一", 6, {1: 1.0}, 1000),
        CandidateQuest(2, "材料二", 6, {2: 1.0}, 1000),
        CandidateQuest(3, "副产物路线", 10, {1: 0.9, 2: 0.9}, 1000),
        CandidateQuest(4, "一次完成", 24, {1: 2.0, 2: 2.0}, 1000),
    ]
    return gaps, candidates


def _oracle(gaps, candidates, max_count=4):
    best = None
    best_counts = None
    for values in product(range(max_count + 1), repeat=len(candidates)):
        coverage = {
            material_id: sum(
                values[index] * candidate.rates.get(material_id, 0)
                for index, candidate in enumerate(candidates)
            )
            for material_id in gaps
        }
        if not all(coverage[key] + 1e-9 >= value for key, value in gaps.items()):
            continue
        objective = (
            sum(values[index] * candidate.ap_cost for index, candidate in enumerate(candidates)),
            sum(values),
        )
        if best is None or objective < best:
            best = objective
            best_counts = {
                candidate.quest_id: values[index]
                for index, candidate in enumerate(candidates)
                if values[index]
            }
    return best, best_counts


def test_greedy_baseline_is_deterministic_and_feasible():
    gaps, candidates = _problem()
    planner = GreedyBaselinePlanner()
    first = planner.solve(gaps, candidates)
    second = planner.solve(gaps, list(reversed(candidates)))
    assert first.complete
    assert first == second
    assert first.optimality == "feasible_baseline"


def test_bounded_branch_and_bound_matches_small_exhaustive_oracle():
    gaps, candidates = _problem()
    baseline = GreedyBaselinePlanner().solve(gaps, candidates)
    result = BoundedBranchAndBoundPlanner().solve(
        gaps,
        candidates,
        baseline,
        node_limit=100_000,
        timeout_ms=2_000,
    )
    oracle_objective, oracle_counts = _oracle(gaps, candidates)
    assert (result.total_ap, result.total_runs) == oracle_objective
    assert result.counts == oracle_counts
    assert result.optimality == "local_optimal"
    assert not result.limit_hit


def test_bounded_search_returns_best_so_far_when_limit_is_hit():
    gaps, candidates = _problem()
    baseline = GreedyBaselinePlanner().solve(gaps, candidates)
    result = BoundedBranchAndBoundPlanner().solve(
        gaps,
        candidates,
        baseline,
        node_limit=1,
        timeout_ms=2_000,
    )
    assert result.complete
    assert result.limit_hit
    assert result.optimality == "best_so_far"
    assert result.total_ap == baseline.total_ap


@pytest.mark.parametrize(
    ("gaps", "candidates"),
    [
        (
            {1: 3},
            [
                CandidateQuest(10, "稳定低掉率", 4, {1: 0.7}, 1000),
                CandidateQuest(11, "高掉率", 7, {1: 1.5}, 1000),
            ],
        ),
        (
            {1: 2, 2: 1},
            [
                CandidateQuest(20, "一", 5, {1: 1.0}, 1000),
                CandidateQuest(21, "二", 4, {2: 0.6}, 1000),
                CandidateQuest(22, "组合", 8, {1: 0.7, 2: 0.7}, 1000),
            ],
        ),
        (
            {1: 1, 2: 1, 3: 1},
            [
                CandidateQuest(30, "一", 3, {1: 0.6}, 1000),
                CandidateQuest(31, "二", 4, {2: 0.8}, 1000),
                CandidateQuest(32, "三", 5, {3: 1.0}, 1000),
                CandidateQuest(33, "组合", 9, {1: 0.6, 2: 0.6, 3: 0.6}, 1000),
            ],
        ),
    ],
)
def test_bounded_solver_matches_oracle_across_small_problems(gaps, candidates):
    baseline = GreedyBaselinePlanner().solve(gaps, candidates)
    result = BoundedBranchAndBoundPlanner().solve(
        gaps,
        candidates,
        baseline,
        node_limit=100_000,
        timeout_ms=2_000,
    )
    oracle_objective, _ = _oracle(gaps, candidates, max_count=6)
    assert (result.total_ap, result.total_runs) == oracle_objective
    assert result.optimality == "local_optimal"
