---
name: automated-e2e-testing
description: 当需要将手动测试用例转为 Playwright E2E 测试、对 Web 应用进行探索性自动化测试、编写 Page Object/Helper，或在自动化测试中记录 Bug 报告时使用。
---

# 自动化 E2E 测试

## Overview

本 skill 覆盖 Web 应用自动化测试的完整工作流：将手动测试用例（Markdown）转化为 Playwright spec → 运行并验证 → 发现 Bug → 输出测试报告。

核心原则：
1. **先熟悉业务再写测试** — 对功能不熟悉时，先用自动化脚本主动探索系统，理解实际行为后再动手写测试代码
2. **有疑问就提问，不自行假设** — 编写过程中遇到任何不明确的地方，必须向用户提问澄清，绝不凭猜测写代码
3. **每条自动化用例对应一条手动用例，每条 test 只测一个点**
4. **每个 test 独立**（自建数据 + 自清理）
5. **必须使用 Page Object** — 正式测试中禁止裸写定位器，所有页面交互封装在 Page Object 中

## When to Use

- 给定测试用例 Markdown，需要生成 Playwright spec 文件
- 需要对 Web 应用进行自动化探索性测试
- 自动化测试中发现 Bug，需要记录测试报告
- 需要编写新的 Page Object 或 Helper 函数

## When NOT to Use

- 编写手动测试用例 → 用 `test-case-writing` skill
- 纯 API 接口测试 → 用 Python 脚本 + requests
- 单元测试 → 用 Jest/Vitest
- 性能压测 → 用专业工具（k6、locust）

## 提问时机（必须遵守）

**核心规则：不确定就问，宁可多问不要瞎猜。**

| 场景 | 应提问的内容 | 不要自行假设 |
|------|-------------|-------------|
| 元素定位失败 | "在{页面}上找不到{元素}，实际页面结构是否与预期一致？" | 不要随意换选择器猜测 |
| 操作路径不明确 | "测试用例说{操作X}，但页面上没有直接的入口" | 不要自行拼凑操作步骤 |
| 预期行为有歧义 | "预期{结果A}，实际{结果B}，应以哪个为准？" | 不要选择性地相信其中一个 |
| 业务规则不清楚 | "规则{X}的具体边界是什么？" | 不要用常见默认值代替 |
| 探索中发现异常 | "发现{异常行为}，这是预期行为还是 Bug？" | 不要自行判定是 Bug 还是特性 |

**提问格式**：
```
🔍 遇到问题需要确认：
**问题**: {具体描述}
**背景**: {在做什么、发现了什么}
**影响**: {影响哪些测试用例}
**选项**: A) ... B) ...（如有）
```

## 项目环境

### 运行命令

```bash
cd playwright

npm test                          # 全量运行
npm run test:headed               # 有头模式（可视观察）
npx playwright test tests/{文件名}.spec.ts  # 运行单个文件
npm run show-report               # 查看报告
```

### 环境与账号配置

**本 skill 不硬编码任何环境地址或账号。** 所有 URL、账号、角色映射请集中配置在项目的 `tests/constants.ts`（或 `.env`）中，代码通过常量引用。建议结构：

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

### 代码架构

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
│   └── explore-{功能}.spec.ts # 探索性测试（临时）
└── test-data/                 # CSV 等测试数据
```

### Playwright 配置

```typescript
{
  testDir: './tests',
  fullyParallel: false,       // 串行执行，避免状态冲突
  timeout: 60_000,            // 单个测试超时 60s
  actionTimeout: 10_000,      // 单个操作超时 10s
  screenshot: 'only-on-failure',
  trace: 'retain-on-failure',
  baseURL: process.env.TEST_BASE_URL ?? '<你的测试环境地址>',
}
```

---

## 工作流零：业务熟悉（前置必做）

**何时需要**：从未测试过该功能模块 / 出现不熟悉的页面路由 / 需要编写新的 Page Object / 拿到需求但不知道系统长什么样

### 步骤

1. **探索页面结构**：登录 → 导航到目标页面 → 截图 → 枚举所有可交互元素
2. **体验核心流程**：按测试用例步骤走一遍完整流程，每步截图，记录 API 调用
3. **记录发现**：页面导航路径、关键元素选择器、API 接口、隐藏行为、**编写或更新 Page Object**

### 完成标准

- [ ] 每个涉及的页面都有截图
- [ ] 理解了页面间的导航路径
- [ ] 确认了关键元素的选择器
- [ ] 记录了实际的 API 请求
- [ ] 发现了隐藏行为（隐藏字段、默认值、前置条件）
- [ ] 已编写或更新了对应的 Page Object

### 探索测试代码模板

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

---

## 工作流一：手动用例 → 自动化代码

> **前提**：已完成工作流零（业务熟悉），对目标功能有充分认知。

### 步骤

1. **解析测试用例**：从 markmap Markdown 提取场景与预期
2. **选择/新建 Page Object**：检查 `tests/pages/` 下是否已有对应 Page Object，优先复用
3. **编写 spec**：使用 Page Object 封装所有页面交互
4. **运行验证**：`npx playwright test tests/{文件名}.spec.ts`

### 场景类型与代码模板

#### CRUD 操作

```typescript
test.describe('{模块名}', () => {
  let createdName: string;

  test.beforeEach(async ({ page }) => {
    // 登录 + 进入页面
  });

  test.afterEach(async ({ page }) => {
    if (createdName) {
      await pageObject.deleteResource(createdName).catch(() => {});
    }
  });

  test('TC-XXX: {用例描述}', async ({ page }) => {
    createdName = `{前缀}-${Date.now()}`;
    await pageObject.createResource(createdName);

    const row = await pageObject.getResourceByName(createdName);
    expect(row).not.toBeNull();
    await expect(row!).toBeVisible();
  });
});
```

#### 表单提交

```typescript
test('TC-XXX: {用例描述}', async ({ page }) => {
  // 1. 监听网络请求（必须在操作之前）
  let apiCalled = false;
  page.on('request', req => {
    if (req.url().includes('/api/target') && req.method() === 'POST') {
      apiCalled = true;
    }
  });

  // 2. 填充表单（受控组件用 keyboard.type，不用 fill，详见速查表）
  const input = page.locator('#field');
  await input.click();
  await page.keyboard.type('值', { delay: 50 });
  await input.blur();

  // 3. 提交
  await page.getByRole('button', { name: '提交' }).click();

  // 4. 验证 API 调用 + 持久化
  await page.waitForTimeout(2000);
  expect(apiCalled).toBe(true);
  await page.reload();
  await expect(page.getByText('值')).toBeVisible();
});
```

#### 状态流转

```typescript
test('TC-XXX: {用例描述}', async ({ page }) => {
  // 前置：用对应 Page Object 创建一条可操作的业务数据
  const { resourceName } = await createResourceWithData(page, 'TC-STATUS');
  await xxxPage.performAction();
  await expect(page.getByText('<目标状态文案>')).toBeVisible();
});
```

#### 多用户并发

```typescript
test('TC-XXX: {用例描述}', async ({ browser }) => {
  // 创建两个独立会话（各自登录不同角色），见「通用 Helper 参考实现」
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

### Page Object 编写规范

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
    // 受控组件表单用 keyboard.type
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

### 测试数据管理

- **常量数据**：放 `constants.ts`（账号、URL、状态枚举）
- **CSV 数据**：放 `test-data/` 目录
- **动态数据**：在测试中用 `Date.now()` 生成唯一名称

### spec 文件命名

| 类型 | 命名 | 示例 |
|------|------|------|
| 正式测试 | `{序号}-{模块}.spec.ts` | `01-resource-creation.spec.ts` |
| 探索测试 | `explore-{功能}.spec.ts` | `explore-config.spec.ts`（**临时文件**） |

---

## 工作流二：Bug 探索与记录

在已理解业务逻辑的前提下，系统性验证页面功能，发现 Bug 和不一致。

### Bug 发现策略

| 策略 | 检查方式 | 典型 Bug |
|------|---------|---------|
| UI 预期不一致 | 对比测试用例与实际截图 | 默认值不对、文案错误 |
| 表单校验缺失 | 提交非法数据 | 必填不校验、范围不限制 |
| 网络异常 | 监听 API 响应 | 500 错误、超时 |
| 数据不一致 | 操作后 reload 验证 | 提交成功但数据丢失 |
| 状态流转错误 | 多步操作验证状态 | 状态未更新、卡死 |
| 控制台错误 | `setupConsoleLogging(page)` 持续监听 | 组件崩溃、静默失败 |

### Bug 证据收集（发现 Bug 时必须执行）

```
Bug 发现 → 截图操作前 → 操作触发异常 → 截图操作后 → 收集 API/控制台日志 → 写入报告
```

```typescript
test('测试中发现 Bug', async ({ page }, testInfo) => {
  const tracker = setupBugTracking(page);
  await new LoginPage(page).loginAs('admin');

  // 截图 1：操作前
  await page.screenshot({ path: 'bug-001-01-操作前.png', fullPage: true });

  // 触发异常的操作
  await page.getByRole('button', { name: '保存' }).click();
  await page.waitForTimeout(2000);

  // 截图 2：异常现象
  await page.screenshot({ path: 'bug-001-02-异常.png', fullPage: true });

  // 收集完整证据（截图 + API + 控制台）
  const evidence = await tracker.collect(testInfo, 'BUG-001', '保存失败无提示');
});
```

### Bug 报告格式

记录在 `{项目名}/测试报告_{来源}.md`：

```markdown
### BUG-{序号}: {简要描述}

- **严重程度**: P0 / P1 / P2
- **发现方式**: 自动化测试 / 探索性测试
- **复现步骤**:
  1. 以 {角色} 登录
  2. 进入 {页面} ({URL})
  3. {具体操作}
- **预期行为**: {根据需求文档/测试用例}
- **实际行为**: {观察到的实际现象}
- **证据**: 截图 `bug-{序号}-*.png` | API: `{METHOD} {URL} → {状态码}` | 控制台: `{错误}`
- **环境**: {URL} / {账号角色} / {浏览器}
```

---

## 通用 Helper 参考实现

工作流中反复使用的通用工具函数（登录、多用户会话、API/控制台监听、Bug 证据收集、服务端崩溃检测）建议集中放在 `tests/helpers.ts`。下面是**脱敏后的通用参考实现**，可直接作为起点，按你的系统调整选择器、登录后跳转规则和 token 存储位置。

> 业务专有的"造数"函数（如创建某类业务实体并灌入测试数据）请基于你的 Page Object 自行实现，不要塞进通用 helpers。

```typescript
// tests/helpers.ts
import { Page, Locator, Browser, BrowserContext, TestInfo } from '@playwright/test';
import { BASE_URL, ACCOUNTS } from './constants';

type Role = keyof typeof ACCOUNTS;
type ApiEntry = { method: string; url: string; status?: number; body?: string };

/** 登录页 Page Object。按你的系统调整选择器和登录后跳转规则。 */
export class LoginPage {
  readonly page: Page;
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.usernameInput = page.getByPlaceholder('请输入用户名'); // 按实际页面调整
    this.passwordInput = page.getByPlaceholder('请输入密码');
    this.submitButton = page.getByRole('button', { name: /登\s*录/ });
  }

  async goto() {
    await this.page.goto(`${BASE_URL}/<登录页路由>`);
    await this.page.waitForLoadState('networkidle');
  }

  /** 按角色登录，角色名对应 constants.ts 中 ACCOUNTS 的 key */
  async loginAs(role: Role) {
    const { username, password } = ACCOUNTS[role];
    await this.goto();
    // 用 keyboard.type 而非 fill，兼容受控组件（Ant Design / React 表单）
    await this.usernameInput.click();
    await this.page.keyboard.type(username, { delay: 30 });
    await this.passwordInput.click();
    await this.page.keyboard.type(password, { delay: 30 });
    // 登录后等待跳转离开登录页（按你的系统调整预期 URL）
    await Promise.all([
      this.page.waitForURL(/\/(dashboard|home|task-center)/, { timeout: 15000 }),
      this.submitButton.click(),
    ]);
  }
}

/** 创建两个独立会话（各自登录指定角色），用于多用户并发场景 */
export async function createDualSession(browser: Browser, roleA: Role, roleB: Role) {
  const contextA = await browser.newContext();
  const contextB = await browser.newContext();
  const pageA = await contextA.newPage();
  const pageB = await contextB.newPage();
  await new LoginPage(pageA).loginAs(roleA);
  await new LoginPage(pageB).loginAs(roleB);
  return { pageA, pageB, contextA, contextB };
}

/** 创建 N 个角色的会话（多角色场景） */
export async function createMultiSession(browser: Browser, roles: Role[]) {
  const sessions: Array<{ page: Page; context: BrowserContext; role: string }> = [];
  for (const role of roles) {
    const context = await browser.newContext();
    const page = await context.newPage();
    await new LoginPage(page).loginAs(role);
    sessions.push({ page, context, role });
  }
  return sessions;
}

/** 安全关闭若干浏览器上下文（忽略已关闭的） */
export function closeContexts(...contexts: (BrowserContext | null)[]) {
  return Promise.all(
    contexts.filter((c): c is BrowserContext => !!c).map(c => c.close().catch(() => {})),
  );
}

/** 监听 /api/ 请求与响应，返回累积的 API 日志数组 */
export function setupApiLogging(page: Page): ApiEntry[] {
  const apiLog: ApiEntry[] = [];
  page.on('request', req => {
    if (req.url().includes('/api/')) {
      const entry: ApiEntry = { method: req.method(), url: req.url() };
      if (req.method() === 'POST') entry.body = req.postData() ?? undefined;
      apiLog.push(entry);
    }
  });
  page.on('response', resp => {
    const entry = apiLog.find(e => e.url === resp.url() && !e.status);
    if (entry) entry.status = resp.status();
  });
  return apiLog;
}

/** 监听控制台错误与未捕获异常，返回错误信息数组 */
export function setupConsoleLogging(page: Page): string[] {
  const consoleErrors: string[] = [];
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', err => consoleErrors.push(`Uncaught: ${err.message}`));
  return consoleErrors;
}

/** 检测页面文本中是否出现服务端错误（500/502 等） */
export function isServerCrash(text: string): boolean {
  return /HTTP\s*500|500|502\s*Bad\s*Gateway|Internal\s*Server\s*Error|服务器内部错误/i.test(text);
}

export interface BugEvidence {
  id: string;
  description: string;
  screenshots: string[];
  apiCalls: ApiEntry[];
  consoleErrors: string[];
  currentUrl: string;
  pageTitle: string;
}

/** 收集 Bug 证据：截图 + attach 到报告 + 记录 URL/标题/API/控制台 */
export async function collectBugEvidence(
  page: Page,
  testInfo: TestInfo,
  bugId: string,
  description: string,
  options: { apiLog?: ApiEntry[]; consoleErrors?: string[]; fullPage?: boolean } = {},
): Promise<BugEvidence> {
  const fullPage = options.fullPage ?? true;
  const screenshotPath = `${bugId}.png`;
  const buffer = await page.screenshot({ path: screenshotPath, fullPage });
  await testInfo.attach(`${bugId}: ${description}`, { body: buffer, contentType: 'image/png' });
  return {
    id: bugId,
    description,
    screenshots: [screenshotPath],
    apiCalls: options.apiLog ? [...options.apiLog] : [],
    consoleErrors: options.consoleErrors ? [...options.consoleErrors] : [],
    currentUrl: page.url(),
    pageTitle: await page.title(),
  };
}

/** 一站式 Bug 跟踪：注册 API + 控制台监听，提供 collect() 一键收集证据 */
export function setupBugTracking(page: Page) {
  const apiLog = setupApiLogging(page);
  const consoleErrors = setupConsoleLogging(page);
  return {
    apiLog,
    consoleErrors,
    async collect(
      testInfo: TestInfo,
      bugId: string,
      description: string,
      options?: { fullPage?: boolean },
    ) {
      return collectBugEvidence(page, testInfo, bugId, description, {
        apiLog: [...apiLog],
        consoleErrors: [...consoleErrors],
        ...options,
      });
    },
  };
}

/** （进阶）用浏览器内 fetch 携带认证 token 调用 API：绕过 UI 直接造数据或校验后端 */
export async function apiFetch(page: Page, path: string, options?: RequestInit) {
  const token = await page.evaluate(() => {
    const raw = localStorage.getItem('<你的 token 存储 key>'); // 按实际调整
    try {
      return raw ? (JSON.parse(raw).token ?? raw) : null;
    } catch {
      return null;
    }
  });
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options?.headers as Record<string, string>) ?? {}),
  };
  if (token) headers['Authorization'] = token.startsWith('Bearer ') ? token : `Bearer ${token}`;
  return page.evaluate(
    async ({ url, opts }) => {
      const resp = await fetch(url, opts);
      return { status: resp.status, body: await resp.text() };
    },
    { url: `${BASE_URL}${path}`, opts: { ...options, credentials: 'include' as RequestCredentials, headers } },
  );
}
```

---

## Explore 文件生命周期管理

探索性测试文件是**临时产物**，遵循以下生命周期：

```
创建 explore-xxx.spec.ts → 提取知识到 Page Object → 删除 explore 文件 + 截图
```

### 规则

1. **知识提取后立即删除**：将发现的选择器、API 路径、页面结构写入 Page Object 或 helpers 后，删除 explore 文件
2. **截图清理**：探索产生的 `debug-*.png` 截图是临时调试产物，确认不需要后删除
3. **不积累**：`tests/` 目录下不应存在已完成的 explore 文件。如果存在，说明知识提取步骤被跳过了
4. **Bug 报告截图保留**：`bug-{序号}-*.png` 截图属于 Bug 报告的一部分，不删除

---

## 关键技巧速查表

| 场景 | 方法 | 备注 |
|------|------|------|
| 受控组件输入框（Ant Design 等） | `keyboard.type()` | 不用 `fill()`，避免不触发校验 |
| 隐藏必填字段 | `page.evaluate()` 直接设值 | 阻止表单提交的常见原因 |
| 网络请求验证 | `page.on('request')` 监听 | 必须在操作之前设置 |
| 数据持久化验证 | `page.reload()` + 断言 | 确认数据真正保存 |
| 多用户会话 | `createDualSession(browser, roleA, roleB)` | 两个角色并发 |
| 等待策略 | `waitForLoadState('networkidle')` | 优于固定 `waitForTimeout` |
| 截图调试 | `page.screenshot({ fullPage: true })` | 每个关键步骤都截图 |
| 服务端崩溃检测 | `isServerCrash(bodyText)` | 检测 500/502 错误 |
| 唯一命名 | `${前缀}-${Date.now()}` | 避免测试间名称冲突 |
| Bug 证据收集 | `tracker.collect(testInfo, id, desc)` | 一键收集截图+API+控制台 |
| Bug 探索前置 | `setupBugTracking(page)` | 注册 API 和控制台监听 |

## Common Mistakes

| 错误 | 后果 | 正确做法 |
|------|------|---------|
| `fill()` 用于受控组件表单 | 校验不通过，表单无法提交 | 用 `keyboard.type()` |
| 网络监听放在 click 之后 | 捕捉不到请求 | 先注册 listener，再执行操作 |
| 不清理测试数据 | 后续测试受影响 | afterEach 中删除创建的资源 |
| 用固定 timeout 等待 | 时序不稳定 | 优先用 `waitForLoadState` / `waitForResponse` |
| 不验证持久化 | 数据可能只存在内存 | reload 后重新断言 |
| 正式测试不使用 Page Object | 代码重复，难以维护 | 所有页面交互封装在 Page Object 中 |
| explore 文件不删除 | 上下文污染，AI 每次读大量废代码 | 知识提取后立即删除 |
| 遇到疑问自行假设 | 产出不可靠的测试 | 不确定就向用户提问 |
| Bug 只截图不记录 API/控制台 | 开发无法定位根因 | 用 `setupBugTracking()` + `tracker.collect()` |
| 硬编码环境地址/账号 | 无法跨环境运行、泄露敏感信息 | 统一放 `constants.ts` / `.env`，代码只引用常量 |

---

## 与其他 skill 配合

本 skill 的输入是**手动测试用例**（markmap Markdown）。当还没有测试用例、需要从需求/设计文档先编写时，使用 `test-case-writing` skill，形成「用例编写 → 自动化执行」的闭环。
