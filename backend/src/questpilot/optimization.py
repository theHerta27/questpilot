from __future__ import annotations

import math
from dataclasses import dataclass
from time import monotonic


@dataclass(frozen=True)
class CandidateQuest:
    quest_id: int
    quest_name: str
    ap_cost: int
    rates: dict[int, float]
    sample_runs: int


@dataclass(frozen=True)
class SolverResult:
    counts: dict[int, int]
    total_ap: int
    total_runs: int
    coverage: dict[int, float]
    complete: bool
    solver: str
    optimality: str
    search_nodes: int = 0
    limit_hit: bool = False


def _coverage(
    counts: dict[int, int],
    candidates: list[CandidateQuest],
    material_ids: set[int],
) -> dict[int, float]:
    result = {material_id: 0.0 for material_id in material_ids}
    by_id = {candidate.quest_id: candidate for candidate in candidates}
    for quest_id, runs in counts.items():
        candidate = by_id[quest_id]
        for material_id, rate in candidate.rates.items():
            if material_id in result:
                result[material_id] += runs * rate
    return result


class GreedyBaselinePlanner:
    """Deterministic feasible baseline; it makes no optimality claim."""

    def solve(
        self,
        gaps: dict[int, int],
        candidates: list[CandidateQuest],
        *,
        max_ap: int | None = None,
        max_runs: int | None = None,
    ) -> SolverResult:
        relevant = [
            candidate
            for candidate in candidates
            if any(candidate.rates.get(material_id, 0) > 0 for material_id in gaps)
        ]
        remaining = {key: float(value) for key, value in gaps.items() if value > 0}
        counts: dict[int, int] = {}
        total_ap = 0
        total_runs = 0
        while any(value > 1e-9 for value in remaining.values()):
            choices = []
            for candidate in relevant:
                progress = sum(
                    min(remaining.get(material_id, 0), rate)
                    for material_id, rate in candidate.rates.items()
                    if remaining.get(material_id, 0) > 1e-9
                )
                if progress <= 1e-9:
                    continue
                choices.append(
                    (
                        -(progress / candidate.ap_cost),
                        candidate.ap_cost,
                        -candidate.sample_runs,
                        candidate.quest_id,
                        candidate,
                    )
                )
            if not choices:
                break
            candidate = min(choices)[-1]
            if max_ap is not None and total_ap + candidate.ap_cost > max_ap:
                break
            if max_runs is not None and total_runs + 1 > max_runs:
                break
            counts[candidate.quest_id] = counts.get(candidate.quest_id, 0) + 1
            total_ap += candidate.ap_cost
            total_runs += 1
            for material_id, rate in candidate.rates.items():
                if material_id in remaining:
                    remaining[material_id] = max(0.0, remaining[material_id] - rate)
        coverage = _coverage(counts, relevant, set(gaps))
        complete = all(coverage.get(key, 0) + 1e-9 >= value for key, value in gaps.items())
        return SolverResult(
            counts=counts,
            total_ap=total_ap,
            total_runs=total_runs,
            coverage=coverage,
            complete=complete,
            solver="greedy-baseline",
            optimality="feasible_baseline" if complete else "partial_baseline",
        )


class BoundedBranchAndBoundPlanner:
    """Integer branch-and-bound minimizing AP, then run count."""

    def solve(
        self,
        gaps: dict[int, int],
        candidates: list[CandidateQuest],
        incumbent: SolverResult,
        *,
        node_limit: int,
        timeout_ms: int,
    ) -> SolverResult:
        if not incumbent.complete:
            return incumbent
        targets = {key: float(value) for key, value in gaps.items() if value > 0}
        ordered = sorted(
            [
                candidate
                for candidate in candidates
                if any(candidate.rates.get(material_id, 0) > 0 for material_id in targets)
            ],
            key=lambda candidate: (
                -sum(candidate.rates.get(key, 0) for key in targets) / candidate.ap_cost,
                candidate.ap_cost,
                candidate.quest_id,
            ),
        )
        best_counts = dict(incumbent.counts)
        best_ap = incumbent.total_ap
        best_runs = incumbent.total_runs
        nodes = 0
        limit_hit = False
        started = monotonic()

        def timed_out() -> bool:
            return (monotonic() - started) * 1000 >= timeout_ms

        def lower_bound_ap(index: int, coverage: dict[int, float]) -> float:
            bounds = []
            remaining_candidates = ordered[index:]
            for material_id, target in targets.items():
                deficit = max(0.0, target - coverage.get(material_id, 0))
                if deficit <= 1e-9:
                    continue
                best_rate_per_ap = max(
                    (
                        candidate.rates.get(material_id, 0) / candidate.ap_cost
                        for candidate in remaining_candidates
                    ),
                    default=0.0,
                )
                if best_rate_per_ap <= 0:
                    return math.inf
                bounds.append(deficit / best_rate_per_ap)
            return max(bounds, default=0.0)

        def visit(
            index: int,
            counts: dict[int, int],
            coverage: dict[int, float],
            total_ap: int,
            total_runs: int,
        ) -> None:
            nonlocal best_counts, best_ap, best_runs, nodes, limit_hit
            if limit_hit:
                return
            nodes += 1
            if nodes > node_limit or timed_out():
                limit_hit = True
                return
            if all(coverage.get(key, 0) + 1e-9 >= target for key, target in targets.items()):
                if (total_ap, total_runs) < (best_ap, best_runs):
                    best_counts = {key: value for key, value in counts.items() if value}
                    best_ap = total_ap
                    best_runs = total_runs
                return
            if index >= len(ordered) or total_ap >= best_ap:
                return
            bound = lower_bound_ap(index, coverage)
            if math.isinf(bound) or total_ap + math.ceil(bound - 1e-9) > best_ap:
                return

            candidate = ordered[index]
            ap_budget = best_ap - total_ap
            max_count = max(0, ap_budget // candidate.ap_cost)
            useful_counts = [
                math.ceil(
                    max(0.0, target - coverage.get(material_id, 0)) / rate
                )
                for material_id, target in targets.items()
                if (rate := candidate.rates.get(material_id, 0)) > 0
            ]
            if useful_counts:
                max_count = min(max_count, max(useful_counts))
            for count in range(max_count, -1, -1):
                next_ap = total_ap + count * candidate.ap_cost
                next_runs = total_runs + count
                if (next_ap, next_runs) >= (best_ap, best_runs):
                    continue
                next_coverage = dict(coverage)
                if count:
                    counts[candidate.quest_id] = count
                    for material_id, rate in candidate.rates.items():
                        if material_id in targets:
                            next_coverage[material_id] = (
                                next_coverage.get(material_id, 0) + count * rate
                            )
                visit(index + 1, counts, next_coverage, next_ap, next_runs)
                counts.pop(candidate.quest_id, None)

        visit(0, {}, {key: 0.0 for key in targets}, 0, 0)
        coverage = _coverage(best_counts, ordered, set(targets))
        return SolverResult(
            counts=best_counts,
            total_ap=best_ap,
            total_runs=best_runs,
            coverage=coverage,
            complete=True,
            solver="bounded-branch-and-bound",
            optimality="best_so_far" if limit_hit else "local_optimal",
            search_nodes=nodes,
            limit_hit=limit_hit,
        )
