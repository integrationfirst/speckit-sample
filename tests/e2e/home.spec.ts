import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("home page loads and has no WCAG 2.1 AA violations", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle("speckit-sample");

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();

  expect(results.violations).toEqual([]);
});
