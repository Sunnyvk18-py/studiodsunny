import { expect, test } from "@playwright/test";

test("login page renders and signs in", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: /Enter HQ/i })).toBeVisible();
  await page.getByLabel("Email").fill("sunny@studiosunny.com");
  await page.getByLabel("Password").fill("SunnyHQ2026!");
  await page.getByRole("button", { name: /Sign in/i }).click();
  await expect(page).toHaveURL(/home/, { timeout: 20000 });
});
