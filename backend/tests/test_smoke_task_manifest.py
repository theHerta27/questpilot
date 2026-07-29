from __future__ import annotations

import json
from pathlib import Path


def test_deepseek_smoke_manifest_has_bounded_real_language_tasks():
    path = Path(__file__).parent / "fixtures" / "deepseek_smoke_tasks.json"
    content = path.read_text(encoding="utf-8")
    tasks = json.loads(content)
    assert 10 <= len(tasks) <= 20
    assert len({task["id"] for task in tasks}) == len(tasks)
    assert all(task["query"].strip() for task in tasks)
    assert all(task["required_tools"] for task in tasks)
    assert "sk-" not in content


def test_deepseek_planning_manifest_has_required_scope():
    path = Path(__file__).parent / "fixtures" / "deepseek_planning_tasks.json"
    content = path.read_text(encoding="utf-8")
    tasks = json.loads(content)
    assert 8 <= len(tasks) <= 12
    assert len({task["id"] for task in tasks}) == len(tasks)
    assert sum(not task["requires_selection"] for task in tasks) >= 8
    assert sum(task["requires_selection"] for task in tasks) >= 2
    assert any(task["expected_goal_count"] >= 2 for task in tasks)
    assert "sk-" not in content
