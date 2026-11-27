import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

const WELCOME_TEXT = /foundation for upcoming features/;

async function expectLandmarksVisibleWithoutHorizontalScroll(page: Page) {
  await page.goto("/");

  const banner = page.getByRole("banner");
  await expect(banner).toBeVisible();
  await expect(banner).toContainText("speckit-sample");

  const main = page.getByRole("main");
  await expect(main).toBeVisible();
  await expect(main.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(main.getByText(WELCOME_TEXT)).toBeVisible();

  await expect(page.getByRole("contentinfo")).toBeVisible();

  const hasNoHorizontalScroll = await page.evaluate(
    () => document.documentElement.scrollWidth <= window.innerWidth,
  );
  expect(hasNoHorizontalScroll).toBe(true);
}

test("mobile 320px", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 640 });
  await expectLandmarksVisibleWithoutHorizontalScroll(page);
});

test("desktop 1280px", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await expectLandmarksVisibleWithoutHorizontalScroll(page);
});

test("has no WCAG 2.1 AA violations", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle("speckit-sample");

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();

  expect(results.violations).toEqual([]);
});

test("no focus trap", async ({ page }) => {
  await page.goto("/");

  const focusedElements: string[] = [];
  for (let i = 0; i < 5; i++) {
    await page.keyboard.press("Tab");
    focusedElements.push(
      await page.evaluate(() => {
        const el = document.activeElement;
        if (el === null || el === document.body) {
          return "outside-page";
        }
        return el.outerHTML;
      }),
    );
  }

  // Focus must never stay stuck on the same element inside the page.
  for (let i = 1; i < focusedElements.length; i++) {
    const previous = focusedElements[i - 1];
    const current = focusedElements[i];
    if (current !== "outside-page") {
      expect(current).not.toBe(previous);
    }
  }

  await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
});
