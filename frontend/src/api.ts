import type {
  Character,
  DataSourceStatus,
  DropDatasetStatus,
  GapResult,
  GoalParseResult,
  PlanResult,
  SkillGoal
} from "./types";

const baseUrl = import.meta.env.VITE_API_URL ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers
    }
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  dataStatus() {
    return request<DataSourceStatus>("/api/v1/data/status");
  },
  dropDatasetStatus() {
    return request<DropDatasetStatus>("/api/v1/data/drop-dataset");
  },
  parseGoals(query: string) {
    return request<GoalParseResult>("/api/v1/agent/parse-goals", {
      method: "POST",
      body: JSON.stringify({ query, user_id: "demo", locale: "zh-CN" })
    });
  },
  searchCharacters(query: string) {
    return request<Character[]>(
      `/api/v1/characters?query=${encodeURIComponent(query)}`
    );
  },
  replaceInventory(items: Array<{ material_id: number; quantity: number }>) {
    return request("/api/v1/account/inventory", {
      method: "PUT",
      body: JSON.stringify({ user_id: "demo", mode: "replace", items })
    });
  },
  calculateGap(goals: SkillGoal[]) {
    return request<GapResult>("/api/v1/calculations/material-gap", {
      method: "POST",
      body: JSON.stringify({ user_id: "demo", goals })
    });
  },
  createPlan(
    goals: SkillGoal[],
    currentAp: number,
    apples: number,
    deadline: string,
    dailyMinutes: number,
    minutesPerRun: number
  ) {
    return request<PlanResult>("/api/v1/plans", {
      method: "POST",
      body: JSON.stringify({
        user_id: "demo",
        goals,
        current_ap: currentAp,
        golden_apples: apples,
        deadline: deadline ? new Date(deadline).toISOString() : null,
        daily_minutes: dailyMinutes,
        minutes_per_run: minutesPerRun
      })
    });
  },
  trace(runId: string) {
    return request<{ run_id: string; events: Array<Record<string, unknown>> }>(
      `/api/v1/traces/${encodeURIComponent(runId)}`
    );
  },
  replay(runId: string) {
    return request<Record<string, unknown>>(
      `/api/v1/replays/${encodeURIComponent(runId)}`
    );
  }
};
