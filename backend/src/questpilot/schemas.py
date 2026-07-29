from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CharacterSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    game_id: int
    collection_no: int
    name_zh_cn: str
    name_ja: str | None = None
    rarity: int
    class_name: str
    aliases: list[str] = Field(default_factory=list)
    source: str
    source_version: str
    fetched_at: datetime
    match_type: Literal["exact_name", "exact_alias", "fuzzy"] = "exact_name"
    confidence: float = Field(default=1.0, ge=0, le=1)
    requires_selection: bool = False
    image_url: str


class DataSourceStatus(BaseModel):
    source: str
    region: str
    version: str
    server_hash: str | None = None
    data_ver: int | None = None
    fetched_at: datetime
    source_url: str
    character_count: int
    material_count: int
    snapshot_count: int


class DropDatasetStatus(BaseModel):
    source: str
    version: str
    upstream_commit: str | None
    content_sha256: str
    fetched_at: datetime
    source_url: str
    license_status: str
    raw_distribution: bool
    material_count: int
    candidate_quest_count: int
    rate_count: int
    minimum_sample_runs: int


class SkillCostItem(BaseModel):
    skill_number: int
    from_level: int
    to_level: int
    material_id: int
    material_name: str
    amount: int


class InventoryItemInput(BaseModel):
    material_id: int
    quantity: int = Field(ge=0)


class InventoryReplaceRequest(BaseModel):
    user_id: str = "demo"
    mode: Literal["replace", "increment"] = "replace"
    items: list[InventoryItemInput]


class InventoryItemView(BaseModel):
    material_id: int
    material_name: str
    quantity: int


class SkillGoal(BaseModel):
    character_id: int
    skill_number: int = Field(ge=1, le=3)
    current_level: int = Field(ge=1, le=10)
    target_level: int = Field(ge=1, le=10)
    priority: int = Field(default=1, ge=1, le=100)

    @model_validator(mode="after")
    def target_must_not_be_lower(self) -> SkillGoal:
        if self.target_level < self.current_level:
            raise ValueError("target_level must be greater than or equal to current_level")
        return self


class MaterialGapRequest(BaseModel):
    user_id: str = "demo"
    goals: list[SkillGoal] = Field(min_length=1)


class MaterialGapItem(BaseModel):
    material_id: int
    material_game_id: int
    material_name: str
    image_url: str
    required: int
    owned: int
    gap: int


class MaterialGapResult(BaseModel):
    user_id: str
    goals: list[SkillGoal]
    items: list[MaterialGapItem]
    verified: bool = True
    verification_notes: list[str] = Field(default_factory=list)


class AgentQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    user_id: str = "demo"
    locale: str = "zh-CN"


class AgentQueryResponse(BaseModel):
    run_id: str
    answer: str
    tool_results: list[dict[str, Any]]
    event_count: int


class TrainingGoalDraft(BaseModel):
    character_query: str = Field(min_length=1, max_length=120)
    skill_number: int = Field(ge=1, le=3)
    current_level: int = Field(ge=1, le=10)
    target_level: int = Field(ge=1, le=10)

    @model_validator(mode="after")
    def target_must_not_be_lower(self) -> TrainingGoalDraft:
        if self.target_level < self.current_level:
            raise ValueError("target_level must be greater than or equal to current_level")
        return self


class TrainingGoalProposal(BaseModel):
    goals: list[TrainingGoalDraft] = Field(min_length=1, max_length=20)


class ResolvedTrainingGoal(BaseModel):
    character: CharacterSummary
    character_id: int
    skill_number: int
    current_level: int
    target_level: int


class GoalCandidateGroup(BaseModel):
    draft_index: int
    character_query: str
    skill_number: int
    current_level: int
    target_level: int
    candidates: list[CharacterSummary]


class GoalParseRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    user_id: str = "demo"
    locale: str = "zh-CN"


class GoalParseResponse(BaseModel):
    run_id: str
    drafts: list[TrainingGoalDraft]
    resolved_goals: list[ResolvedTrainingGoal]
    candidate_groups: list[GoalCandidateGroup]
    tool_steps: list[dict[str, Any]]
    explanation: str
    event_count: int


class PlanRequest(BaseModel):
    user_id: str = "demo"
    goals: list[SkillGoal] = Field(min_length=1)
    deadline: datetime | None = None
    current_ap: int = Field(default=0, ge=0)
    golden_apples: int = Field(default=0, ge=0)
    ap_per_apple: int = Field(default=142, ge=1)
    daily_minutes: int = Field(default=60, ge=1)
    minutes_per_run: int = Field(default=3, ge=1)
    max_candidates: int = Field(default=20, ge=1, le=50)
    planner_node_limit: int = Field(default=50_000, ge=1, le=500_000)
    planner_timeout_ms: int = Field(default=750, ge=10, le=5_000)


class FarmingStep(BaseModel):
    quest_id: int
    quest_name: str
    runs: int
    ap_cost: int
    expected_drops: dict[int, float]
    sample_runs: int
    image_url: str = ""


class PlanResult(BaseModel):
    plan_id: str
    run_id: str
    material_gap: MaterialGapResult
    steps: list[FarmingStep]
    total_ap: int
    available_ap: int
    completion_ratio: float
    status: Literal["complete", "partial", "no_verified_route"]
    dataset_version: str | None
    candidate_scope: str
    warnings: list[str] = Field(default_factory=list)
    verified: bool
    solver: str = "greedy-baseline"
    optimality: Literal[
        "local_optimal",
        "best_so_far",
        "feasible_baseline",
        "partial_baseline",
        "no_solution",
    ] = "feasible_baseline"
    planner_version: str = "p3b-v1"
    search_nodes: int = 0
    search_limit_hit: bool = False
    degraded: bool = False
    dataset_fetched_at: datetime | None = None
    dataset_source_url: str | None = None
    dataset_license_status: str | None = None
    minimum_sample_runs: int | None = None


class RagCitation(BaseModel):
    source_url: str
    title: str
    heading: str
    fetched_at: datetime
    excerpt: str


class RagAnswer(BaseModel):
    answer: str
    citations: list[RagCitation]
    route: Literal["rag", "structured", "mixed"]
