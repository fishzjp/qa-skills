## tests/pages/project.page.ts

```typescript
import { Page, Locator } from '@playwright/test';
import { BASE_URL } from '../constants';

export class ProjectPage {
  readonly page: Page;
  readonly createButton: Locator;
  readonly searchInput: Locator;

  constructor(page: Page) {
    this.page = page;
    this.createButton = page.getByRole('button', { name: '新建项目' });
    this.searchInput = page.getByPlaceholder('搜索项目');
  }

  /** 导航到「控制台 -> 项目」页，等待列表加载完成 */
  async goto() {
    await this.page.goto(`${BASE_URL}/console/projects`);
    await this.page.waitForResponse(
      resp =>
        resp.url().includes('/api/projects') &&
        resp.request().method() === 'GET',
    );
    await this.page.waitForLoadState('networkidle');
  }

  /** 点击「新建项目」-> 填入名称 -> 点击「确定」，等待创建接口返回 */
  async createProject(name: string) {
    await this.createButton.click();
    const nameInput = this.page.getByPlaceholder('请输入项目名称');
    // fill 优先；受控组件不生效时改用 keyboard.type
    await nameInput.fill(name);

    const responsePromise = this.page.waitForResponse(
      resp =>
        resp.url().includes('/api/projects') &&
        resp.request().method() === 'POST',
    );
    await this.page.getByRole('button', { name: '确定' }).click();
    await responsePromise;
    await this.page.waitForLoadState('networkidle');
  }

  /** 在搜索框输入关键词并按回车触发搜索 */
  async searchProjects(keyword: string) {
    await this.searchInput.fill(keyword);
    await this.page.keyboard.press('Enter');
    await this.page.waitForResponse(
      resp =>
        resp.url().includes('/api/projects') &&
        resp.request().method() === 'GET',
    );
    await this.page.waitForLoadState('networkidle');
  }

  /** 返回名称匹配的项目卡片 Locator（可能匹配 0~N 个，使用处按需 .first()） */
  getProjectCardByName(name: string): Locator {
    return this.page.locator('.project-card', { hasText: name });
  }

  /** 删除指定名称的项目：更多 -> 删除 -> 确认弹窗删除。项目不存在时安全返回 */
  async deleteProject(name: string) {
    const card = this.getProjectCardByName(name).first();
    if ((await card.count()) === 0) return;

    await card.getByRole('button', { name: '更多' }).click();
    await this.page.getByRole('menuitem', { name: '删除' }).click();

    const responsePromise = this.page.waitForResponse(
      resp =>
        resp.url().includes('/api/projects') &&
        resp.request().method() === 'DELETE',
    );
    await this.page.getByRole('button', { name: '删除' }).click();
    await responsePromise;
    await this.page.waitForLoadState('networkidle');
  }
}
```

---

## tests/01-project-management.spec.ts

```typescript
import { test, expect } from '@playwright/test';
import { LoginPage } from './helpers';
import { ProjectPage } from './pages/project.page';

test.describe('项目管理', () => {
  let projectPage: ProjectPage;
  let createdProjectName: string;

  test.beforeEach(async ({ page }) => {
    createdProjectName = '';
    await new LoginPage(page).loginAs('admin');
    projectPage = new ProjectPage(page);
    await projectPage.goto();
  });

  test.afterEach(async () => {
    if (createdProjectName) {
      await projectPage.deleteProject(createdProjectName).catch(() => {});
    }
  });

  test('TC-01-01: 创建项目', async () => {
    createdProjectName = `自动化测试项目-${Date.now()}`;

    await projectPage.createProject(createdProjectName);

    const card = projectPage.getProjectCardByName(createdProjectName);
    await expect(card.first()).toBeVisible();
  });

  test('TC-01-02: 搜索项目', async () => {
    createdProjectName = `自动化测试项目-${Date.now()}`;
    await projectPage.createProject(createdProjectName);

    await projectPage.searchProjects(createdProjectName);

    // 列表仅显示该搜索项目
    const cards = projectPage.page.locator('.project-card');
    await expect(cards).toHaveCount(1);
    await expect(cards.first()).toContainText(createdProjectName);
  });

  test('TC-01-03: 删除项目', async () => {
    createdProjectName = `自动化测试项目-${Date.now()}`;
    await projectPage.createProject(createdProjectName);

    // 确认项目存在
    await expect(
      projectPage.getProjectCardByName(createdProjectName).first(),
    ).toBeVisible();

    // 执行删除
    await projectPage.deleteProject(createdProjectName);

    // 验证列表不再显示该项目
    await expect(
      projectPage.getProjectCardByName(createdProjectName).first(),
    ).not.toBeVisible();

    // 刷新页面后仍不存在
    await projectPage.page.reload();
    await projectPage.page.waitForLoadState('networkidle');
    await expect(
      projectPage.getProjectCardByName(createdProjectName).first(),
    ).not.toBeVisible();

    // 项目已删除，标记为空避免 afterEach 重复清理
    createdProjectName = '';
  });
});
```

---

## 待澄清清单

1. **「更多」菜单项的 ARIA 角色**：踩点结论描述为"展开菜单，含「删除」项"，代码中按 `menuitem` 角色定位。若实际渲染为 `button` 或 `link`，`getByRole('menuitem', { name: '删除' })` 将匹配失败，需调整为实际角色或改用 `getByText`。

2. **删除 API 的 HTTP 方法与路径**：代码假设删除请求为 `DELETE /api/projects`。若系统采用非 RESTful 风格（如 `POST /api/projects/{id}/delete`），`waitForResponse` 的匹配条件需相应调整。

3. **创建项目弹窗关闭行为**：代码假设点击「确定」后弹窗自动关闭、列表自动刷新。若弹窗不自动关闭，可能需要在 `createProject` 中增加显式关闭弹窗的步骤。

4. **搜索框 `fill` 兼容性**：搜索框使用 `fill` 输入关键词。若该输入框为复杂受控组件（如 Ant Design Search 组件），`fill` 可能不触发状态更新，需改用 `keyboard.type`。

5. **TC-01-02 搜索结果精确度**：`toHaveCount(1)` 假设搜索为精确匹配。若搜索为模糊匹配且系统中存在名称包含该项目名称的其他项目，断言可能失败。需确认搜索是精确匹配还是模糊匹配。