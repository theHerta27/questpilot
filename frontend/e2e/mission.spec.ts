import { expect, test } from "@playwright/test";

test("mission workspace is usable at desktop and mobile widths", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "QuestPilot" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "工作台视图" })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("button", { name: "检索" })).toBeVisible();
});

test("the last duplicate goal fully replaces the earlier level range", async ({ page }) => {
  await page.route("**/api/v1/data/status", (route) =>
    route.fulfill({
      json: {
        source: "atlas_cn",
        region: "CN",
        version: "fixture",
        server_hash: null,
        data_ver: 1,
        fetched_at: "2026-07-29T00:00:00Z",
        source_url: "https://api.atlasacademy.io",
        character_count: 1,
        material_count: 1,
        snapshot_count: 1
      }
    })
  );
  await page.route("**/api/v1/characters?query=*", (route) =>
    route.fulfill({
      json: [
        {
          id: 7,
          game_id: 2007,
          collection_no: 254,
          name_zh_cn: "伊阿宋",
          name_ja: "イアソン",
          rarity: 1,
          class_name: "Saber",
          aliases: ["Jason"],
          source: "atlas_cn",
          source_version: "fixture",
          fetched_at: "2026-07-29T00:00:00Z",
          match_type: "exact_name",
          confidence: 1,
          requires_selection: false,
          image_url: "/api/v1/assets/characters/254.png"
        }
      ]
    })
  );

  await page.goto("/");
  await page.getByLabel("角色名称").fill("伊阿宋");
  await page.getByRole("button", { name: "检索" }).click();

  await page.getByLabel("当前等级").fill("1");
  await page.getByLabel("目标等级").fill("6");
  await page.getByRole("button", { name: "加入目标清单" }).click();
  await expect(page.getByText("技能 1 · 1 → 6")).toBeVisible();

  await page.getByLabel("当前等级").fill("3");
  await page.getByLabel("目标等级").fill("5");
  await page.getByRole("button", { name: "加入目标清单" }).click();

  await expect(page.getByText("已编成 1 项培养目标")).toBeVisible();
  await expect(page.getByText("技能 1 · 3 → 5")).toBeVisible();
  await expect(page.getByText("技能 1 · 1 → 6")).toHaveCount(0);
});

test("natural-language multi-goal flow reaches a verified route and trace", async ({ page }) => {
  const jason = {
    id: 7,
    game_id: 2007,
    collection_no: 254,
    name_zh_cn: "伊阿宋",
    name_ja: "イアソン",
    rarity: 1,
    class_name: "Saber",
    aliases: ["杰森"],
    source: "atlas",
    source_version: "fixture",
    fetched_at: "2026-07-29T00:00:00Z",
    match_type: "exact_alias",
    confidence: 1,
    requires_selection: false,
    image_url: "/api/v1/assets/characters/254.png"
  };
  const osakabehime = {
    ...jason,
    id: 8,
    game_id: 2008,
    collection_no: 262,
    name_zh_cn: "刑部姬",
    name_ja: "刑部姫",
    rarity: 4,
    class_name: "Archer",
    aliases: ["弓刑部"],
    image_url: "/api/v1/assets/characters/262.png"
  };
  await page.route("**/api/v1/data/status", (route) =>
    route.fulfill({
      json: {
        source: "Atlas Academy",
        region: "CN",
        version: "fixture",
        server_hash: null,
        data_ver: 967,
        fetched_at: "2026-07-29T00:00:00Z",
        source_url: "https://api.atlasacademy.io/",
        character_count: 3,
        material_count: 4,
        snapshot_count: 1
      }
    })
  );
  await page.route("**/api/v1/data/drop-dataset", (route) =>
    route.fulfill({
      json: {
        source: "Community observations",
        version: "1779642278",
        upstream_commit: "a".repeat(40),
        content_sha256: "e".repeat(64),
        fetched_at: "2026-07-29T00:00:00Z",
        source_url: "https://example.test/pinned",
        license_status: "unverified-local-only",
        raw_distribution: false,
        material_count: 4,
        candidate_quest_count: 13,
        rate_count: 14,
        minimum_sample_runs: 1084
      }
    })
  );
  await page.route("**/api/v1/agent/parse-goals", (route) =>
    route.fulfill({
      json: {
        run_id: "parse-run",
        drafts: [],
        resolved_goals: [
          { character: jason, character_id: 7, skill_number: 1, current_level: 1, target_level: 6 },
          { character: osakabehime, character_id: 8, skill_number: 1, current_level: 4, target_level: 5 },
          { character: jason, character_id: 7, skill_number: 1, current_level: 8, target_level: 9 }
        ],
        candidate_groups: [],
        tool_steps: [
          { name: "propose_training_goals", status: "completed", summary: "解析 3 个目标" },
          { name: "search_character", status: "completed", summary: "杰森：1 个候选" },
          { name: "search_character", status: "completed", summary: "弓刑部：1 个候选" }
        ],
        explanation: "模型解析了 3 个培养目标；3 个已精确解析。",
        event_count: 11
      }
    })
  );
  await page.route("**/api/v1/account/inventory", (route) => route.fulfill({ json: [] }));
  const gap = {
    user_id: "demo",
    goals: [
      { character_id: 8, skill_number: 1, current_level: 4, target_level: 5 },
      { character_id: 7, skill_number: 1, current_level: 8, target_level: 9 }
    ],
    items: [
      {
        material_id: 31,
        material_game_id: 6537,
        material_name: "巨人的戒指",
        image_url: "/api/v1/assets/materials/6537.png",
        required: 6,
        owned: 0,
        gap: 6
      },
      {
        material_id: 32,
        material_game_id: 6542,
        material_name: "真理之卵",
        image_url: "/api/v1/assets/materials/6542.png",
        required: 4,
        owned: 0,
        gap: 4
      }
    ],
    verified: true,
    verification_notes: ["后一次输入完整覆盖"]
  };
  await page.route("**/api/v1/calculations/material-gap", (route) =>
    route.fulfill({ json: gap })
  );
  await page.route("**/api/v1/plans", (route) =>
    route.fulfill({
      json: {
        plan_id: "plan-1",
        run_id: "plan-run",
        material_gap: gap,
        steps: [
          {
            quest_id: 93030303,
            quest_name: "巨人的花园 · 炎与冰的狭缝间",
            runs: 14,
            ap_cost: 20,
            expected_drops: { "31": 6.2 },
            sample_runs: 9880,
            image_url: "/api/v1/assets/quests/93030303.png"
          }
        ],
        total_ap: 280,
        available_ap: 424,
        completion_ratio: 1,
        status: "complete",
        dataset_version: "1779642278",
        candidate_scope: "13 个版本固定的永久自由关卡",
        warnings: ["已在固定候选集内证明局部最优。"],
        verified: true,
        solver: "bounded-branch-and-bound",
        optimality: "local_optimal",
        planner_version: "p3b-v1",
        search_nodes: 8411,
        search_limit_hit: false,
        degraded: false,
        dataset_fetched_at: "2026-07-29T00:00:00Z",
        dataset_source_url: "https://example.test/pinned",
        dataset_license_status: "unverified-local-only",
        minimum_sample_runs: 1084
      }
    })
  );
  await page.route("**/api/v1/traces/plan-run", (route) =>
    route.fulfill({
      json: {
        run_id: "plan-run",
        events: [{ sequence: 1, event_type: "run.started" }]
      }
    })
  );

  await page.goto("/");
  await page.getByRole("button", { name: "解析并加入清单" }).click();
  const manifest = page.getByLabel("培养目标清单");
  await expect(manifest.getByText("已编成 2 项培养目标")).toBeVisible();
  await expect(manifest.getByText("技能 1 · 8 → 9")).toBeVisible();
  await expect(manifest.getByText("技能 1 · 1 → 6")).toHaveCount(0);

  await page.getByRole("button", { name: "合并计算材料缺口" }).click();
  await expect(page.getByText("巨人的戒指", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "生成受约束路线" }).click();
  await expect(page.getByText("固定候选集局部最优")).toBeVisible();
  await expect(page.getByText("巨人的花园 · 炎与冰的狭缝间")).toBeVisible();

  await page.getByRole("button", { name: "查看本次 Trace" }).click();
  await expect(page.getByText(/run.started/)).toBeVisible();
});
