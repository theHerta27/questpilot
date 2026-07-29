export interface Character {
  id: number;
  game_id: number;
  collection_no: number;
  name_zh_cn: string;
  name_ja?: string;
  rarity: number;
  class_name: string;
  aliases: string[];
  source: string;
  source_version: string;
  fetched_at: string;
  match_type: "exact_name" | "exact_alias" | "fuzzy";
  confidence: number;
  requires_selection: boolean;
  image_url: string;
}

export interface DataSourceStatus {
  source: string;
  region: string;
  version: string;
  server_hash: string | null;
  data_ver: number | null;
  fetched_at: string;
  source_url: string;
  character_count: number;
  material_count: number;
  snapshot_count: number;
}

export interface SkillGoal {
  character_id: number;
  skill_number: number;
  current_level: number;
  target_level: number;
}

export interface DropDatasetStatus {
  source: string;
  version: string;
  upstream_commit: string | null;
  content_sha256: string;
  fetched_at: string;
  source_url: string;
  license_status: string;
  raw_distribution: boolean;
  material_count: number;
  candidate_quest_count: number;
  rate_count: number;
  minimum_sample_runs: number;
}

export interface GapItem {
  material_id: number;
  material_game_id: number;
  material_name: string;
  image_url: string;
  required: number;
  owned: number;
  gap: number;
}

export interface GapResult {
  user_id: string;
  goals: SkillGoal[];
  items: GapItem[];
  verified: boolean;
  verification_notes: string[];
}

export interface PlanResult {
  plan_id: string;
  run_id: string;
  material_gap: GapResult;
  steps: Array<{
    quest_id: number;
    quest_name: string;
    runs: number;
    ap_cost: number;
    expected_drops: Record<string, number>;
    sample_runs: number;
    image_url: string;
  }>;
  total_ap: number;
  available_ap: number;
  completion_ratio: number;
  status: "complete" | "partial" | "no_verified_route";
  dataset_version: string | null;
  candidate_scope: string;
  warnings: string[];
  verified: boolean;
  solver: string;
  optimality: "local_optimal" | "best_so_far" | "feasible_baseline" | "partial_baseline" | "no_solution";
  planner_version: string;
  search_nodes: number;
  search_limit_hit: boolean;
  degraded: boolean;
  dataset_fetched_at: string | null;
  dataset_source_url: string | null;
  dataset_license_status: string | null;
  minimum_sample_runs: number | null;
}

export interface GoalParseResult {
  run_id: string;
  drafts: Array<{
    character_query: string;
    skill_number: number;
    current_level: number;
    target_level: number;
  }>;
  resolved_goals: Array<SkillGoal & { character: Character }>;
  candidate_groups: Array<{
    draft_index: number;
    character_query: string;
    skill_number: number;
    current_level: number;
    target_level: number;
    candidates: Character[];
  }>;
  tool_steps: Array<{ name: string; status: string; summary: string }>;
  explanation: string;
  event_count: number;
}
