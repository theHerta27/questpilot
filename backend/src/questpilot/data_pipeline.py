from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from questpilot.character_aliases import CURATED_CHARACTER_ALIASES
from questpilot.models import (
    Character,
    CharacterAlias,
    DataConflict,
    GameEvent,
    GameQuest,
    Material,
    SkillLevelCost,
    SourceSnapshot,
)


@dataclass(frozen=True)
class FetchResult:
    url: str
    content: bytes
    etag: str | None
    last_modified: str | None

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


class AtlasClient:
    def __init__(self, base_url: str = "https://api.atlasacademy.io") -> None:
        self.base_url = base_url.rstrip("/")

    def fetch(self, path: str, *, timeout_seconds: float = 120) -> FetchResult:
        url = f"{self.base_url}/{path.lstrip('/')}"
        with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
        return FetchResult(
            url=url,
            content=response.content,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )

    def info(self) -> dict[str, Any]:
        return json.loads(self.fetch("/raw/CN/info", timeout_seconds=30).content)


class SnapshotStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(
        self,
        session: Session,
        *,
        source: str,
        region: str,
        dataset_name: str,
        result: FetchResult,
        upstream: dict[str, Any],
    ) -> SourceSnapshot:
        existing = session.scalar(
            select(SourceSnapshot).where(
                SourceSnapshot.source == source,
                SourceSnapshot.region == region,
                SourceSnapshot.content_sha256 == result.sha256,
            )
        )
        if existing:
            return existing
        target_dir = self.root / "snapshots" / source / region
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{dataset_name}-{result.sha256[:12]}.json"
        path.write_bytes(result.content)
        snapshot = SourceSnapshot(
            source=source,
            region=region,
            dataset_name=dataset_name,
            upstream_hash=upstream.get("hash"),
            server_hash=upstream.get("serverHash"),
            data_ver=upstream.get("dataVer"),
            etag=result.etag,
            last_modified=result.last_modified,
            content_sha256=result.sha256,
            local_path=str(path),
            metadata_json={"url": result.url},
        )
        session.add(snapshot)
        session.commit()
        return snapshot

    @staticmethod
    def latest_verified(
        session: Session, source: str, region: str, dataset_name: str
    ) -> SourceSnapshot | None:
        return session.scalar(
            select(SourceSnapshot)
            .where(
                SourceSnapshot.source == source,
                SourceSnapshot.region == region,
                SourceSnapshot.dataset_name == dataset_name,
                SourceSnapshot.published.is_(True),
            )
            .order_by(SourceSnapshot.fetched_at.desc())
        )


class AtlasAdapter:
    @staticmethod
    def character_row(
        raw: dict[str, Any], source_version: str, fetched_at: datetime | None = None
    ) -> dict[str, Any]:
        return {
            "game_id": int(raw["id"]),
            "collection_no": int(raw["collectionNo"]),
            "name_zh_cn": str(raw["name"]),
            "name_ja": raw.get("originalName"),
            "rarity": int(raw.get("rarity") or 0),
            "class_name": str(raw.get("className") or raw.get("classId") or "unknown"),
            "source": "atlas",
            "source_version": source_version,
            "fetched_at": fetched_at or datetime.now(UTC),
        }

    @staticmethod
    def material_rows(raw_items: list[dict[str, Any]], source_version: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in raw_items:
            if "id" not in item or not item.get("name"):
                continue
            rows.append(
                {
                    "game_id": int(item["id"]),
                    "name": str(item["name"]),
                    "item_type": str(item.get("type") or "unknown"),
                    "source_version": source_version,
                }
            )
        return rows

    @staticmethod
    def skill_cost_rows(raw: dict[str, Any]) -> list[dict[str, int]]:
        """Normalize Atlas variants into one row per level and item."""
        source = raw.get("skillMaterials") or raw.get("skill_materials") or {}
        # Current Atlas nice servant payloads expose one shared active-skill
        # material table keyed by the starting level ("1" means 1 -> 2).
        # Every one of the servant's three active skills uses that table.
        if (
            isinstance(source, dict)
            and source
            and all(
                isinstance(value, dict) and isinstance(value.get("items"), list)
                for value in source.values()
            )
        ):
            rows: list[dict[str, int]] = []
            for from_level_text, level in source.items():
                if not str(from_level_text).isdigit():
                    continue
                from_level = int(from_level_text)
                for entry in level.get("items") or []:
                    item = entry.get("item") or {}
                    item_id = entry.get("itemId") or entry.get("id") or item.get("id")
                    amount = entry.get("amount") or entry.get("count") or 0
                    if item_id and amount:
                        for skill_number in (1, 2, 3):
                            rows.append(
                                {
                                    "skill_number": skill_number,
                                    "from_level": from_level,
                                    "to_level": from_level + 1,
                                    "material_game_id": int(item_id),
                                    "amount": int(amount),
                                }
                            )
            return rows

        blocks: list[tuple[int, Any]] = []
        if isinstance(source, dict):
            blocks = [(int(key), value) for key, value in source.items() if str(key).isdigit()]
        elif isinstance(source, list):
            for index, value in enumerate(source, start=1):
                if isinstance(value, dict):
                    number = int(
                        value.get("skillNum")
                        or value.get("skill_number")
                        or value.get("num")
                        or index
                    )
                    levels = (
                        value.get("materials")
                        or value.get("levels")
                        or value.get("costs")
                        or []
                    )
                    blocks.append((number, levels))
                else:
                    blocks.append((index, value))
        rows: list[dict[str, int]] = []
        for skill_number, levels in blocks:
            if isinstance(levels, dict):
                level_pairs = [
                    (int(key), value) for key, value in levels.items() if str(key).isdigit()
                ]
            else:
                level_pairs = list(enumerate(levels or [], start=1))
            for level_index, level in level_pairs:
                if not isinstance(level, dict):
                    continue
                to_level = int(level.get("lv") or level.get("level") or level_index + 1)
                items = level.get("items") or level.get("materials") or []
                for entry in items:
                    item = entry.get("item") or {}
                    item_id = entry.get("itemId") or entry.get("id") or item.get("id")
                    amount = entry.get("amount") or entry.get("count") or 0
                    if item_id and amount:
                        rows.append(
                            {
                                "skill_number": skill_number,
                                "from_level": max(1, to_level - 1),
                                "to_level": to_level,
                                "material_game_id": int(item_id),
                                "amount": int(amount),
                            }
                        )
        return rows

    @staticmethod
    def quest_rows(raw_wars: list[dict[str, Any]], source_version: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for war in raw_wars:
            war_id = int(war.get("id") or 0)
            war_name = str(war.get("name") or "")
            for spot in war.get("spots") or []:
                spot_name = str(spot.get("name") or "")
                for quest in spot.get("quests") or []:
                    quest_id = quest.get("id")
                    if not quest_id:
                        continue
                    rows.append(
                        {
                            "game_id": int(quest_id),
                            "name": str(quest.get("name") or spot_name or quest_id),
                            "war_id": war_id,
                            "war_name": war_name,
                            "spot_name": spot_name,
                            "ap_cost": int(quest.get("consume") or quest.get("apCost") or 0),
                            "is_permanent": not bool(quest.get("eventId")),
                            "source_version": source_version,
                        }
                    )
        return rows

    @staticmethod
    def event_rows(raw_events: list[dict[str, Any]], source_version: str) -> list[dict[str, Any]]:
        def timestamp(value: Any) -> datetime | None:
            return datetime.fromtimestamp(int(value), tz=UTC) if value else None

        return [
            {
                "game_id": int(event["id"]),
                "name": str(event.get("name") or event["id"]),
                "started_at": timestamp(event.get("startedAt")),
                "ended_at": timestamp(event.get("endedAt")),
                "source_version": source_version,
            }
            for event in raw_events
            if event.get("id")
        ]


class AtlasPipeline:
    def __init__(self, session: Session, client: AtlasClient, store: SnapshotStore) -> None:
        self.session = session
        self.client = client
        self.store = store

    def fetch_snapshot(
        self, dataset_name: str, path: str, upstream: dict[str, Any]
    ) -> SourceSnapshot:
        result = self.client.fetch(path)
        json.loads(result.content)
        return self.store.save(
            self.session,
            source="atlas",
            region="CN",
            dataset_name=dataset_name,
            result=result,
            upstream=upstream,
        )

    def publish_materials(self, snapshot: SourceSnapshot) -> int:
        raw = json.loads(Path(snapshot.local_path).read_bytes())
        if not isinstance(raw, list):
            raise ValueError("nice_item snapshot must contain a list")
        version = snapshot.upstream_hash or snapshot.content_sha256[:12]
        rows = AtlasAdapter.material_rows(raw, version)
        with self.session.begin_nested():
            for row in rows:
                current = self.session.scalar(
                    select(Material).where(Material.game_id == row["game_id"])
                )
                if current:
                    if current.name != row["name"]:
                        self._record_conflict(
                            "material",
                            str(row["game_id"]),
                            "name",
                            current.name,
                            row["name"],
                        )
                    for key, value in row.items():
                        setattr(current, key, value)
                else:
                    self.session.add(Material(**row))
            snapshot.published = True
        self.session.commit()
        return len(rows)

    def publish_character(self, snapshot: SourceSnapshot) -> Character:
        raw = json.loads(Path(snapshot.local_path).read_bytes())
        version = snapshot.upstream_hash or snapshot.content_sha256[:12]
        character = self._upsert_character(raw, version, snapshot.fetched_at)
        snapshot.published = True
        self.session.commit()
        return character

    def _upsert_character(
        self, raw: dict[str, Any], version: str, fetched_at: datetime
    ) -> Character:
        row = AtlasAdapter.character_row(raw, version, fetched_at)
        character = self.session.scalar(
            select(Character).where(Character.collection_no == row["collection_no"])
        )
        if character:
            if character.name_zh_cn != row["name_zh_cn"]:
                self._record_conflict(
                    "character",
                    str(row["collection_no"]),
                    "name_zh_cn",
                    character.name_zh_cn,
                    row["name_zh_cn"],
                )
            for key, value in row.items():
                setattr(character, key, value)
        else:
            character = Character(**row)
            self.session.add(character)
            self.session.flush()
        self.session.execute(
            delete(SkillLevelCost).where(SkillLevelCost.character_id == character.id)
        )
        for cost in AtlasAdapter.skill_cost_rows(raw):
            material = self.session.scalar(
                select(Material).where(Material.game_id == cost.pop("material_game_id"))
            )
            if not material:
                raise ValueError("character references an unknown material; publish items first")
            self.session.add(
                SkillLevelCost(character_id=character.id, material_id=material.id, **cost)
            )
        aliases = {
            raw.get("name"),
            raw.get("originalName"),
            *CURATED_CHARACTER_ALIASES.get(character.collection_no, ()),
        }
        for alias in aliases:
            if alias and not self.session.scalar(
                select(CharacterAlias).where(
                    CharacterAlias.character_id == character.id,
                    CharacterAlias.alias == alias,
                )
            ):
                self.session.add(CharacterAlias(character_id=character.id, alias=alias))
        return character

    def publish_characters(self, snapshot: SourceSnapshot) -> int:
        raw = json.loads(Path(snapshot.local_path).read_bytes())
        if not isinstance(raw, list):
            raise ValueError("nice_servant snapshot must contain a list")
        version = snapshot.upstream_hash or snapshot.content_sha256[:12]
        with self.session.begin_nested():
            for row in raw:
                self._upsert_character(row, version, snapshot.fetched_at)
            snapshot.published = True
        self.session.commit()
        return len(raw)

    def publish_wars(self, snapshot: SourceSnapshot) -> int:
        raw = json.loads(Path(snapshot.local_path).read_bytes())
        if not isinstance(raw, list):
            raise ValueError("nice_war snapshot must contain a list")
        version = snapshot.upstream_hash or snapshot.content_sha256[:12]
        rows = AtlasAdapter.quest_rows(raw, version)
        for row in rows:
            current = self.session.scalar(
                select(GameQuest).where(GameQuest.game_id == row["game_id"])
            )
            if current:
                for key, value in row.items():
                    setattr(current, key, value)
            else:
                self.session.add(GameQuest(**row))
        snapshot.published = True
        self.session.commit()
        return len(rows)

    def publish_events(self, snapshot: SourceSnapshot) -> int:
        raw = json.loads(Path(snapshot.local_path).read_bytes())
        if not isinstance(raw, list):
            raise ValueError("nice_event snapshot must contain a list")
        version = snapshot.upstream_hash or snapshot.content_sha256[:12]
        rows = AtlasAdapter.event_rows(raw, version)
        for row in rows:
            current = self.session.scalar(
                select(GameEvent).where(GameEvent.game_id == row["game_id"])
            )
            if current:
                for key, value in row.items():
                    setattr(current, key, value)
            else:
                self.session.add(GameEvent(**row))
        snapshot.published = True
        self.session.commit()
        return len(rows)

    def _record_conflict(
        self,
        record_type: str,
        record_key: str,
        field_name: str,
        previous: Any,
        incoming: Any,
    ) -> None:
        self.session.add(
            DataConflict(
                source="atlas",
                record_type=record_type,
                record_key=record_key,
                field_name=field_name,
                previous_value=str(previous) if previous is not None else None,
                incoming_value=str(incoming) if incoming is not None else None,
            )
        )

    def sync_demo(self, collection_numbers: list[int]) -> dict[str, Any]:
        upstream = self.client.info()
        item_snapshot = self.fetch_snapshot(
            "nice_item", "/export/CN/nice_item.json", upstream
        )
        material_count = self.publish_materials(item_snapshot)
        characters = []
        for collection_no in collection_numbers:
            snapshot = self.fetch_snapshot(
                f"nice_servant_{collection_no}",
                f"/nice/CN/servant/{collection_no}",
                upstream,
            )
            characters.append(self.publish_character(snapshot).name_zh_cn)
        return {
            "version": upstream,
            "materials": material_count,
            "characters": characters,
        }

    def sync_full(self) -> dict[str, Any]:
        upstream = self.client.info()
        snapshots = {
            name: self.fetch_snapshot(name, f"/export/CN/{name}.json", upstream)
            for name in [
                "basic_servant",
                "nice_item",
                "nice_servant",
                "nice_war",
                "nice_event",
            ]
        }
        snapshots["basic_servant"].published = True
        self.session.commit()
        return {
            "version": upstream,
            "materials": self.publish_materials(snapshots["nice_item"]),
            "characters": self.publish_characters(snapshots["nice_servant"]),
            "quests": self.publish_wars(snapshots["nice_war"]),
            "events": self.publish_events(snapshots["nice_event"]),
        }
