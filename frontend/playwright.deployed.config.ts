import { defineConfig } from '@playwright/test';

/**
 * Playwright config for running E2E tests against deployed services.
 *
 * Usage:
 *   npx playwright test --config playwright.deployed.config.ts
 *
 * Requires env vars (or defaults to current deployed URLs):
 *   DEPLOYED_FRONTEND_URL - Vercel frontend URL
 *   DEPLOYED_API_URL      - Railway backend URL
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.DEPLOYED_FRONTEND_URL || 'https://survey-mu-dun.vercel.app',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  // No webServer — tests run against already-deployed services
});
