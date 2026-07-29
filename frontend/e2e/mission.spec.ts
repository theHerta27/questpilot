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
          requires_selection: false
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
