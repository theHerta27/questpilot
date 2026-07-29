import { describe, expect, it } from "vitest";
import type { Character } from "./types";
import { upsertGoalLastWins, validateGoalLevels } from "./goalList";

const character: Character = {
  id: 7,
  game_id: 2007,
  collection_no: 254,
  name_zh_cn: "伊阿宋",
  rarity: 1,
  class_name: "Saber",
  aliases: [],
  source: "atlas_cn",
  source_version: "fixture",
  fetched_at: "2026-07-29T00:00:00Z",
  match_type: "exact_name",
  confidence: 1,
  requires_selection: false
};

describe("goal list", () => {
  it("fully replaces current and target levels with the last duplicate input", () => {
    const first = {
      character,
      character_id: character.id,
      skill_number: 1,
      current_level: 1,
      target_level: 6
    };
    const second = { ...first, current_level: 3, target_level: 5 };

    expect(upsertGoalLastWins(upsertGoalLastWins([], first), second)).toEqual([second]);
  });

  it.each([
    [0, 1],
    [1, 11],
    [5, 4],
    [1.5, 6]
  ])("rejects invalid level range %s -> %s", (current, target) => {
    expect(() => validateGoalLevels(current, target)).toThrow();
  });
});
