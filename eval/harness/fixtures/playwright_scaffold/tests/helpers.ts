import { Page, Browser, BrowserContext } from '@playwright/test';
import { ACCOUNTS } from './constants';

export class LoginPage {
  constructor(private page: Page) {}

  async loginAs(role: keyof typeof ACCOUNTS): Promise<void> {
    await this.page.goto('/login');
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
