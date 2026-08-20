export const BASE_URL = process.env.TEST_BASE_URL ?? 'http://127.0.0.1:8931';
export const ACCOUNTS = {
  admin: { username: process.env.ADMIN_USER ?? 'admin', password: process.env.ADMIN_PASS ?? 'pass' },
} as const;
