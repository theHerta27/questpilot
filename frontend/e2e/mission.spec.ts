import { expect, test } from "@playwright/test";

test("mission workspace is usable at desktop and mobile widths", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "QuestPilot" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "工作台视图" })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("button", { name: "检索" })).toBeVisible();
});
