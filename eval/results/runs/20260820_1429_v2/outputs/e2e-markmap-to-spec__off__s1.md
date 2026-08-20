```typescript
// tests/pages/ProjectsPage.ts
import { expect, Locator, Page, Response } from '@playwright/test';
import { BASE_URL } from '../constants';

export class ProjectsPage {
  readonly page: Page;
  readonly projectsUrl: string;
  readonly newProjectButton: Locator;
  readonly searchInput: Locator;
  readonly projectCards: Locator;
  readonly projectNameInput: Locator;
  readonly confirmCreateButton: Locator;
  readonly deleteMenuItem: Locator;
  readonly confirmDialog: Locator;
  readonly confirmDeleteButton: Locator;

  private readonly isProjectsResponse = (resp: Response) =>
    resp.url().includes('/api/projects') && resp.request().method() === 'GET';

  constructor(page: Page) {
    this.page = page;
    this.projectsUrl = `${BASE_URL}/console/projects`;
    this.newProjectButton = page.getByRole('button', { name: '新建项目' });
    this.searchInput = page.getByPlaceholder('搜索项目');
    this.projectCards = page.locator('.project-card');
    this.projectNameInput = page.getByPlaceholder('请输入项目名称');
    this.confirmCreateButton = page.getByRole('button', { name: '确定' });
    this.deleteMenuItem = page.getByRole('menuitem', { name: '删除' });
    this.confirmDialog = page
      .locator('[role="dialog"], .el-dialog, .ant-modal')
      .filter({ hasText: '删除' })
      .last();
    this.confirmDeleteButton = this.confirmDialog.getByRole('button', { name: '删除' });
  }

  async goto(): Promise<void> {
    const responsePromise = this.page.waitForResponse(this.isProjectsResponse);
    await this.page.goto(this.projectsUrl);
    await responsePromise;
    await this.page.waitForLoadState('networkidle');
  }

  private async waitForProjectsListSettled(): Promise<void> {
    await this.page.waitForResponse(this.isProjectsResponse);
    await this.page.waitForLoadState('networkidle');
  }

  async createProject(name: string): Promise<void> {
    const settled = this.waitForProjectsListSettled();
    await this.newProjectButton.click();
    await this.projectNameInput.fill(name);
    await this.confirmCreateButton.click();
    await settled;
  }

  cardByName(name: string): Locator {
    return this.projectCards.filter({ hasText: name });
  }

  async searchProjects(keyword: string): Promise<void> {
    const settled = this.waitForProjectsListSettled();
    await this.searchInput.fill(keyword);
    await this.searchInput.press('Enter');
    await settled;
  }

  async clearSearch(): Promise<void> {
    await this.goto();
  }

  async ensureProjectDoesNotExist(name: string): Promise<void> {
    await this.searchProjects(name);
    while ((await this.cardByName(name).count()) > 0) {
      await this.deleteProjectByName(name);
    }
    await this.clearSearch();
  }

  async deleteProjectByName(name: string): Promise<void> {
    const card = this.cardByName(name).first();
    await expect(card).toBeVisible();
    await card.getByRole('button', { name: '更多' }).click();
    await this.deleteMenuItem.click();
    await expect(this.confirmDialog).toBeVisible();
    const settled = this.waitForProjectsListSettled();
    await this.confirmDeleteButton.click();
    await settled;
  }

  async reload(): Promise<void> {
    const settled = this.waitForProjectsListSettled();
    await this.page.reload();
    await settled;
  }
}
```

```typescript
// tests/projects.spec.ts
import { expect, test } from '@playwright/test';
import { LoginPage } from '../helpers';
import { ProjectsPage } from '../pages/ProjectsPage';

const PROJECT_NAME = '自动化测试项目-0721';

test.describe.serial('项目管理 - TC-01', () => {
  test.beforeEach(async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.loginAs('admin');
    const projectsPage = new ProjectsPage(page);
    await projectsPage.goto();
  });

  test('TC-01-01 创建项目 [P0] (SMOKE-1)', async ({ page }) => {
    const projectsPage = new ProjectsPage(page);

    await projectsPage.ensureProjectDoesNotExist(PROJECT_NAME);
    await projectsPage.createProject(PROJECT_NAME);

    await expect(projectsPage.cardByName(PROJECT_NAME)).toBeVisible();
  });

  test('TC-01-02 搜索项目 [P1]', async ({ page }) => {
    const projectsPage = new ProjectsPage(page);

    await projectsPage.searchProjects(PROJECT_NAME);

    await expect(projectsPage.projectCards).toHaveCount(1);
    await expect(projectsPage.cardByName(PROJECT_NAME)).toBeVisible();
  });

  test('TC-01-03 删除项目 [P1]', async ({ page }) => {
    const projectsPage = new ProjectsPage(page);

    await expect(projectsPage.cardByName(PROJECT_NAME)).toBeVisible();

    await projectsPage.deleteProjectByName(PROJECT_NAME);

    await expect(projectsPage.cardByName(PROJECT_NAME)).toHaveCount(0);

    await projectsPage.reload();
    await expect(projectsPage.cardByName(PROJECT_NAME)).toHaveCount(0);
  });

  /*
   * 待澄清：
   * 1. 项目名称是否需要按运行追加时间戳以避免历史脏数据；当前按手动用例固定为"自动化测试项目-0721"，并在 TC-01-01 前通过 UI 清理同名项目。
   * 2. 「更多」菜单项与删除确认弹窗的 role/class 未明确；当前假设菜单项 role 为 menuitem、确认弹窗为 dialog/el-dialog/ant-modal。
   * 3. 是否允许通过后端 API 进行数据准备/清理；当前未提供 API 细节，故全部走 UI。
   * 4. 登录态是否可跨用例复用；当前每个用例独立登录并进入「控制台 -> 项目」页以保证隔离。
   */
});
```