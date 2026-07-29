from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from questpilot.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    collection_no: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name_zh_cn: Mapped[str] = mapped_column(String(160), index=True)
    name_ja: Mapped[str | None] = mapped_column(String(160))
    rarity: Mapped[int] = mapped_column(Integer, default=0)
    class_name: Mapped[str] = mapped_column(String(64), default="unknown")
    source: Mapped[str] = mapped_column(String(64), default="atlas")
    source_version: Mapped[str] = mapped_column(String(128), default="unknown")
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    aliases: Mapped[list[CharacterAlias]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )
    skill_costs: Mapped[list[SkillLevelCost]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )


class CharacterAlias(Base):
    __tablename__ = "character_aliases"
    __table_args__ = (UniqueConstraint("character_id", "alias", name="uq_character_alias"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"))
    alias: Mapped[str] = mapped_column(String(160), index=True)
    locale: Mapped[str] = mapped_column(String(16), default="zh-CN")

    character: Mapped[Character] = relationship(back_populates="aliases")


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    item_type: Mapped[str] = mapped_column(String(64), default="skillLvUp")
    source_version: Mapped[str] = mapped_column(String(128), default="unknown")


class SkillLevelCost(Base):
    __tablename__ = "skill_level_costs"
    __table_args__ = (
        UniqueConstraint(
            "character_id",
            "skill_number",
            "from_level",
            "to_level",
            "material_id",
            name="uq_skill_cost",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"))
    skill_number: Mapped[int] = mapped_column(Integer)
    from_level: Mapped[int] = mapped_column(Integer)
    to_level: Mapped[int] = mapped_column(Integer)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"))
    amount: Mapped[int] = mapped_column(Integer)

    character: Mapped[Character] = relationship(back_populates="skill_costs")
    material: Mapped[Material] = relationship()


class UserMaterialInventory(Base):
    __tablename__ = "user_material_inventory"
    __table_args__ = (UniqueConstraint("user_id", "material_id", name="uq_inventory_material"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="demo")
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    material: Mapped[Material] = relationship()


class SourceSnapshot(Base):
    __tablename__ = "source_snapshots"
    __table_args__ = (
        UniqueConstraint("source", "region", "content_sha256", name="uq_source_snapshot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    region: Mapped[str] = mapped_column(String(16), default="CN")
    dataset_name: Mapped[str] = mapped_column(String(128))
    upstream_hash: Mapped[str | None] = mapped_column(String(128))
    server_hash: Mapped[str | None] = mapped_column(String(128))
    data_ver: Mapped[int | None] = mapped_column(Integer)
    etag: Mapped[str | None] = mapped_column(String(256))
    last_modified: Mapped[str | None] = mapped_column(String(128))
    content_sha256: Mapped[str] = mapped_column(String(64), index=True)
    local_path: Mapped[str] = mapped_column(String(512))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class GameQuest(Base):
    __tablename__ = "game_quests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    war_id: Mapped[int] = mapped_column(Integer, index=True)
    war_name: Mapped[str] = mapped_column(String(200), default="")
    spot_name: Mapped[str] = mapped_column(String(200), default="")
    ap_cost: Mapped[int] = mapped_column(Integer, default=0)
    is_permanent: Mapped[bool] = mapped_column(Boolean, default=True)
    source_version: Mapped[str] = mapped_column(String(128))


class GameEvent(Base):
    __tablename__ = "game_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(240), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_version: Mapped[str] = mapped_column(String(128))


class DataConflict(Base):
    __tablename__ = "data_conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(64))
    record_type: Mapped[str] = mapped_column(String(64))
    record_key: Mapped[str] = mapped_column(String(160))
    field_name: Mapped[str] = mapped_column(String(128))
    previous_value: Mapped[str | None] = mapped_column(Text)
    incoming_value: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str] = mapped_column(String(64), default="source-priority")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), index=True)
    trace_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(64), default="demo")
    status: Mapped[str] = mapped_column(String(32), default="running")
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    model_name: Mapped[str] = mapped_column(String(128), default="fake")
    prompt_id: Mapped[str | None] = mapped_column(String(128))
    prompt_version: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExecutionEventRow(Base):
    __tablename__ = "execution_events"
    __table_args__ = (UniqueConstraint("run_id", "sequence", name="uq_event_sequence"),)

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    component: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    usage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AgentCheckpoint(Base):
    __tablename__ = "agent_checkpoints"
    __table_args__ = (UniqueConstraint("run_id", "node_name", "version", name="uq_checkpoint"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    node_name: Mapped[str] = mapped_column(String(128))
    version: Mapped[int] = mapped_column(Integer, default=1)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DropSource(Base):
    __tablename__ = "drop_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    source_url: Mapped[str] = mapped_column(String(512))
    license_status: Mapped[str] = mapped_column(String(64), default="unknown")


class DropDatasetVersion(Base):
    __tablename__ = "drop_dataset_versions"
    __table_args__ = (UniqueConstraint("source_id", "version", name="uq_drop_dataset_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("drop_sources.id"))
    version: Mapped[str] = mapped_column(String(128))
    upstream_commit: Mapped[str | None] = mapped_column(String(64))
    content_sha256: Mapped[str] = mapped_column(String(64))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    source: Mapped[DropSource] = relationship()


class QuestDropRate(Base):
    __tablename__ = "quest_drop_rates"
    __table_args__ = (
        UniqueConstraint("dataset_version_id", "quest_id", "item_id", name="uq_quest_drop_rate"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_version_id: Mapped[int] = mapped_column(ForeignKey("drop_dataset_versions.id"))
    quest_id: Mapped[int] = mapped_column(Integer, index=True)
    quest_name: Mapped[str] = mapped_column(String(200), default="")
    item_id: Mapped[int] = mapped_column(Integer, index=True)
    drop_rate_percent: Mapped[float] = mapped_column(Float)
    sample_runs: Mapped[int] = mapped_column(Integer)
    ap_cost: Mapped[int] = mapped_column(Integer)
    is_permanent: Mapped[bool] = mapped_column(Boolean, default=True)
    is_random_enemy: Mapped[bool] = mapped_column(Boolean, default=False)

    dataset_version: Mapped[DropDatasetVersion] = relationship()


class GeneratedPlan(Base):
    __tablename__ = "generated_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    user_id: Mapped[str] = mapped_column(String(64), default="demo")
    request_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="complete")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_url: Mapped[str] = mapped_column(String(512), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    revision: Mapped[str | None] = mapped_column(String(128))
    license_name: Mapped[str] = mapped_column(String(128), default="CC BY-NC-SA")
    content_sha256: Mapped[str] = mapped_column(String(64))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RagChunk(Base):
    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("rag_documents.id", ondelete="CASCADE"))
    heading: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text)
    token_estimate: Mapped[int] = mapped_column(Integer)
    embedding_json: Mapped[list[float]] = mapped_column(JSON, default=list)

    document: Mapped[RagDocument] = relationship()


class PromptRecord(Base):
    __tablename__ = "prompt_records"
    __table_args__ = (UniqueConstraint("prompt_id", "version", name="uq_prompt_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prompt_id: Mapped[str] = mapped_column(String(128))
    version: Mapped[str] = mapped_column(String(32))
    node_name: Mapped[str] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(Text)
    content_sha256: Mapped[str] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
