# 任务：将手动用例转为 Playwright 自动化测试

你是测试工程师。请根据下方的手动测试用例与项目脚手架，编写 Playwright 测试代码（spec + 需要的 Page Object），直接输出全部代码文件内容（每个文件给出文件名与完整路径）。

只需编写代码，无需运行。

---

## 输入材料

### 材料 1：手动测试用例（markmap 节选）

```markdown
## 1. 项目管理

> 前置：管理员账号已登录，进入「控制台 → 项目」页

- **TC-01-01 创建项目** [P0]（SMOKE-1）
  - 操作步骤: 1. 点击「新建项目」按钮 2. 名称填"自动化测试项目-0721" 3. 点击「确定」
  - 预期结果: 列表出现名称为"自动化测试项目-0721"的卡片
- **TC-01-02 搜索项目** [P1]
  - 操作步骤: 1. 在搜索框输入"自动化测试项目-0721" 2. 按回车
  - 预期结果: 列表仅显示该项目（其他项目不显示）
- **TC-01-03 删除项目** [P1]
  - 前置条件: 列表中存在"自动化测试项目-0721"
  - 操作步骤: 1. 该项目卡片点击「更多」→「删除」 2. 确认弹窗点击「删除」
  - 预期结果: 列表不再显示该项目；刷新页面后仍不存在
```

### 材料 2：项目脚手架（已存在，勿重复输出，按此引用）

```typescript
// tests/constants.ts（已存在）
export const BASE_URL = process.env.TEST_BASE_URL ?? 'https://console.example.test';
export const ACCOUNTS = {
  admin: { username: process.env.ADMIN_USER ?? 'admin', password: process.env.ADMIN_PASS ?? 'pass' },
} as const;

// tests/helpers.ts（已存在）
import { Page, Browser, BrowserContext } from '@playwright/test';
import { BASE_URL, ACCOUNTS } from './constants';
export class LoginPage {
  // （已实现）loginAs(role) 登录并跳转控制台首页
}
export async function createDualSession(browser: Browser, roleA: string, roleB: string) {
  // （已实现）返回 { pageA, pageB, contextA, contextB }
}
```

### 材料 3：页面结构说明（业务熟悉踩点结论）

- 「控制台 → 项目」页路由：`/console/projects`
- 新建项目：右上角按钮，文案「新建项目」；弹窗中名称输入框 placeholder 为「请输入项目名称」；确认按钮文案「确定」
- 项目卡片：卡片内名称为文本节点；卡片右下角「更多」按钮展开菜单，含「删除」项；确认弹窗按钮文案「删除」
- 搜索框：页面顶部，placeholder「搜索项目」，回车触发搜索
- 列表加载完成标志：网络请求 `GET /api/projects` 返回且页面出现 `.project-card` 元素
