import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

// G4d regression: /specimen had zero Axe coverage in the whole suite before
// this test existed -- the only real route with no a11y check at all, which
// is why a real axe-core Playwright pass against the live backend (not MSW)
// found a genuine WCAG 2.1.1 (keyboard) violation here: the horizontally
// scrollable findings table had no keyboard access (scrollable-region-focusable).
// Fixed in src/app/specimen/page.tsx by adding tabIndex={0} + role="region" +
// aria-label to the scroll container. This test pins that fix in place.
test.describe('Screen: Design System Specimen (/specimen) E2E Verification', () => {
  test('renders specimen page and passes Axe a11y in Dark & Light themes', async ({ page }) => {
    await page.goto('/specimen');
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('heading', { name: /CIPHER OBSERVATORY DESIGN SYSTEM/i })).toBeVisible();

    const darkAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(darkAxe.violations, JSON.stringify(darkAxe.violations, null, 2)).toHaveLength(0);

    const themeBtn = page.getByLabel('Toggle visual theme');
    await themeBtn.click();
    await page.waitForTimeout(200);

    const lightAxe = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze();
    expect(lightAxe.violations, JSON.stringify(lightAxe.violations, null, 2)).toHaveLength(0);

    await themeBtn.click();
  });
});
