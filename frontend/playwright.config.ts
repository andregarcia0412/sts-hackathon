import { defineConfig, devices } from "@playwright/test";

/*
 * End-to-end tests (e2e/): user journeys in a real browser against the dev
 * server with the mock data. Every test gets a fresh browser context, so the
 * mock database (localStorage) starts from the seed each time.
 */
const PORT = 5180;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  // The graph is heavy: too many browsers at once make typing and animations crawl
  workers: process.env.CI ? 2 : 4,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: `http://localhost:${PORT}`,
    locale: "pt-BR",
    timezoneId: "America/Fortaleza",
    viewport: { width: 1440, height: 900 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
  webServer: {
    command: `npm run dev -- --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    // Vite echoes browser warnings (e.g. ResizeObserver) here: too noisy for test output
    stdout: "ignore",
    stderr: "ignore",
  },
});
