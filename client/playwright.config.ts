import { defineConfig, devices } from "@playwright/test";

const CI = Boolean(process.env.CI);
const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:5173";

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: true,
  // Shared Fusion IAM refreshes the same developer test designations during
  // sign-in. Serial browsers avoid a uniqueness race in that external IAM
  // service and keep the full cross-module suite deterministic.
  workers: 1,
  forbidOnly: CI,
  retries: CI ? 1 : 0,
  reporter: CI ? [["list"], ["html", { open: "never" }]] : [["list"]],
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  // The IAM and `make dev` must already be running; this only starts the client.
  webServer: {
    command: "npm run dev -- --port 5173 --strictPort",
    url: BASE_URL,
    reuseExistingServer: !CI,
    timeout: 60_000,
  },
});
