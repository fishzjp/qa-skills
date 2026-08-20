```typescript
// tests/pages/project.page.ts
import { Page, Locator, expect } from '@playwright/test';
import { BASE_URL } from '../constants';

export class ProjectPage {
  readonly page: Page;
  readonly createButton: Locator;
  readonly searchInput: Locator;
  readonly projectCards: Locator;

  constructor(page: Page) {
    this.page = page;
    this.createButton = page.getByRole('button', { name: '新建项目' });
    this.searchInput = page.getByPlaceholder('搜索项目');
    this.projectCards = page.locator('.project-card');
  }

  /** 进入「控制台 -> 项目」页并等待列表加载完成 */
  async goto() {
    const listResponse = this.page.waitForResponse(
      resp => resp.url().includes('/api/projects') && resp.request().method() === 'GET',
    );
    await this.page.goto(`${BASE_URL}/console/projects`);
    await listResponse;
    await this.page.waitForLoadState('networkidle');
  }

  /** 等待列表刷新（操作后重新拉取 GET /api/projects） */
  async waitForListRefresh() {
    await this.page
      .waitForResponse(
        resp => resp.url().includes('/api/projects') && resp.request().method() === 'GET',
      )
      .catch(() => {});
    await this.page.waitForLoadState('networkidle');
  }

  /** 点击「新建项目」并填充名称、提交，等待创建接口与列表刷新 */
  async createProject(name: string) {
    await this.createButton.click();

    const nameInput = this.page.getByPlaceholder('请输入项目名称');
    await nameInput.click();
    // 受控组件用 keyboard.type 最稳（见 SKILL 速查表）
    await this.page.keyboard.type(name, { delay: 30 });

    // 先注册响应等待，再点提交
    const createResponse = this.page.waitForResponse(
      resp => resp.url().includes('/api/projects') && resp.request().method() === 'POST',
    );
    await this.page.getByRole('dialog').getByRole('button', { name: '确定' }).click();
    const response = await createResponse;
    expect(response.ok()).toBeTruthy();

    await this.waitForListRefresh();
  }

  /** 在搜索框输入关键字并回车触发搜索 */
  async searchProject(keyword: string) {
    await this.searchInput.click();
    await this.searchInput.fill('');
    await this.page.keyboard.type(keyword, { delay: 30 });

    const searchResponse = this.page.waitForResponse(
      resp => resp.url().includes('/api/projects') && resp.request().method() === 'GET',
    );
    await this.page.keyboard.press('Enter');
    await searchResponse;
    await this.page.waitForLoadState('networkidle');
  }

  /** 按名称查找项目卡片，找不到返回 null */
  async getProjectCard(name: string): Promise<Locator | null> {
    const matched = this.projectCards.filter({ hasText: name });
    const count = await matched.count();
    return count > 0 ? matched.first() : null;
  }

  /** 当前列表可见卡片数量 */
  async getCardCount(): Promise<number> {
    return this.projectCards.count();
  }

  /** 删除指定名称的项目：更多 -> 删除 -> 确认弹窗删除 */
  async deleteProject(name: string) {
    const card = await this.getProjectCard(name);
    if (!card) return;

    await card.getByRole('button', { name: '更多' }).click();
    await this.page.getByRole('menuitem', { name: '删除' }).click();

    const deleteResponse = this.page.waitForResponse(
      resp => resp.url().includes('/api/projects') && resp.request().method() === 'DELETE',
    );
    await this.page.getByRole('dialog').getByRole('button', { name: '删除' }).click();
    const response = await deleteResponse;
    expect(response.ok()).toBeTruthy();

    await this.waitForListRefresh();
  }

  /** 刷新页面并等待列表重新加载 */
  async reloadList() {
    const listResponse = this.page.waitForResponse(
      resp => resp.url().includes('/api/projects') && resp.request().method() === 'GET',
    );
    await this.page.reload();
    await listResponse;
    await this.page.waitForLoadState('networkidle');
  }
}
```

```typescript
// tests/01-project-management.spec.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from './helpers';
import { ProjectPage } from './pages/project.page';

test.describe('项目管理', () => {
  let projectPage: ProjectPage;
  let createdName: string;

  test.beforeEach(async ({ page }) => {
    await new LoginPage(page).loginAs('admin');
    projectPage = new ProjectPage(page);
    await projectPage.goto();
    // 每条用例独立使用唯一名称，避免测试间冲突
    createdName = `自动化测试项目-${Date.now()}`;
  });

  test.afterEach(async () => {
    // 自清理：若项目仍存在则删除（TC-01-03 已删除时会将 createdName 置空跳过）
    if (createdName && projectPage) {
      await projectPage.deleteProject(createdName).catch(() => {});
    }
  });

  test('TC-01-01: 创建项目', async () => {
    await projectPage.createProject(createdName);

    const card = await projectPage.getProjectCard(createdName);
    expect(card).not.toBeNull();
    await expect(card!).toBeVisible();
  });

  test('TC-01-02: 搜索项目', async () => {
    // 前置：自建数据
    await projectPage.createProject(createdName);

    await projectPage.searchProject(createdName);

    // 预期：列表仅显示该项目
    const count = await projectPage.getCardCount();
    expect(count).toBe(1);

    const card = await projectPage.getProjectCard(createdName);
    expect(card).not.toBeNull();
    await expect(card!).toBeVisible();
  });

  test('TC-01-03: 删除项目', async () => {
    // 前置：自建数据
    await projectPage.createProject(createdName);

    await projectPage.deleteProject(createdName);

    // 预期：列表不再显示该项目
    const card = await projectPage.getProjectCard(createdName);
    expect(card).toBeNull();

    // 预期：刷新页面后仍不存在
    await projectPage.reloadList();
    const cardAfterReload = await projectPage.getProjectCard(createdName);
    expect(cardAfterReload).toBeNull();

    // 标记已删除，afterEach 跳过清理
    createdName = '';
  });
});
```

---

## 待澄清清单

1. **「更多」按钮与删除菜单项的精确角色**：当前假设卡片内「更多」为 `button` 角色、文案「更多」；展开后「删除」为 `menuitem` 角色。若实际为其他结构（如 popover 内普通按钮），需调整 `deleteProject` 中定位方式。

2. **创建项目弹窗是否有其他必填字段**：手动用例仅提及名称。若弹窗存在其他隐藏必填项（描述、所属组织等），`createProject` 需补充填充逻辑，否则提交可能被拦截。

3. **接口方法假设**：创建假设 `POST /api/projects`，删除假设 `DELETE /api/projects`，搜索/列表假设 `GET /api/projects`。若实际为 `PUT`/`DELETE /api/projects/{id}` 等变体，`waitForResponse` 匹配条件需对应调整。

4. **搜索结果为空时 `.project-card` 是否存在**：当前 `getCardCount` 基于 `.project-card` 计数，假设空结果时该元素不存在。若空状态仍渲染占位卡片（带不同 class），需改用更精确的选择器区分真实项目卡片与空状态占位。

5. **创建项目后列表是否自动刷新**：假设提交成功后前端会重新拉取 `GET /api/projects`。若该列表为本地追加（不发起新请求），`waitForListRefresh` 中的 `waitForResponse` 会超时（已用 `.catch` 容错，但断言仍依赖卡片出现）。

6. **登录后跳转**：`LoginPage.loginAs('admin')` 假设登录后跳转至控制台首页，随后 `projectPage.goto()` 显式导航至 `/console/projects`。若登录态未就绪或路由需权限校验，需确认登录后是否需等待特定元素。