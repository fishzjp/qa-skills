import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  use: {
    baseURL: process.env.TEST_BASE_URL ?? 'http://127.0.0.1:8931',
    actionTimeout: 10_000,
    headless: true,
  },
});
