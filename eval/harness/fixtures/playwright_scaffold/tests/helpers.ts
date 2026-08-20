import { Page, Browser, BrowserContext } from '@playwright/test';
import { BASE_URL, ACCOUNTS } from './constants';

export class LoginPage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto(`${BASE_URL}/login`);
  }

  async loginAs(role: keyof typeof ACCOUNTS): Promise<void> {
    const { username, password } = ACCOUNTS[role];
    await this.goto();
    await this.page.getByPlaceholder('请输入用户名').fill(username);
    await this.page.getByPlaceholder('请输入密码').fill(password);
    await Promise.all([
      this.page.waitForURL(/\/console/, { timeout: 15000 }),
      this.page.getByRole('button', { name: /登\s*录/ }).click(),
    ]);
  }
}

export async function createDualSession(
  browser: Browser,
  roleA: string,
  roleB: string,
): Promise<{ pageA: Page; pageB: Page; contextA: BrowserContext; contextB: BrowserContext }> {
  const contextA = await browser.newContext();
  const contextB = await browser.newContext();
  return {
    pageA: await contextA.newPage(),
    pageB: await contextB.newPage(),
    contextA,
    contextB,
  };
}
