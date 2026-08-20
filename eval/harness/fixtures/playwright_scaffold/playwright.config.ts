import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  // 串行单 worker：测试共享同一个 mock 应用状态，并行会互相干扰
  workers: 1,
  fullyParallel: false,
  use: {
    baseURL: process.env.TEST_BASE_URL ?? 'http://127.0.0.1:8931',
    actionTimeout: 10_000,
    headless: true,
  },
});
