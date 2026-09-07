现在，我将为你编写完整的 Playwright 自动化测试代码，包含 Page Object 和测试 spec 文件，严格遵循独立性、断言强度和清理规范。

先创建 Page Object 文件，用于封装所有项目页面的交互；再创建 spec 文件，包含三个独立测试用例，每个用例自建数据并自清理，搜索测试额外创建不匹配数据以增强断言区分度；删除测试增加持久化验证。

```typescript
// tests/pages/projects.page.ts
import { Page, Locator, expect } from '@playwright/test';
import { BASE_URL } from '../constants';

export class ProjectsPage {
  readonly page: Page;
  readonly newProjectButton: Locator;
  readonly projectNameInput: Locator;
  readonly confirmButton: Locator;
  readonly searchInput: Locator;
  readonly projectCards: Locator;

  constructor(page: Page) {
    this.page = page;
    this.newProjectButton = page.getByRole('button', { name: '新建项目' });
    this.projectNameInput = page.getByPlaceholder('请输入项目名称');
    this.confirmButton = page.getByRole('button', { name: '确定' });
    this.searchInput = page.getByPlaceholder('搜索项目');
    this.projectCards = page.locator('.project-card');
  }

  async goto() {
    await this.page.goto(`${BASE_URL}/console/projects`);
    // 等待列表加载完成：搜索框可见表明页面基本渲染
    await this.searchInput.waitFor({ state: 'visible', timeout: 15000 });
    // 等待网络请求稳定，后续操作依赖 API 完成
    await this.page.waitForLoadState('networkidle');
  }

  async createProject(name: string) {
    await this.newProjectButton.click();
    await this.projectNameInput.click();
    await this.projectNameInput.fill(name);
    await this.confirmButton.click();
    // 等待新建的项目卡片出现
    await expect(this.getProjectCardByName(name)).toBeVisible({ timeout: 10000 });
  }

  async deleteProject(name: string) {
    const card = this.getProjectCardByName(name);
    // 展开卡片右下角「更多」菜单
    const moreButton = card.getByRole('button', { name: '更多' });
    await moreButton.click();
    // 点击菜单中的「删除」
    const deleteMenuItem = this.page.getByRole('menuitem', { name: '删除' });
    await deleteMenuItem.click();
    // 确认弹窗
    const deleteConfirmButton = this.page.getByRole('button', { name: '删除' });
    await deleteConfirmButton.click();
    // 等待卡片消失
    await expect(card).not.toBeVisible({ timeout: 10000 });
  }

  getProjectCardByName(name: string): Locator {
    return this.projectCards.filter({ hasText: name });
  }

  async searchProject(query: string) {
    await this.searchInput.click();
    await this.searchInput.fill(query);
    // 注册搜索 API 响应等待，确保后端返回后才进行断言
    const responsePromise = this.page.waitForResponse(
      resp => resp.url().includes('/api/projects') && resp.request().method() === 'GET',
      { timeout: 15000 }
    );
    await this.page.keyboard.press('Enter');
    await responsePromise;
  }
}
```

```typescript
// tests/01-project-management.spec.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from './helpers';
import { ProjectsPage } from './pages/projects.page';

test.describe('项目管理', () => {
  let projectsPage: ProjectsPage;
  const createdProjectNames: string[] = [];

  test.beforeEach(async ({ page }) => {
    // 登录后进入项目页
    const loginPage = new LoginPage(page);
    await loginPage.loginAs('admin');
    projectsPage = new ProjectsPage(page);
    await projectsPage.goto();
    // 清空上一个测试留下的名称列表
    createdProjectNames.length = 0;
  });

  test.afterEach(async () => {
    // 清理所有在本测试中创建的项目，确保不影响后续测试
    for (const name of createdProjectNames) {
      try {
        // 项目可能已被删除（如 TC-01-03），catch 忽略
        await projectsPage.deleteProject(name);
      } catch {
        // 忽略删除失败，可能已不存在
      }
    }
  });

  test('TC-01-01: 创建项目', async () => {
    const projectName = `自动化测试项目-${Date.now()}`;
    createdProjectNames.push(projectName);

    await projectsPage.createProject(projectName);

    // 断言：列表出现名称为 projectName 的卡片
    await expect(projectsPage.getProjectCardByName(projectName)).toBeVisible();
  });

  test('TC-01-02: 搜索项目', async () => {
    // 前置：创建一条匹配搜索词和一条不匹配的数据，确保断言有区分度
    const matchingName = `自动化测试项目-${Date.now()}`;
    const otherName = `其他项目-${Date.now()}`;
    createdProjectNames.push(matchingName, otherName);

    await projectsPage.createProject(matchingName);
    await projectsPage.createProject(otherName);

    // 执行搜索（回车触发）
    await projectsPage.searchProject(matchingName);

    // 断言：搜索后仅显示匹配项目，不匹配项目不出现
    await expect(projectsPage.getProjectCardByName(matchingName)).toBeVisible();
    await expect(projectsPage.getProjectCardByName(otherName)).toHaveCount(0);
  });

  test('TC-01-03: 删除项目', async () => {
    // 前置：创建一个项目
    const projectName = `自动化测试项目-${Date.now()}`;
    createdProjectNames.push(projectName);

    await projectsPage.createProject(projectName);

    // 执行删除操作
    await projectsPage.deleteProject(projectName);

    // 断言：列表不再显示该项目
    await expect(projectsPage.getProjectCardByName(projectName)).toHaveCount(0);

    // 刷新页面验证持久化：数据真正落库，刷新后仍不存在
    await projectsPage.page.reload();
    await projectsPage.page.waitForLoadState('networkidle');
    await expect(projectsPage.getProjectCardByName(projectName)).toHaveCount(0);
  });
});
```