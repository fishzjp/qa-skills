## tests/pages/projects.page.ts

```typescript
import { Page, Locator } from '@playwright/test';
import { BASE_URL } from '../constants';

export class ProjectsPage {
  readonly page: Page;
  readonly newProjectButton: Locator;
  readonly searchInput: Locator;

  constructor(page: Page) {
    this.page = page;
    this.newProjectButton = page.getByRole('button', { name: '新建项目' });
    this.searchInput = page.getByPlaceholder('搜索项目');
  }

  /** 导航到项目列表页并等待加载完成 */
  async goto() {
    const responsePromise = this.page.waitForResponse(
      resp => resp.url().includes('/api/projects') && resp.request().method() === 'GET',
    );
    await this.page.goto(`${BASE_URL}/console/projects`);
    await responsePromise;
    await this.page.waitForLoadState('networkidle');
  }

  /** 刷新页面并等待列表加载 */
  async reload() {
    await this.page.reload();
    await this.page.waitForLoadState('networkidle');
  }

  /** 创建项目：点击新建 -> 填写名称 -> 确定 -> 等待列表刷新 */
  async createProject(name: string) {
    await this.newProjectButton.click();
    const nameInput = this.page.getByPlaceholder('请输入项目名称');
    await nameInput.waitFor({ state: 'visible' });
    await nameInput.fill(name);

    const responsePromise = this.page.waitForResponse(
      resp => resp.url().includes('/api/projects') && resp.request().method() === 'POST',
    );
    await this.page.getByRole('button', { name: '确定' }).click();
    await responsePromise;
    await this.page.waitForLoadState('networkidle');
  }

  /** 搜索项目：输入名称并回车触发搜索 */
  async searchProject(name: string) {
    await this.searchInput.fill(name);
    await this.page.keyboard.press('Enter');
    await this.page.waitForLoadState('networkidle');
  }

  /** 获取列表中所有项目卡片 */
  getAllProjectCards(): Locator {
    return this.page.locator('.project-card');
  }

  /** 按名称获取项目卡片 */
  getProjectCardByName(name: string): Locator {
    return this.page.locator('.project-card', { hasText: name });
  }

  /** 删除项目：更多 -> 删除 -> 确认弹窗删除 -> 等待列表刷新 */
  async deleteProject(name: string) {
    const card = this.getProjectCardByName(name);
    await card.getByRole('button', { name: '更多' }).click();
    await this.page.getByRole('menuitem', { name: '删除' }).click();

    // 确认弹窗中的删除按钮
    await this.page.getByRole('dialog').getByRole('button', { name: '删除' }).click();
    await this.page.waitForLoadState('networkidle');
  }

  /** 确保指定名称的项目不存在（搜索 -> 存在则删除 -> 回到完整列表） */
  async ensureProjectNotExists(name: string) {
    await this.goto();
    await this.searchProject(name);
    const card = this.getProjectCardByName(name);
    if (await card.count() > 0) {
      await this.deleteProject(name).catch(() => {});
    }
    await this.goto();
  }
}
```

## tests/01-project-management.spec.ts

```typescript
import { test, expect } from '@playwright/test';
import { LoginPage } from './helpers';
import { ProjectsPage } from './pages/projects.page';

const PROJECT_NAME = '自动化测试项目-0721';

test.describe('项目管理', () => {
  let projectsPage: ProjectsPage;

  test.beforeEach(async ({ page }) => {
    await new LoginPage(page).loginAs('admin');
    projectsPage = new ProjectsPage(page);
    // 清理可能残留的同名项目，确保干净初始状态
    await projectsPage.ensureProjectNotExists(PROJECT_NAME);
  });

  test.afterEach(async () => {
    if (projectsPage) {
      await projectsPage.ensureProjectNotExists(PROJECT_NAME).catch(() => {});
    }
  });

  test('TC-01-01: 创建项目', async () => {
    await projectsPage.createProject(PROJECT_NAME);

    // 预期：列表出现名称为"自动化测试项目-0721"的卡片
    const card = projectsPage.getProjectCardByName(PROJECT_NAME);
    await expect(card).toBeVisible();
  });

  test('TC-01-02: 搜索项目', async () => {
    // 前置：创建项目
    await projectsPage.createProject(PROJECT_NAME);

    // 操作：在搜索框输入项目名称并回车
    await projectsPage.searchProject(PROJECT_NAME);

    // 预期：列表仅显示该项目（其他项目不显示）
    await expect(projectsPage.getAllProjectCards()).toHaveCount(1);
    await expect(projectsPage.getProjectCardByName(PROJECT_NAME)).toBeVisible();
  });

  test('TC-01-03: 删除项目', async () => {
    // 前置：创建项目
    await projectsPage.createProject(PROJECT_NAME);

    // 操作：更多 -> 删除 -> 确认弹窗删除
    await projectsPage.deleteProject(PROJECT_NAME);

    // 预期：列表不再显示该项目
    await expect(projectsPage.getProjectCardByName(PROJECT_NAME)).toHaveCount(0);

    // 预期：刷新页面后仍不存在
    await projectsPage.reload();
    await expect(projectsPage.getProjectCardByName(PROJECT_NAME)).toHaveCount(0);
  });
});
```

---

## 待澄清

1. **搜索匹配模式**：搜索是否为精确匹配？若为模糊匹配，TC-01-02 的 `toHaveCount(1)` 断言可能因环境中存在名称包含"自动化测试项目-0721"的其他项目而失败。若为模糊匹配，需改用更唯一的项目名称（如追加 `Date.now()` 后缀）。
2. **「更多」按钮定位**：「更多」按钮是否具有可访问名称「更多」？若为纯图标按钮（无文本/aria-label），`getByRole('button', { name: '更多' })` 将无法定位，需改用 `locator` + class 或其他属性定位。
3. **确认弹窗角色**：删除确认弹窗是否为 `role="dialog"`？部分 UI 库（如 Ant Design `Modal.confirm`）渲染为 `role="alertdialog"`，需根据实际情况调整定位器。
4. **删除 API 形式**：删除接口是 `DELETE /api/projects/:id` 还是 `POST /api/projects/delete`（带 body）？当前代码使用 `networkidle` 等待，未对具体请求方法做断言；若需严格验证可补充 `waitForResponse`。
5. **项目卡片选择器**：`.project-card` 是否为卡片容器的实际 class？若实际使用 CSS Modules 或其他命名方式，需调整为真实选择器。