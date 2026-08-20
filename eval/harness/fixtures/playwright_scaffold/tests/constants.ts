export const BASE_URL = process.env.TEST_BASE_URL ?? 'https://console.example.test';
export const ACCOUNTS = {
  admin: { username: process.env.ADMIN_USER ?? 'admin', password: process.env.ADMIN_PASS ?? 'pass' },
} as const;
