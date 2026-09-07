```typescript
// tests/pages/ProjectListPage.ts
import { Page, Locator } from '@playwright/test';

export class ProjectListPage {
  readonly page: Page;
  readonly newProjectButton: Locator;
  readonly searchInput: Locator;
  readonly projectCards: Locator;

  constructor(page: Page) {
    this.page = page;
    this.newProjectButton = page.getByRole('button', { name: '新建项目' });
    this.searchInput = page.getByPlaceholder('搜索项目');
    this.projectCards = page.locator('.project-card');
  }

  async goto() {
    await this.page.goto('/console/projects');
    await this.waitForListLoaded();
  }

  async waitForListLoaded() {
    await Promise.all([
      this.page.waitForResponse(
        (resp) => resp.url().includes('/api/projects') && resp.status() === 200,
      ),
      this.page.waitForSelector('.project-card'),
    ]);
  }

  async createProject(name: string) {
    await this.newProjectButton.click();
    await this.page.getByPlaceholder('请输入项目名称').fill(name);
    await this.page.getByRole('button', { name: '确定' }).click();
    await this.waitForListLoaded();
  }

  async searchProject(query: string) {
    await this.searchInput.fill(query);
    await this.page.keyboard.press('Enter');
    await this.waitForListLoaded();
  }

  async deleteProject(name: string) {
    const card = this.projectCards.filter({ hasText: name });
    await card.getByRole('button', { name: '更多' }).click();
    await this.page
      .locator('.el-dropdown-menu__item:has-text("删除")')
      .waitFor({ state: 'visible' });
    await this.page.locator('.el-dropdown-menu__item:has-text("删除")').click();
    await this.page
      .locator('.el-dialog .el-button--primary:has-text("删除")')
      .click();
    await this.waitForListLoaded();
  }

  async isProjectVisible(name: string): Promise<boolean> {
    return (await this.projectCards.filter({ hasText: name }).count()) > 0;
  }
}
```

```typescript
// tests/projects.spec.ts
import { test, expect, Page } from '@playwright/test';
import { ProjectListPage } from './pages/ProjectListPage';
import { LoginPage } from './helpers';

test.describe.serial('项目管理', () => {
  let page: Page;
  let projectListPage: ProjectListPage;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    const loginPage = new LoginPage(page);
    await loginPage.loginAs('admin');
    projectListPage = new ProjectListPage(page);
    await projectListPage.goto();
  });

  test('TC-01-01 创建项目 [P0] (SMOKE-1)', async () => {
    await projectListPage.createProject('自动化测试项目-0721');
    expect(await projectListPage.isProjectVisible('自动化测试项目-0721')).toBeTruthy();
  });

  test('TC-01-02 搜索项目 [P1]', async () => {
    await projectListPage.searchProject('自动化测试项目-0721');
    await expect(projectListPage.projectCards).toHaveCount(1);
    await expect(projectListPage.projectCards.first()).toHaveText('自动化测试项目-0721');
  });

  test('TC-01-03 删除项目 [P1]', async () => {
    await projectListPage.deleteProject('自动化测试项目-0721');
    expect(await projectListPage.isProjectVisible('自动化测试项目-0721')).toBeFalsy();
    // 刷新页面后仍不存在
    await projectListPage.goto();
    expect(await projectListPage.isProjectVisible('自动化测试项目-0721')).toBeFalsy();
  });

  test.afterAll(async () => {
    await page.close();
  });
});
```