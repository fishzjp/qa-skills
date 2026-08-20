```typescript
// 文件：tests/pages/ProjectsPage.ts
import { Page, Locator } from '@playwright/test';
import { BASE_URL } from '../constants';

export class ProjectsPage {
  readonly page: Page;
  readonly url: string;

  constructor(page: Page) {
    this.page = page;
    this.url = `${BASE_URL}/console/projects`;
  }

  /**
   * 导航到「控制台 -> 项目」页并等待列表加载完成。
   * 加载完成标志：GET /api/projects 返回 200 且页面出现 .project-card。
   */
  async goto(): Promise<void> {
    await Promise.all([
      this.page.waitForResponse(
        (resp) =>
          resp.url().includes('/api/projects') &&
          resp.request().method() === 'GET' &&
          resp.status() === 200,
      ),
      this.page.goto(this.url),
    ]);
    await this.page.locator('.project-card').first().waitFor({ state: 'visible' });
  }

  /**
   * 等待项目列表加载完成（GET /api/projects 返回 + 网络空闲）。
   * 适用于创建/搜索/删除等操作后的列表刷新场景。
   */
  async waitForProjectsLoaded(): Promise<void> {
    await this.page.waitForResponse(
      (resp) =>
        resp.url().includes('/api/projects') &&
        resp.request().method() === 'GET' &&
        resp.status() === 200,
    );
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * 获取所有项目卡片
   */
  getAllProjectCards(): Locator {
    return this.page.locator('.project-card');
  }

  /**
   * 根据项目名称获取对应的项目卡片
   */
  getProjectCardByName(name: string): Locator {
    return this.page.locator('.project-card', { hasText: name });
  }

  /**
   * 创建项目
   * 1. 点击「新建项目」按钮
   * 2. 填写项目名称
   * 3. 点击「确定」
   */
  async createProject(name: string): Promise<void> {
    await this.page.getByRole('button', { name: '新建项目' }).click();
    await this.page.getByPlaceholder('请输入项目名称').fill(name);
    await this.page.getByRole('button', { name: '确定' }).click();
    await this.waitForProjectsLoaded();
  }

  /**
   * 搜索项目
   * 1. 在搜索框输入关键词
   * 2. 按回车触发搜索
   */
  async searchProject(keyword: string): Promise<void> {
    const searchBox = this.page.getByPlaceholder('搜索项目');
    await searchBox.fill(keyword);
    await searchBox.press('Enter');
    await this.waitForProjectsLoaded();
  }

  /**
   * 删除指定名称的项目
   * 1. 在该项目卡片点击「更多」->「删除」
   * 2. 在确认弹窗点击「删除」
   */
  async deleteProject(name: string): Promise<void> {
    const card = this.getProjectCardByName(name);
    await card.getByRole('button', { name: '更多' }).click();
    await this.page.getByRole('menuitem', { name: '删除' }).click();
    await this.page.getByRole('dialog').getByRole('button', { name: '删除' }).click();
    await this.waitForProjectsLoaded();
  }

  /**
   * 刷新页面并等待列表加载
   */
  async reload(): Promise<void> {
    await Promise.all([
      this.page.waitForResponse(
        (resp) =>
          resp.url().includes('/api/projects') &&
          resp.request().method() === 'GET' &&
          resp.status() === 200,
      ),
      this.page.reload(),
    ]);
    await this.page.waitForLoadState('networkidle');
  }
}
```

```typescript
// 文件：tests/specs/project-management.spec.ts
import { test, expect, Page } from '@playwright/test';
import { LoginPage } from '../helpers';
import { ProjectsPage } from '../pages/ProjectsPage';

const PROJECT_NAME = '自动化测试项目-0721';

test.describe.serial('项目管理 - TC-01', () => {
  let page!: Page;
  let projectsPage!: ProjectsPage;

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    page = await context.newPage();
    const loginPage = new LoginPage(page);
    await loginPage.loginAs('admin');
    projectsPage = new ProjectsPage(page);
    await projectsPage.goto();

    // 清理上次运行可能残留的同名项目，确保 TC-01-01 可重复执行
    try {
      await projectsPage.searchProject(PROJECT_NAME);
      if (await projectsPage.getProjectCardByName(PROJECT_NAME).isVisible()) {
        await projectsPage.deleteProject(PROJECT_NAME);
      }
    } catch {
      // 忽略清理过程中的错误
    }
    await projectsPage.goto();
  });

  test.afterAll(async () => {
    await page?.close().catch(() => {});
  });

  test('TC-01-01 创建项目 [P0]（SMOKE-1）', async () => {
    await projectsPage.createProject(PROJECT_NAME);

    // 预期：列表出现名称为「自动化测试项目-0721」的卡片
    await expect(projectsPage.getProjectCardByName(PROJECT_NAME)).toBeVisible();
  });

  test('TC-01-02 搜索项目 [P1]', async () => {
    await projectsPage.searchProject(PROJECT_NAME);

    // 预期：列表仅显示该项目（其他项目不显示）
    await expect(projectsPage.getAllProjectCards()).toHaveCount(1);
    await expect(projectsPage.getProjectCardByName(PROJECT_NAME)).toBeVisible();
  });

  test('TC-01-03 删除项目 [P1]', async () => {
    // 前置：列表中存在「自动化测试项目-0721」（由 TC-01-01 创建）
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

## 待澄清清单

1. **项目卡片选择器**：`.project-card` 及卡片内名称的 DOM 结构待确认；当前使用 `hasText` 子串匹配，若卡片内存在同名前缀的其他文本节点可能误匹配，需确认是否需要精确匹配（如 `getByText(name, { exact: true })`）。
2. **「更多」按钮**：当前假设为 `role=button name=更多`；若实际为图标按钮（无文字 accessible name）或 dropdown trigger，需改用其他选择器。
3. **删除菜单项**：当前假设为 `role=menuitem name=删除`；若菜单实现非标准 ARIA menu（如 popover + 普通按钮），需调整定位方式。
4. **确认弹窗**：当前假设为 `role=dialog`；若弹窗未设置 ARIA role，需改用 class 选择器（如 `.confirm-modal` 或 `.ant-modal-confirm`）。
5. **搜索机制**：当前假设为后端搜索（回车触发 `GET /api/projects` 请求并重新渲染列表），`toHaveCount(1)` 依赖此假设；若为前端过滤，需改为可见性断言。
6. **admin 账号默认数据**：`goto()` 中等待 `.project-card` 出现，依赖 admin 账号下至少存在一个项目；若无默认项目，`goto()` 会超时，需改为等待响应 + `networkidle` 兜底。
7. **LoginPage.loginAs 行为**：假设其内部会自行导航到登录页并完成登录后跳转控制台首页；若需外部先导航到登录页，需在 `beforeAll` 中补充 `page.goto`。
8. **删除后列表为空场景**：`waitForProjectsLoaded()` 当前用 `networkidle` 兜底以应对删除后列表为空（无 `.project-card`）的情况；若产品有骨架屏或空状态组件，可改用更精确的空状态标志。