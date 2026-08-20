// tests/pages/ProjectsPage.ts

import { Locator, Page, expect } from '@playwright/test';
import { BASE_URL } from '../constants';

export class ProjectsPage {
  readonly page: Page;
  readonly createProjectButton: Locator;
  readonly searchInput: Locator;
  readonly projectNameInput: Locator;
  readonly projectCards: Locator;

  constructor(page: Page) {
    this.page = page;
    this.createProjectButton = page.getByRole('button', { name: '新建项目' });
    this.searchInput = page.getByPlaceholder('搜索项目');
    this.projectNameInput = page.getByPlaceholder('请输入项目名称');
    this.projectCards = page.locator('.project-card');
  }

  async goto(): Promise<void> {
    await Promise.all([
      this.page.waitForResponse(resp =>
        /\/api\/projects(?:[\/?#]|$)/.test(resp.url()) &&
        resp.request().method() === 'GET' &&
        resp.ok()
      ),
      this.page.goto(`${BASE_URL}/console/projects`),
    ]);
    await this.waitForAnyProjectCard();
  }

  async waitForAnyProjectCard(timeout = 5000): Promise<void> {
    await this.projectCards
      .first()
      .waitFor({ state: 'visible', timeout })
      .catch(() => undefined);
  }

  getProjectCardByName(name: string): Locator {
    return this.projectCards.filter({ hasText: name });
  }

  async createProject(name: string): Promise<void> {
    await this.createProjectButton.click();
    const dialog = this.page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await this.projectNameInput.fill(name);
    await Promise.all([
      this.page.waitForResponse(resp =>
        /\/api\/projects(?:[\/?#]|$)/.test(resp.url()) &&
        resp.request().method() === 'POST' &&
        resp.ok()
      ),
      dialog.getByRole('button', { name: '确定' }).first().click(),
    ]);
    await expect(this.getProjectCardByName(name).first()).toBeVisible();
  }

  async searchProjects(keyword: string): Promise<void> {
    await this.searchInput.fill(keyword);
    await Promise.all([
      this.page.waitForResponse(resp =>
        /\/api\/projects(?:[\/?#]|$)/.test(resp.url()) &&
        resp.request().method() === 'GET' &&
        resp.ok()
      ),
      this.searchInput.press('Enter'),
    ]);
    await this.waitForAnyProjectCard();
  }

  async deleteProject(name: string): Promise<void> {
    const card = this.getProjectCardByName(name).first();
    await expect(card).toBeVisible();

    await card.getByRole('button', { name: '更多' }).click();
    const deleteMenuItem = this.page
      .getByRole('menuitem', { name: '删除' })
      .or(this.page.getByText('删除', { exact: true }));
    await deleteMenuItem.first().click();

    const confirmDialog = this.page.getByRole('dialog').last();
    await expect(confirmDialog).toBeVisible();
    await Promise.all([
      this.page.waitForResponse(resp =>
        /\/api\/projects(?:[\/?#]|$)/.test(resp.url()) &&
        ['DELETE', 'POST'].includes(resp.request().method()) &&
        resp.ok()
      ),
      confirmDialog.getByRole('button', { name: '删除' }).first().click(),
    ]);

    await expect(card).toBeHidden();
  }

  async deleteProjectIfExists(name: string): Promise<void> {
    await this.waitForAnyProjectCard();
    if ((await this.getProjectCardByName(name).count()) > 0) {
      await this.deleteProject(name);
    }
  }

  async refresh(): Promise<void> {
    await Promise.all([
      this.page.waitForResponse(resp =>
        /\/api\/projects(?:[\/?#]|$)/.test(resp.url()) &&
        resp.request().method() === 'GET' &&
        resp.ok()
      ),
      this.page.reload(),
    ]);
    await this.waitForAnyProjectCard();
  }
}

// tests/specs/project-management.spec.ts

import { expect, Page, test } from '@playwright/test';
import { LoginPage } from '../helpers';
import { ProjectsPage } from '../pages/ProjectsPage';

const PROJECT_NAME = '自动化测试项目-0721';

test.describe.serial('项目管理', () => {
  let page!: Page;
  let projectsPage!: ProjectsPage;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    const loginPage = new LoginPage(page);
    await loginPage.loginAs('admin');

    projectsPage = new ProjectsPage(page);
    await projectsPage.goto();
    await projectsPage.deleteProjectIfExists(PROJECT_NAME);
  });

  test.afterAll(async () => {
    if (projectsPage) {
      await projectsPage.deleteProjectIfExists(PROJECT_NAME).catch(() => undefined);
    }
    if (page) {
      await page.close();
    }
  });

  test('TC-01-01 创建项目 [P0]（SMOKE-1）', async () => {
    await projectsPage.createProject(PROJECT_NAME);
    await expect(projectsPage.getProjectCardByName(PROJECT_NAME).first()).toBeVisible();
  });

  test('TC-01-02 搜索项目 [P1]', async () => {
    await projectsPage.searchProjects(PROJECT_NAME);
    await expect(projectsPage.projectCards).toHaveCount(1);
    await expect(projectsPage.getProjectCardByName(PROJECT_NAME).first()).toBeVisible();
  });

  test('TC-01-03 删除项目 [P1]', async () => {
    await projectsPage.deleteProject(PROJECT_NAME);
    await expect(projectsPage.getProjectCardByName(PROJECT_NAME)).toBeHidden();

    await projectsPage.refresh();
    await expect(projectsPage.getProjectCardByName(PROJECT_NAME)).toBeHidden();
  });
});

/*
 * 待澄清：
 * 1. LoginPage 的构造签名与 loginAs 行为未在材料中给出，本代码假设 `new LoginPage(page).loginAs('admin')` 登录后可保持会话。
 * 2. `.project-card` 是否为稳定选择器/是否有 data-testid，需确认。
 * 3. 「更多」菜单与确认弹窗是否使用标准 ARIA role（menuitem/dialog/button），若为自定义组件需替换选择器。
 * 4. 删除接口的方法与路径未明确，本代码以 `/api/projects` 的 DELETE/POST 响应作为删除成功标志。
 * 5. 搜索是前端过滤还是触发 GET `/api/projects`，本代码按触发 GET 实现；若为前端过滤需改为等待列表稳定。
 * 6. 项目名称是否需要随机后缀避免并发冲突，本代码按用例固定名称实现。
 * 7. 空列表时 `.project-card` 不存在，本代码对空列表仅等待 GET 响应，不强制 `.project-card` 可见。
 */