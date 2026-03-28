import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  use: { baseURL: 'http://localhost:4200' },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
  webServer: {
    command: 'npx ng serve --port 4200',
    port: 4200,
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
