from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from questpilot.models import (
    DropDatasetVersion,
    DropSource,
    GameQuest,
    Material,
    QuestDropRate,
)


@dataclass(frozen=True)
class NormalizedDropRate:
    quest_id: int
    quest_name: str
    item_id: int
    drop_rate_percent: float
    sample_runs: int
    ap_cost: int
    is_permanent: bool = True
    is_random_enemy: bool = False


class CommunityDropAdapter:
    """Adapter for chaldea-data dropData.json plus a readable fixture format."""

    @staticmethod
    def parse(raw: dict[str, Any]) -> list[NormalizedDropRate]:
        if "rates" in raw:
            return [NormalizedDropRate(**row) for row in raw["rates"]]
        dataset = raw.get("domusAurea") or raw
        item_ids = dataset.get("itemIds") or dataset.get("items") or []
        quest_ids = dataset.get("questIds") or dataset.get("quests") or []
        ap_costs = dataset.get("apCosts") or []
        runs = dataset.get("runs") or dataset.get("sampleRuns") or []
        names = dataset.get("questNames") or {}
        matrix = dataset.get("sparseMatrix") or {}
        rows: list[NormalizedDropRate] = []

        def emit(item_index: int, quest_index: int, rate: float) -> None:
            if not (0 <= item_index < len(item_ids) and 0 <= quest_index < len(quest_ids)):
                return
            sample = int(runs[quest_index]) if quest_index < len(runs) else 0
            ap = int(ap_costs[quest_index]) if quest_index < len(ap_costs) else 0
            quest_id = int(quest_ids[quest_index])
            name = (
                str(names.get(str(quest_id)) or names.get(quest_id) or quest_id)
                if isinstance(names, dict)
                else str(names[quest_index] if quest_index < len(names) else quest_id)
            )
            rows.append(
                NormalizedDropRate(
                    quest_id=quest_id,
                    quest_name=name,
                    item_id=int(item_ids[item_index]),
                    drop_rate_percent=float(rate),
                    sample_runs=sample,
                    ap_cost=ap,
                )
            )

        if isinstance(matrix, dict):
            for item_key, entries in matrix.items():
                item_index = int(item_key)
                if isinstance(entries, dict):
                    for quest_key, rate in entries.items():
                        emit(item_index, int(quest_key), float(rate))
                else:
                    for entry in entries or []:
                        if isinstance(entry, dict):
                            emit(
                                item_index,
                                int(entry.get("questIndex") or entry.get("index") or 0),
                                float(entry.get("rate") or entry.get("value") or 0),
                            )
                        else:
                            emit(item_index, int(entry[0]), float(entry[1]))
        elif isinstance(matrix, list):
            for item_index, entries in enumerate(matrix):
                for entry in entries or []:
                    emit(item_index, int(entry[0]), float(entry[1]))
        return rows


class DropDatasetPublisher:
    def __init__(self, session: Session) -> None:
        self.session = session

    def publish(
        self,
        raw_bytes: bytes,
        *,
        source_url: str,
        upstream_commit: str | None = None,
        allowed_quest_ids: set[int] | None = None,
        minimum_sample_runs: int = 1,
    ) -> DropDatasetVersion:
        raw = json.loads(raw_bytes)
        content_hash = hashlib.sha256(raw_bytes).hexdigest()
        source = self.session.scalar(
            select(DropSource).where(DropSource.slug == "chaldea-domus")
        )
        if not source:
            source = DropSource(
                slug="chaldea-domus",
                name="Chaldea / Domus Aurea community observations",
                source_url=source_url,
                license_status="review-required",
            )
            self.session.add(source)
            self.session.flush()
        version_name = str(raw.get("domusVer") or content_hash[:12])
        dataset = self.session.scalar(
            select(DropDatasetVersion).where(
                DropDatasetVersion.source_id == source.id,
                DropDatasetVersion.version == version_name,
            )
        )
        if dataset:
            return dataset
        dataset = DropDatasetVersion(
            source_id=source.id,
            version=version_name,
            upstream_commit=upstream_commit,
            content_sha256=content_hash,
            fetched_at=datetime.now(UTC),
            metadata_json={
                "scope": "versioned demo subset",
                "raw_distribution": False,
            },
        )
        self.session.add(dataset)
        self.session.flush()
        normalized = CommunityDropAdapter.parse(raw)
        selected = [
            row
            for row in normalized
            if (allowed_quest_ids is None or row.quest_id in allowed_quest_ids)
            and row.is_permanent
            and not row.is_random_enemy
            and row.sample_runs >= minimum_sample_runs
            and row.ap_cost > 0
            and row.drop_rate_percent > 0
        ]
        if len({row.quest_id for row in selected}) > 20:
            raise ValueError("M3 dataset may contain at most 20 candidate quests")
        for row in selected:
            material = self.session.scalar(
                select(Material).where(Material.game_id == row.item_id)
            )
            if material:
                quest = self.session.scalar(
                    select(GameQuest).where(GameQuest.game_id == row.quest_id)
                )
                values = {
                    **row.__dict__,
                    "item_id": material.id,
                    "quest_name": quest.name if quest else row.quest_name,
                    "ap_cost": row.ap_cost or (quest.ap_cost if quest else 0),
                }
                self.session.add(QuestDropRate(dataset_version_id=dataset.id, **values))
        self.session.commit()
        return dataset


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    required = {"source_url", "upstream_commit", "domus_version", "content_sha256"}
    missing = required.difference(manifest)
    if missing:
        raise ValueError(f"drop manifest missing fields: {sorted(missing)}")
    return manifest
