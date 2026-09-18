import { defineConfig, devices } from '@playwright/test';

// No hardcoded browser channel: 'channel: msedge' only exists on Windows and
// silently made this whole suite unrunnable everywhere else (Linux CI,
// containers). Playwright's own bundled Chromium is portable by default;
// PLAYWRIGHT_CHROMIUM_PATH lets a specific environment (e.g. a container
// with a pre-installed browser cache) point at its own binary instead of
// downloading one, without hardcoding that path for every other environment.
export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    ...devices['Desktop Chrome'],
    ...(process.env.PLAYWRIGHT_CHROMIUM_PATH
      ? { launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_PATH } }
      : {}),
  },
  webServer: {
    command: 'pnpm start -p 3000',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 120000,
  },
});
