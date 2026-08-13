import { expect, test } from "@playwright/test";

async function signIn(page: import("@playwright/test").Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill("sunny@studiosunny.com");
  await page.getByLabel("Password").fill("SunnyHQ2026!");
  await page.getByRole("button", { name: /Sign in/i }).click();
  await expect(page).toHaveURL(/home/, { timeout: 20000 });
}

test("edit client name and archive it", async ({ page }) => {
  await signIn(page);

  const stamp = Date.now();
  const name = `Archive Probe ${stamp}`;
  const edited = `${name} Edited`;

  await page.goto("/clients/new");
  await page.getByLabel("Business name").fill(name);
  await page.getByRole("button", { name: /Create client/i }).click();
  await expect(page).toHaveURL(/\/clients\/[^/]+$/, { timeout: 20000 });
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible({ timeout: 20000 });

  await page.getByRole("button", { name: "Edit" }).click();
  await page.locator("form.panel input").first().fill(edited);
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByRole("heading", { level: 1, name: edited })).toBeVisible({ timeout: 15000 });

  await page.getByRole("button", { name: "Archive" }).click();
  await expect(page.getByRole("heading", { name: `Archive ${edited}?` })).toBeVisible();
  await page.getByRole("alertdialog").getByRole("button", { name: "Archive" }).click();

  await expect(page).toHaveURL(/\/clients\/?$/, { timeout: 15000 });
  await expect(page.getByText(edited, { exact: true })).toHaveCount(0);

  await page.getByRole("button", { name: "Archived" }).click();
  await expect(page.getByText(edited, { exact: true })).toBeVisible({ timeout: 15000 });
});
