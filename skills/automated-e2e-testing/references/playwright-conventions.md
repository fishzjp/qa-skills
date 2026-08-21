# Playwright 工程约定与代码模板

> `automated-e2e-testing` 的脚手架、配置与场景代码模板全集。工作流零/一/二需要写代码时**加载本文件**；SKILL.md 只保留工作流与决策点。

## 1. 项目脚手架

```
playwright/
├── playwright.config.ts      # 配置
├── package.json               # 脚本入口
├── tests/
│   ├── constants.ts           # 常量（账号、URL、状态枚举）
│   ├── helpers.ts             # 通用函数（登录、多用户会话、Bug 证据收集）
│   ├── pages/                 # Page Objects
│   │   └── xxx.page.ts        # 每个页面一个文件
│   ├── {序号}-{模块}.spec.ts  # 正式测试用例
│   └── explore-{功能}.spec.ts # 业务熟悉探索（临时）
└── test-data/                 # CSV 等测试数据
```

运行命令（依赖 package.json 的 scripts 定义，新项目需配置 `"test": "playwright test"`、`"test:headed": "playwright test --headed"`、`"show-report": "playwright show-report"`）：

```bash
cd playwright

npm test                          # 全量运行
npm run test:headed               # 有头模式（可视观察）
npx playwright test tests/{文件名}.spec.ts  # 运行单个文件
npm run show-report               # 查看报告
```

## 2. 环境与账号配置

**不硬编码任何环境地址或账号。** 所有 URL、账号、角色映射集中配置在项目的 `tests/constants.ts`（或 `.env`）中，代码通过常量引用：

```typescript
// tests/constants.ts
export const BASE_URL = process.env.TEST_BASE_URL ?? '<你的测试环境地址>';

// 角色账号映射：key 为角色名，供 LoginPage.loginAs(role) 使用
export const ACCOUNTS = {
  admin: { username: '<管理员账号>', password: '<密码>' },
  user:  { username: '<普通用户账号>', password: '<密码>' },
  // 按你的系统角色继续扩展
} as const;
```

> 账号、密码、真实用户 ID 等敏感信息不要提交到代码仓库，建议通过 `.env` + `dotenv` 注入，或在 CI 密钥中提供；`constants.ts` 只读取环境变量并提供默认占位。

## 3. playwright.config.ts

```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,       // 串行执行，避免状态冲突
  timeout: 60_000,            // 单个测试超时 60s
  use: {
    actionTimeout: 10_000,      // 单个操作超时 10s
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    baseURL: process.env.TEST_BASE_URL ?? '<你的测试环境地址>',
  },
});
```

> 注意：`actionTimeout` / `screenshot` / `trace` / `baseURL` 必须放在 `use` 内——写在配置顶层会被 Playwright 静默忽略，导致失败时无截图、无 trace。

## 4. 探索测试模板（工作流零用）

```typescript
// explore-{功能}.spec.ts — 临时文件，知识提取后删除
import { test } from '@playwright/test';
import { LoginPage, setupApiLogging } from './helpers';

test('业务熟悉：探索{功能名}页面结构', async ({ page }) => {
  const apiLog = setupApiLogging(page);

  await new LoginPage(page).loginAs('admin');
  await page.goto('/<你的页面路由>');
  await page.waitForLoadState('networkidle');

  // 全页截图
  await page.screenshot({ path: 'debug-{功能}-landing.png', fullPage: true });

  // 枚举可交互元素
  const buttons = await page.getByRole('button').allTextContents();
  const tabs = await page.getByRole('tab').allTextContents();
  console.log('按钮:', buttons);
  console.log('Tab:', tabs);
  console.log('当前 URL:', page.url());

  // 按测试用例步骤操作，每步截图
  // ...
});
```

## 5. 场景代码模板（工作流一用）

### CRUD 操作

```typescript
test.describe('{模块名}', () => {
  let createdName: string;
  let xxxPage: XxxPage; // afterEach 清理要用，在 beforeEach 中初始化

  test.beforeEach(async ({ page }) => {
    // 登录 + 进入页面
    xxxPage = new XxxPage(page);
  });

  test.afterEach(async () => {
    // beforeEach 可能登录失败导致 xxxPage 未初始化，同步判空防清理噪音
    if (createdName && xxxPage) {
      await xxxPage.deleteXxx(createdName).catch(() => {});
    }
  });

  test('TC-01-01: {用例描述}', async () => {
    createdName = `{前缀}-${Date.now()}`;
    await xxxPage.createXxx(createdName);

    const row = await xxxPage.getXxxByName(createdName);
    expect(row).not.toBeNull();
    await expect(row!).toBeVisible();
  });
});
```

### 表单提交

```typescript
test('TC-01-02: {用例描述}', async ({ page }) => {
  // 1. 先注册响应等待（必须在操作之前；勿用固定 waitForTimeout，见 SKILL.md 速查表）
  const responsePromise = page.waitForResponse(
    resp => resp.url().includes('/api/target') && resp.request().method() === 'POST',
  );

  // 2. 填充表单（fill 优先；受控组件校验不触发/值不生效时改用 keyboard.type，详见速查表）
  await page.locator('#field').fill('值');

  // 3. 提交
  await page.getByRole('button', { name: '提交' }).click();

  // 4. 验证 API 调用 + 持久化
  const response = await responsePromise;
  expect(response.ok()).toBeTruthy();
  await page.reload();
  await expect(page.getByText('值')).toBeVisible();
});
```

### 状态流转

```typescript
test('TC-01-03: {用例描述}', async ({ page }) => {
  // 前置：用对应 Page Object 创建一条可操作的业务数据
  const { resourceName } = await createResourceWithData(page, 'TC-STATUS');
  await xxxPage.performAction();
  await expect(page.getByText('<目标状态文案>')).toBeVisible();
});
```

### 多用户并发

```typescript
test('TC-01-04: {用例描述}', async ({ browser }) => {
  // 创建两个独立会话（各自登录不同角色），见 references/helpers_reference.md
  const { pageA, pageB, contextA, contextB } =
    await createDualSession(browser, 'admin', 'user');
  try {
    await pageA.getByRole('button', { name: '<动作A>' }).click();
    await pageB.getByRole('button', { name: '<动作B>' }).click();
    await expect(pageA.getByText('<预期文案>')).toBeVisible();
  } finally {
    await closeContexts(contextA, contextB);
  }
});
```

## 6. Page Object 编写规范

**复用优先**：检查 `tests/pages/` 下是否已有对应页面的 Page Object。

```typescript
// pages/xxx.page.ts
import { Page, Locator, expect } from '@playwright/test';
import { BASE_URL } from '../constants';

export class XxxPage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async goto() {
    await this.page.goto(`${BASE_URL}/xxx/list`);
    await this.page.waitForLoadState('networkidle');
  }

  async createXxx(name: string) {
    // fill 优先；受控组件校验不触发/值不生效时改用 keyboard.type
    await this.page.getByRole('textbox', { name: /名称/ }).click();
    await this.page.keyboard.type(name, { delay: 30 });
  }

  async deleteXxx(name: string) {
    const row = await this.getXxxByName(name);
    if (!row) return;
    await row.locator('[aria-label="delete"]').first().click();
    await this.page.getByRole('button', { name: /确\s*定/ }).click();
  }
}
```

## 7. 测试数据管理与 spec 命名

- **常量数据**：放 `constants.ts`（账号、URL、状态枚举）
- **CSV 数据**：放 `test-data/` 目录
- **动态数据**：在测试中用 `Date.now()` 生成唯一名称

| 类型 | 命名 | 示例 |
|------|------|------|
| 正式测试 | `{序号}-{模块}.spec.ts` | `01-resource-creation.spec.ts` |
| 探索测试 | `explore-{功能}.spec.ts` | `explore-config.spec.ts`（**临时文件**） |

## 8. Bug 证据收集代码（工作流二用）

```typescript
test('测试中发现 Bug', async ({ page }, testInfo) => {
  const tracker = setupBugTracking(page);
  await new LoginPage(page).loginAs('admin');

  // 截图 1：操作前
  await page.screenshot({ path: 'bug-001-01-操作前.png', fullPage: true });

  // 触发异常的操作（先注册响应等待，再点击；勿用固定 waitForTimeout）
  const saveResponse = page.waitForResponse(resp => resp.url().includes('/api/save'));
  await page.getByRole('button', { name: '保存' }).click();
  await saveResponse;

  // 截图 2：异常现象
  await page.screenshot({ path: 'bug-001-02-异常.png', fullPage: true });

  // 收集完整证据（截图 + API + 控制台）
  const evidence = await tracker.collect(testInfo, 'BUG-001', '保存失败无提示');
});
```
