# 通用 Helper 参考实现（脱敏）

落地 `tests/helpers.ts` 时可直接复制以下代码作为起点，按你的系统调整选择器、登录后跳转规则和 token 存储位置。

> 业务专有的"造数"函数（如创建某类业务实体并灌入测试数据）请基于你的 Page Object 自行实现，不要塞进通用 helpers。

```typescript
// tests/helpers.ts
import * as fs from 'node:fs';
import { Page, Locator, Request, Browser, BrowserContext, TestInfo } from '@playwright/test';
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
    // 登录失败难兜底，为最大兼容用 keyboard.type；常规表单 fill 优先（见 SKILL.md 速查表）
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

/** 认证态缓存目录。含登录凭据，务必加入 .gitignore（见 references/playwright-conventions.md 第 10 节） */
const AUTH_DIR = '.auth';

/** 把当前已登录页面的认证态落盘为 .auth/{role}.json，返回缓存文件路径 */
export async function saveLoginState(page: Page, role: Role) {
  fs.mkdirSync(AUTH_DIR, { recursive: true });
  const file = `${AUTH_DIR}/${role}.json`;
  await page.context().storageState({ path: file });
  return file;
}

/** 创建已登录会话：优先复用 storageState 缓存；缺失/失效时回退 UI 登录并刷新缓存。
 *  每个用例独立创建会话，替代裸 createMultiSession 的全量 UI 登录，显著缩短执行时长 */
export async function createSession(browser: Browser, role: Role) {
  const file = `${AUTH_DIR}/${role}.json`;
  let session: { page: Page; context: BrowserContext } | null = null;

  if (fs.existsSync(file)) {
    const context = await browser.newContext({ storageState: file });
    const page = await context.newPage();
    // 探测访问首页；被重定向到登录页说明缓存失效（跳转特征按你的系统调整）
    await page.goto(`${BASE_URL}/`);
    if (!/login/i.test(page.url())) {
      session = { page, context };
    } else {
      await closeContexts(context);
      fs.rmSync(file, { force: true }); // 删除过期缓存，走下方 UI 登录分支重建
    }
  }

  if (!session) {
    const context = await browser.newContext();
    const page = await context.newPage();
    await new LoginPage(page).loginAs(role);
    await saveLoginState(page, role); // 首次 UI 登录成功后刷新缓存
    session = { page, context };
  }
  return session;
}

/** 监听 /api/ 请求与响应，返回累积的 API 日志数组 */
export function setupApiLogging(page: Page): ApiEntry[] {
  const apiLog: ApiEntry[] = [];
  // 用 Request 对象关联请求与响应，避免同 URL 并发请求时状态码错配
  const entryByRequest = new Map<Request, ApiEntry>();
  page.on('request', req => {
    if (!req.url().includes('/api/')) return;
    const entry: ApiEntry = { method: req.method(), url: req.url() };
    if (req.method() === 'POST') entry.body = req.postData() ?? undefined;
    apiLog.push(entry);
    entryByRequest.set(req, entry);
  });
  page.on('response', resp => {
    const entry = entryByRequest.get(resp.request());
    if (entry) {
      entry.status = resp.status();
      entryByRequest.delete(resp.request());
    }
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

/** 检测页面文本中是否出现服务端错误（5xx）。
 *  避免裸匹配「500」造成误报（如「共 1500 条」「¥500」），只匹配带上下文的形式 */
export function isServerCrash(text: string): boolean {
  return (
    /HTTP\s*5\d{2}/.test(text) || // HTTP 500 / HTTP 502
    /\b5\d{2}\b\s*(?:Bad\s*Gateway|Internal\s*Server\s*Error)/i.test(text) || // 502 Bad Gateway（无 HTTP 前缀）
    /Internal\s*Server\s*Error|Bad\s*Gateway|服务器内部错误|网关错误/i.test(text)
  );
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

/** 收集 Bug 证据：截图 + attach 到报告 + 记录 URL/标题/API/控制台。
 *  截图命名与手动过程截图统一为小写 bug-{序号}-* 前缀（bugId 传 'BUG-001' 时存为 bug-001-汇总.png） */
export async function collectBugEvidence(
  page: Page,
  testInfo: TestInfo,
  bugId: string,
  description: string,
  options: { apiLog?: ApiEntry[]; consoleErrors?: string[]; fullPage?: boolean } = {},
): Promise<BugEvidence> {
  const fullPage = options.fullPage ?? true;
  const screenshotPath = `${bugId.toLowerCase()}-汇总.png`;
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
