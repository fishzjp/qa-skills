tests/pages/ProjectsPage.ts
```typescript
import { Page, Locator, expect } from '@playwright/test';
import { BASE_URL } from '../constants';

export class ProjectsPage {
  readonly page: Page;
  readonly createProjectButton: Locator;
  readonly searchInput: Locator;
  readonly projectCards: Locator;
  readonly projectNameInput: Locator;
  readonly confirmCreateButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.createProjectButton = page.getByRole('button', { name: '新建项目' });
    this.searchInput = page.getByPlaceholder('搜索项目');
    this.projectCards = page.locator('.project-card');
    this.projectNameInput = page.getByPlaceholder('请输入项目名称');
    this.confirmCreateButton = page.getByRole('dialog').getByRole('button', { name: '确定' });
  }

  async goto(): Promise<void> {
    await Promise.all([
      this.page.waitForResponse(
        (response) =>
          response.url().includes('/api/projects') &&
          response.request().method() === 'GET' &&
          response.ok()
      ),
      this.page.goto(`${BASE_URL}/console/projects`),
    ]);
    await this.waitForListLoaded();
  }

  async waitForListLoaded(): Promise<void> {
    await this.page.waitForLoadState('networkidle');
    await this.projectCards.first().waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});
  }

  getProjectCardByName(name: string): Locator {
    return this.projectCards.filter({ has: this.page.getByText(name, { exact: true }) });
  }

  async createProject(name: string): Promise<void> {
    await this.createProjectButton.click();
    await this.projectNameInput.waitFor();
    await this.projectNameInput.fill(name);

    await Promise.all([
      this.page.waitForResponse(
        (response) =>
          response.url().includes('/api/projects') &&
          response.request().method() === 'POST' &&
          response.ok()
      ),
      this.confirmCreateButton.click(),
    ]);

    await this.waitForListLoaded();
  }

  async searchProjects(keyword: string): Promise<void> {
    await this.searchInput.fill(keyword);

    await Promise.all([
      this.page.waitForResponse(
        (response) =>
          response.url().includes('/api/projects') &&
          response.request().method() === 'GET' &&
          response.ok()
      ),
      this.searchInput.press('Enter'),
    ]);

    await this.waitForListLoaded();
  }

  async expectOnlyProjectVisible(name: string): Promise<void> {
    await expect(this.projectCards).toHaveCount(1);
    await expect(this.projectCards.first()).toContainText(name);
  }

  async deleteProject(name: string): Promise<void> {
    const card = this.getProjectCardByName(name).first();
    await expect(card).toBeVisible();

    await card.getByRole('button', { name: '更多' }).click();
    const deleteMenuItem = this.page.getByRole('menuitem', { name: '删除' });
    await expect(deleteMenuItem).toBeVisible();
    await deleteMenuItem.click();

    const confirmDialog = this.page.getByRole('dialog');
    await expect(confirmDialog).toBeVisible();

    await Promise.all([
      this.page.waitForResponse(
        (response) =>
          response.url().includes('/api/projects') &&
          response.request().method() === 'DELETE' &&
          response.ok()
      ),
      confirmDialog.getByRole('button', { name: '删除' }).click(),
    ]);

    await this.waitForListLoaded();
  }

  async deleteProjectIfExists(name: string): Promise<void> {
    await this.searchProjects(name);

    while ((await this.getProjectCardByName(name).count()) > 0) {
      await this.deleteProject(name);
      await this.searchProjects(name);
    }

    await this.goto();
  }

  async refresh(): Promise<void> {
    await Promise.all([
      this.page.waitForResponse(
        (response) =>
          response.url().includes('/api/projects') &&
          response.request().method() === 'GET' &&
          response.ok()
      ),
      this.page.reload(),
    ]);

    await this.waitForListLoaded();
  }
}
```

tests/specs/project-management.spec.ts
```typescript
import { test, expect } from '@playwright/test';
import { LoginPage } from '../helpers';
import { ProjectsPage } from '../pages/ProjectsPage';

const PROJECT_NAME = '自动化测试项目-0721';

test.describe.serial('项目管理', () => {
  let projectsPage: ProjectsPage;

  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    const loginPage = new LoginPage(page);
    await loginPage.loginAs('admin');

    projectsPage = new ProjectsPage(page);
    await projectsPage.goto();
    await projectsPage.deleteProjectIfExists(PROJECT_NAME);
  });

  test.afterAll(async () => {
    if (!projectsPage) return;

    try {
      await projectsPage.deleteProjectIfExists(PROJECT_NAME);
    } catch {
      // 忽略清理失败，避免影响用例结果收集
    }

    await projectsPage.page.close();
  });

  test('TC-01-01 创建项目 [P0] SMOKE-1', async () => {
    await projectsPage.createProject(PROJECT_NAME);

    await expect(projectsPage.getProjectCardByName(PROJECT_NAME).first()).toBeVisible();
  });

  test('TC-01-02 搜索项目 [P1]', async () => {
    await projectsPage.searchProjects(PROJECT_NAME);

    await projectsPage.expectOnlyProjectVisible(PROJECT_NAME);
  });

  test('TC-01-03 删除项目 [P1]', async () => {
    // 重置搜索状态，确保删除操作在完整列表中生效
    await projectsPage.goto();

    await projectsPage.deleteProject(PROJECT_NAME);

    await expect(projectsPage.getProjectCardByName(PROJECT_NAME)).toHaveCount(0);

    await projectsPage.refresh();

    await expect(projectsPage.getProjectCardByName(PROJECT_NAME)).toHaveCount(0);
  });
});
```