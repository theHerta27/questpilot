export interface Character {
  id: number;
  game_id: number;
  collection_no: number;
  name_zh_cn: string;
  name_ja?: string;
  rarity: number;
  class_name: string;
  aliases: string[];
}

export interface SkillGoal {
  character_id: number;
  skill_number: number;
  current_level: number;
  target_level: number;
}

export interface GapItem {
  material_id: number;
  material_name: string;
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
  }>;
  total_ap: number;
  available_ap: number;
  completion_ratio: number;
  status: "complete" | "partial" | "no_verified_route";
  dataset_version: string | null;
  candidate_scope: string;
  warnings: string[];
  verified: boolean;
}
