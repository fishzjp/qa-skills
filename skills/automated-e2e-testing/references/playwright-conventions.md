# Playwright 工程约定与代码模板

> **路径口径**：本文档内 `../core/...`、`references/...` 等相对路径按消费方 SKILL.md 所在目录（`skills/automated-e2e-testing/`）解析书写，不是相对本文件。

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
  fullyParallel: false,       // 默认串行（保守起点）；用例独立性达标后按第 11 节渐进开启并行
  timeout: 60_000,            // 单个测试超时 60s
  retries: process.env.CI ? 1 : 0, // 本地零重试暴露问题；CI 至多重试 1 次，重跑变绿仍要按第 11 节定性 flaky
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

## 9. 等待策略与降级阶梯

Playwright 操作自带 auto-wait，`expect(locator)` 断言自带轮询重试。显式等待手段按下表**自上而下优先**选用：

| 层级 | 手段 | 适用 |
|------|------|------|
| ① | auto-wait + `expect(locator).toBeVisible()` 等 | 绝大多数交互与断言 |
| ② | `page.waitForResponse()` / `waitForURL()` 先注册再操作 | 提交/跳转类操作的确定性收口 |
| ③ | `waitForLoadState('networkidle')` | 传统 SSR/MPA 页面的聚合加载收尾 |
| ④ | 固定 `waitForTimeout` | 仅临时调试，禁止提交进正式 spec |

**networkidle 失效场景必须降级**：页面存在 WebSocket/SSE 长连接、轮询心跳（监控上报、IM 未读数、灰度打点）时网络"永不空闲"，等待会一直超时到 test timeout。降级方式：找到该操作真正触发的关键接口改用层级 ②；无确定接口时把验证交给层级 ① 的断言自动轮询。不确定是否存在长连接时，向用户提问而不是套 ④。

## 10. 认证态复用（storageState）

大量用例都从登录页走完整 UI 登录会显著拉长执行时长。做法：首次 UI 登录成功后把上下文认证态落盘为 `.auth/{role}.json`；后续会话优先复用缓存——访问任一路径确认未被踢回登录页即视为有效；被踢回登录页（token 过期、登录流程变更）则删除缓存、回退 UI 登录并刷新缓存。

helper 参考实现（`saveLoginState` / `createSession`）见 `references/helpers_reference.md`。注意两点：

- `.auth/` 目录含登录凭据，**必须加入 `.gitignore`**
- 多用户并发场景（`createDualSession`）各角色各自走一遍缓存复用即可，互不影响

## 11. flaky 治理与 CI 接入

### flaky 二次确认规则

- **定性**：一条用例首次失败、原样重跑通过 → 判为 first-run-flaky，**不算稳定通过**；原样重跑只用于定性，不得成为常态化通过手段
- 定性后立即定位：回看 trace（第 3 节配置已开 `retain-on-failure`）、对比失败前后截图与 API 日志；常见根因是竞态等待不足（按第 9 节修正）或数据残留（清理不彻底）
- 修复前的处置：短期标 `test.fixme` 防止污染主干绿灯，修复后恢复
- **禁止**靠调大 retries 或调大超时让用例"变绿"

### 并行开启条件

本 skill 核心原则要求每条 test 独立（自建数据 + 自清理）——独立性达标后就没有理由永久串行：

- 开启前逐项核对：动态数据全部 `${前缀}-${Date.now()}` 唯一命名；afterEach 清理齐全；无跨用例共享可变状态；无互斥业务约束（如同一单据只能一人操作）
- 渐进开启：先以 `npx playwright test tests/{模块目录} --workers=2` 小并发观察一轮，稳定后在配置中上调 `workers`
- 有顺序依赖的遗留用例：用 `test.describe.configure({ mode: 'serial' })` 局部圈住，不阻塞其余并行

### CI 接入要点

- **报告产物**：HTML 报告供 artifact 下载查看；需平台解析时另配 JUnit 输出：

```typescript
// playwright.config.ts 增补
reporter: [
  ['html', { open: 'never' }],
  ['junit', { outputFile: 'results.xml' }],
],
```

- **触发策略**：合入前流水线只跑受影响模块目录；夜间任务跑全量
- **变量注入**：环境地址与账号沿用第 2 节约定，CI 上经变量/密钥注入，不入库
- 最小 GitHub Actions 片段：

```yaml
# .github/workflows/e2e.yml 关键步骤
- uses: actions/setup-node@v4
  with: { node-version: 20 }
- run: npm ci && npx playwright install --with-deps chromium
  working-directory: playwright
- run: npm test
  working-directory: playwright
- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: playwright-report
    path: playwright/playwright-report/
```

## 12. 类型域执行层之一：无障碍扫描（轴 6 accessibility）

类型矩阵轴 6 决策 include 时按本节接入（决策与档位来自 test-strategy 的 type_scope，本节只管执行形态）；报告回收走 report-template §7 表，执行方列如实填 axe-core。

一次性安装：

```bash
npm i -D @axe-core/playwright
```

helper 封装（放 `tests/helpers/axe.ts`，一条命令接入的落地形态）：

```typescript
/**
 * runAxeScan —— 对当前页面执行 axe 可访问性扫描，
 * 只返回 critical / serious 阻断级违规的结构化清单，供分流表或 Cx 条目直接引用
 */
import AxeBuilder from '@axe-core/playwright';
import type { Page } from '@playwright/test';

export async function runAxeScan(page: Page, label: string): Promise<string> {
  const results = await new AxeBuilder({ page }).analyze();
  const blocking = results.violations.filter(
    v => v.impact === 'critical' || v.impact === 'serious'
  );
  if (!blocking.length) return `${label} — 无阻断级违规`;
  const lines = blocking.flatMap(v => [
    `[${v.impact}] ${v.id}: ${v.help}`,
    ...v.nodes.slice(0, 5).map(n => `    ${n.target.join(' ')}`),
  ]);
  return `${label} — ${blocking.length} 类阻断级违规:\n${lines.join('\n')}`;
}
```

处置纪律：
- **分级判定**：critical / serious 计缺陷条目（critical 影响主流程可达性时 Severity 从 S1 起）；moderate / minor 进观察清单不计 Bug——对比度阈值争议、读屏体验等主观项标人工复核（矩阵轴 6 边界条款）
- light 档只扫 type_scope 给定的 P0 页面集，逐页出违规清单条目（Cx 通道）；standard 档扩展到主要页面全集 + 关键流键盘走查（Tab 遍历、断言焦点态可见）
- 扫描失败页面本身可渲染才可信——白屏页上的 axe 结果没有意义，先排除环境故障

## 13. 类型域执行层之二：视觉基线（轴 7 visual）

配置增补（playwright.config.ts）：

```typescript
export default defineConfig({
  // 截图基线独立目录：便于 CI 工件上传规则通配
  snapshotPathTemplate: '{testDir}/__screenshots__/{testFileName}/{arg}{ext}',
  expect: {
    toHaveScreenshot: { maxDiffPixelRatio: 0.02 },   // 2% 容差起步，按页面校准收紧
  },
});
```

用例形态：

```typescript
// TC-07-01: 订单列表页视觉基线比对（fullPage 整页基准）
await expect(page).toHaveScreenshot('TC-07-01-full.png', { fullPage: true });
```

三条硬纪律（矩阵轴 7 防 flaky 条款同源）：
- **动态区必须声明 mask**——时间戳、头像、随机推荐位、广告轮播不遮必炸，这是纪律不是技巧：

```typescript
await expect(page).toHaveScreenshot('dashboard.png', {
  fullPage: true,
  mask: [
    page.locator('[data-testid="timestamp"]'),
    page.locator('.recommend-feed'),
  ],
});
```

- **未声明遮罩规则的 diff 失败不判 Bug**：先进 S 级复核区分动态内容干扰还是真实回归（走 `../core/triage.md` 个体定性路径后再下结论）
- 基线更新只能 `npx playwright test --update-snapshots`，且**仅在分流判 B1（预期变更附依据）之后执行**——拿到红灯就重录基线等于把真回归洗白成绿灯；light 档不自动 diff，只截图存档供人比对

## 14. 类型域执行层之三：多浏览器兼容（轴 5 compatibility）

配置增补（playwright.config.ts）。Playwright 原生引擎为 chromium/firefox/webkit，Edge 由 chromium channel 派生——恰好覆盖 light 档「最新 Chrome/Safari/Edge/Firefox 冒烟」定义：

```typescript
export default defineConfig({
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
    { name: 'msedge', use: { channel: 'msedge' } },
  ],
});
```

档位对接（depth 来自 type_scope，不为档位发明新语义）：
- light → 四 project × P0 冒烟子集：`npx playwright test tests/smoke/ --project=chromium --project=firefox --project=webkit --project=msedge`
- standard → 需求支持清单对应的 project 子集 × P0 路径（不在支持清单内的浏览器不加 project）
- full → 浏览器 × 分辨率矩阵逐格，分辨率经 `use: { viewport: {...} }` 维度展开

成本纪律：本地开发固定 `--project=chromium` 收敛反馈环；多浏览器留给流水线夜间档跑（非交互产物与退出码约定见 `../core/pipeline-integration.md`）——单浏览器本地 + 多浏览器 CI 是多浏览器成本的业界默认切分，全量永远并行只会让反馈环烂掉。
