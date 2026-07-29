import type { Character, SkillGoal } from "./types";

export type GoalEntry = SkillGoal & { character: Character };

export function validateGoalLevels(currentLevel: number, targetLevel: number): void {
  if (
    !Number.isInteger(currentLevel) ||
    !Number.isInteger(targetLevel) ||
    currentLevel < 1 ||
    currentLevel > 10 ||
    targetLevel < 1 ||
    targetLevel > 10
  ) {
    throw new Error("技能等级必须是 1 到 10 之间的整数。");
  }
  if (targetLevel < currentLevel) {
    throw new Error("目标等级不能低于当前等级。");
  }
}

export function upsertGoalLastWins(
  goals: GoalEntry[],
  next: GoalEntry
): GoalEntry[] {
  validateGoalLevels(next.current_level, next.target_level);
  return [
    ...goals.filter(
      (item) =>
        item.character_id !== next.character_id ||
        item.skill_number !== next.skill_number
    ),
    next
  ];
}
