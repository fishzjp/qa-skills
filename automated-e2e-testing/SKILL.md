---
name: automated-e2e-testing
description: 当需要将手动测试用例转为 Playwright E2E 测试并执行、在写自动化前对 Web 应用做小规模业务熟悉探索（踩点）、编写 Page Object/Helper，或在自动化执行中收集 Bug 证据并记录测试报告条目时使用。不用于：纯 API 接口测试（api-testing）、以理解系统/发现风险为目的的独立探索会话（exploratory-testing）、已确认 Bug 的根因分析（bug-analysis）。
---

# 自动化 E2E 测试

## Overview

本 skill 覆盖 Web 应用自动化测试的完整工作流：将手动测试用例（markmap + Schema）转化为 Playwright spec → 运行并验证 → 发现 Bug → 输出测试报告。

核心原则：
1. **先熟悉业务再写测试** — 对功能不熟悉时，先用自动化脚本主动探索系统，理解实际行为后再动手写测试代码
2. **有疑问就提问，不自行假设** — 编写过程中遇到任何不明确的地方，必须向用户提问澄清，绝不凭猜测写代码
3. **每条自动化用例对应一条手动用例，每条 test 只测一个点**
4. **每个 test 独立**（自建数据 + 自清理）
5. **必须使用 Page Object** — 正式测试中禁止裸写定位器，所有页面交互封装在 Page Object 中

## When to Use

- 给定测试用例（markmap / Schema），需要生成 Playwright spec 文件并执行
- 编写自动化前，需要小规模业务熟悉探索（踩点页面结构、提取选择器）
- 自动化执行中发现 Bug，需要收集证据并记录测试报告条目
- 需要编写新的 Page Object 或 Helper 函数

## When NOT to Use

- 端到端测试整个需求（理解→策略→用例→执行→报告的流水线）→ 用 `qa` skill 编排
- 编写手动测试用例 → 用 `test-case-writing` skill
- 纯 API 接口测试（无 Web UI 流程）→ 用 `api-testing` skill
- 以**理解系统 / 发现风险**为目的的独立探索式测试会话（charter 驱动、产出探索笔记）→ 用 `exploratory-testing` skill；本 skill 的工作流零只做「为写自动化踩点」的小规模探索
- 已确认 Bug 的根因定位、影响分析、回归建议 → 用 `bug-analysis` skill；本 skill 只负责收集 Bug 证据（截图/API/控制台）并记录报告条目
- 代码变更后判断回归范围 → 用 `regression-testing` skill
- 单元测试 → 用 Jest/Vitest；性能压测 → 专业工具（k6、locust）；安全测试 → 安全审计专项（见 `test-strategy` 的 handoff 约定）

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

> 以上命令依赖 package.json 的 scripts 定义（新项目需配置）：
> ```json
> "scripts": {
>   "test": "playwright test",
>   "test:headed": "playwright test --headed",
>   "show-report": "playwright show-report"
> }
> ```

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
│   └── explore-{功能}.spec.ts # 业务熟悉探索（临时）
└── test-data/                 # CSV 等测试数据
```

### Playwright 配置

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

---

## 工作流零：业务熟悉（前置必做，为写自动化踩点的小规模探索）

**何时需要**：从未测试过该功能模块 / 出现不熟悉的页面路由 / 需要编写新的 Page Object / 拿到用例但不知道系统长什么样

> 本工作流是**小规模踩点探索**（理解页面结构、提取选择器、落 Page Object），产出服务于工作流一。以理解系统 / 发现风险为目的的**完整探索会话**（charter 驱动、产出探索笔记）用 `exploratory-testing` skill。

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

### 用例输入与自动化范围判定

输入是 `test-case-writing` 产出的 markmap 用例文件（如含 `测试用例.schema.yaml` 则一并消费）：

- Schema 的 `execution_model: ui` 且 `automation.supported != no` 的用例 → 本工作流的转换对象
- `execution_model: dev-collab`（无 UI 协作用例）→ 移交 `api-testing` 或保持手动协作执行，不硬造 UI 自动化
- `automation_plan` 存在时（`test-strategy` 产出）按用户的执行策略裁决执行；策略未定时向用户确认哪些用例转自动化

### 步骤

1. **解析测试用例**：从 markmap Markdown 提取场景与预期；test 名沿用用例的 TC 编号（如 `TC-01-03: {用例名称}`），手动用例缺编号时先补编号再转换
2. **选择/新建 Page Object**：检查 `tests/pages/` 下是否已有对应 Page Object，优先复用
3. **编写 spec**：使用 Page Object 封装所有页面交互
4. **运行验证**：`npx playwright test tests/{文件名}.spec.ts`

### 场景类型与代码模板

#### CRUD 操作

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

#### 表单提交

```typescript
test('TC-01-02: {用例描述}', async ({ page }) => {
  // 1. 先注册响应等待（必须在操作之前；勿用固定 waitForTimeout，见 Common Mistakes）
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

#### 状态流转

```typescript
test('TC-01-03: {用例描述}', async ({ page }) => {
  // 前置：用对应 Page Object 创建一条可操作的业务数据
  const { resourceName } = await createResourceWithData(page, 'TC-STATUS');
  await xxxPage.performAction();
  await expect(page.getByText('<目标状态文案>')).toBeVisible();
});
```

#### 多用户并发

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

> 职责边界：本工作流负责**发现 + 证据收集 + 报告条目**。Bug 被**确认**后的根因定位、影响分析、回归建议移交 `bug-analysis` skill（对应报告条目中"根因分析 / 回归建议"两段留 TODO）。

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

截图命名统一小写 `bug-{序号}-*` 前缀：手动截图记录过程两态（`bug-001-01-操作前.png`、`bug-001-02-异常.png`）；`tracker.collect()` 自动补一张整页汇总截图（`bug-001-汇总.png`）并 attach 到 HTML 报告。Bug 报告标题中的 `BUG-{序号}` 仅为显示格式。

### Bug 报告格式

记录在 `{项目名}/测试报告_{来源}_{日期}.md`，**字段与 `../core/report-template.md`（测试报告唯一来源模板）的 §3 Bug 清单保持一致**，保证条目可直接拼装进 `qa` 收尾的最终报告。执行分报告还需包含 §2 执行统计（P0/P1/P2 × 用例数/通过/失败/阻塞/未执行表，同样按 report-template）：

```markdown
### BUG-{序号}: {简要描述}

- **严重程度**: P0 / P1 / P2
- **发现方式**: 自动化测试 / 探索性测试 / 业务熟悉探索 / 手动执行 / 代码审查（Cx 转）
- **复现步骤**:
  1. 以 {角色} 登录
  2. 进入 {页面} ({URL})
  3. {具体操作}
- **预期行为**: {根据需求文档/测试用例 TC 编号}
- **实际行为**: {观察到的实际现象}
- **证据**: 截图 `bug-{序号}-*.png` | API: `{METHOD} {URL} → {状态码}` | 控制台: `{错误}`
- **环境**: {URL} / {账号角色} / {浏览器}
- **根因分析**: TODO（Bug 确认后由 `bug-analysis` 填写）
- **回归建议**: TODO（由 `bug-analysis` 填写）
```

---

## 通用 Helper 参考实现

工作流中反复使用的通用工具函数（登录、多用户会话、API/控制台监听、Bug 证据收集、服务端崩溃检测）建议集中放在 `tests/helpers.ts`。落地时**加载本 skill 的 `references/helpers_reference.md`**：其中的脱敏参考实现可直接作为起点，按你的系统调整选择器、登录后跳转规则和 token 存储位置。

> 业务专有的"造数"函数（如创建某类业务实体并灌入测试数据）请基于你的 Page Object 自行实现，不要塞进通用 helpers。

---

## Explore 文件生命周期管理

业务熟悉探索文件（explore-xxx.spec.ts）是**临时产物**，遵循以下生命周期：

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
| 受控组件输入框（Ant Design 等） | `fill()` 优先，不生效再 `keyboard.type()` | `fill` 会派发 input 事件，多数受控组件可用；`keyboard.type` 逐键最稳但慢 |
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
| 受控组件值不生效仍反复 `fill()` | 测试卡死或断言失败 | `fill` 失效时改用 `keyboard.type()`（见速查表） |
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

- **上游**：`test-case-writing` 产出手动用例（markmap + Schema）→ 本 skill 把 `execution_model: ui` 且可自动化的用例变成可执行代码；端到端流水线由 `qa` 编排
- **旁路**：无文档 / 系统陌生的**完整探索会话**用 `exploratory-testing`，其探索笔记可作为本 skill 踩点的输入
- **下游**：Bug 确认后的根因 / 影响 / 回归分析 → `bug-analysis`；执行报告与 Bug 条目按 `../core/report-template.md` 对齐，供 `qa` 收尾汇总
- **平级**：纯 API 用例的自动化 → `api-testing`
