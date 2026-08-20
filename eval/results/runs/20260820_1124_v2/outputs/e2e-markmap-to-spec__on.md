```typescript
// File: playwright/tests/pages/projects.page.ts
import { Page, Locator } from '@playwright/test';
import { BASE_URL } from '../constants';

export class ProjectsPage {
  readonly page: Page;
  readonly createButton: Locator;
  readonly searchInput: Locator;

  constructor(page: Page) {
    this.page = page;
    this.createButton = page.getByRole('button', { name: '新建项目' });
    this.searchInput = page.getByPlaceholder('搜索项目');
  }

  /** 进入「控制台 -> 项目」页并等待列表加载完成 */
  async goto() {
    const listResponse = this.page.waitForResponse(
      resp => resp.url().includes('/api/projects') && resp.request().method() === 'GET',
    );
    await this.page.goto(`${BASE_URL}/console/projects`);
    await listResponse;
    await this.page.waitForLoadState('networkidle');
    await this.page.waitForSelector('.project-card');
  }

  /** 重新加载列表页 */
  async reload() {
    const listResponse = this.page.waitForResponse(
      resp => resp.url().includes('/api/projects') && resp.request().method() === 'GET',
    );
    await this.page.reload();
    await listResponse;
    await this.page.waitForLoadState('networkidle');
    await this.page.waitForSelector('.project-card');
  }

  /** 新建项目：点击「新建项目」-> 填名称 -> 点「确定」，等待 POST 响应 */
  async createProject(name: string) {
    const postResponse = this.page.waitForResponse(
      resp => resp.url().includes('/api/projects') && resp.request().method() === 'POST',
    );
    await this.createButton.click();
    const nameInput = this.page.getByPlaceholder('请输入项目名称');
    await nameInput.fill(name);
    await this.page.getByRole('button', { name: '确定' }).click();
    await postResponse;
    await this.page.waitForLoadState('networkidle');
  }

  /** 按名称返回项目卡片 Locator（不存在时 count 为 0） */
  getProjectCardByName(name: string): Locator {
    return this.page.locator('.project-card', { hasText: name });
  }

  /** 返回当前列表中所有可见项目卡片的文本内容 */
  async getVisibleProjectNames(): Promise<string[]> {
    return this.page.locator('.project-card').allTextContents();
  }

  /** 在搜索框输入关键词并回车，等待 GET 响应 */
  async searchProjects(keyword: string) {
    const getResponse = this.page.waitForResponse(
      resp => resp.url().includes('/api/projects') && resp.request().method() === 'GET',
    );
    await this.searchInput.click();
    await this.searchInput.fill(keyword);
    await this.page.keyboard.press('Enter');
    await getResponse;
    await this.page.waitForLoadState('networkidle');
  }

  /** 打开指定项目卡片的「更多」菜单 */
  private async openProjectMenu(name: string) {
    const card = this.getProjectCardByName(name);
    await card.getByRole('button', { name: '更多' }).click();
  }

  /** 删除指定项目：更多 -> 删除 -> 确认弹窗「删除」，等待 DELETE 响应。
   *  若项目不存在则跳过（用于 afterEach 清理） */
  async deleteProject(name: string) {
    await this.page.waitForLoadState('networkidle');
    const card = this.getProjectCardByName(name);
    if ((await card.count()) === 0) return;

    const deleteResponse = this.page.waitForResponse(
      resp => resp.url().includes('/api/projects') && resp.request().method() === 'DELETE',
    );
    await this.openProjectMenu(name);
    await this.page.getByRole('menuitem', { name: '删除' }).click();
    await this.page.getByRole('button', { name: '删除' }).click();
    await deleteResponse;
    await this.page.waitForLoadState('networkidle');
  }
}
```

```typescript
// File: playwright/tests/01-project-management.spec.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from './helpers';
import { ProjectsPage } from './pages/projects.page';

test.describe('项目管理', () => {
  let projectsPage: ProjectsPage;
  let projectName: string;

  test.beforeEach(async ({ page }) => {
    // 每个用例独立数据：用时间戳生成唯一名称避免冲突
    projectName = `自动化测试项目-${Date.now()}`;
    await new LoginPage(page).loginAs('admin');
    projectsPage = new ProjectsPage(page);
    await projectsPage.goto();
  });

  test.afterEach(async () => {
    // 自清理：删除可能残留的项目（删除已不存在的项目会被跳过）
    if (projectsPage && projectName) {
      await projectsPage.deleteProject(projectName).catch(() => {});
    }
  });

  test('TC-01-01: 创建项目', async () => {
    await projectsPage.createProject(projectName);

    const card = projectsPage.getProjectCardByName(projectName);
    await expect(card).toBeVisible();
  });

  test('TC-01-02: 搜索项目', async () => {
    // 前置：创建一条可搜索的项目数据
    await projectsPage.createProject(projectName);

    await projectsPage.searchProjects(projectName);

    const visibleNames = await projectsPage.getVisibleProjectNames();
    // 列表仅显示该项目（其他项目不显示）
    expect(visibleNames).toHaveLength(1);
    expect(visibleNames[0]).toContain(projectName);
  });

  test('TC-01-03: 删除项目', async () => {
    // 前置：创建一条可删除的项目数据
    await projectsPage.createProject(projectName);

    await projectsPage.deleteProject(projectName);

    // 列表不再显示该项目
    const card = projectsPage.getProjectCardByName(projectName);
    await expect(card).toHaveCount(0);

    // 刷新页面后仍不存在
    await projectsPage.reload();
    await expect(card).toHaveCount(0);
  });
});
```

---

## 待澄清清单

1. **项目名称固定 vs 动态**：手动用例 TC-01-01 中名称硬编码为「自动化测试项目-0721」。为支持用例独立运行 + 重复执行不冲突，本实现改为 `自动化测试项目-${Date.now()}`。如需严格按用例字面值使用固定名称，请确认是否接受重复运行需手工清场。
2. **「更多」按钮选择器**：业务熟悉踩点说明卡片右下角有「更多」按钮，但未实地验证其 role/DOM 结构。本实现使用 `card.getByRole('button', { name: '更多' })`，若实际为 `dropdown.trigger` 或图标按钮需调整。
3. **「删除」菜单项 role**：假设展开菜单项 role 为 `menuitem`（Ant Design Dropdown.Menu 默认）。若实际为 `menuitemradio`、`option` 或纯文本节点需调整。
4. **确认弹窗「删除」按钮的区分**：删除菜单项点击后弹出确认弹窗，弹窗内「删除」按钮与列表中可能的「删除」文本共存。本实现依赖 `getByRole('button', { name: '删除' })` 在确认弹窗出现时仅匹配到弹窗按钮。若同一时刻存在多个匹配，需更精确限定（如限定 dialog 容器内）。
5. **搜索接口路径**：假设搜索复用 `GET /api/projects`（带 query 参数），未实地验证。若实际为独立 `/api/projects/search` 等路径，`searchProjects` 与 `goto`/`reload` 中的响应匹配条件需调整。
6. **删除接口路径**：假设为 `DELETE /api/projects/{id}` 形式，匹配条件 `url.includes('/api/projects')` 已足够；若存在 `/api/projects/batch` 等同前缀接口需进一步收紧。
7. **创建项目是否需要其他必填字段**：踩点说明只提到名称输入框。若实际新建弹窗存在其他必填字段（描述、所属组织等），`createProject` 需补充填充逻辑。
8. **`fill` 对名称输入框是否生效**：默认用 `fill()`。若该项目名称输入框为强受控组件导致 `fill` 不触发校验/值不生效，需改用 `keyboard.type(name, { delay: 30 })`。