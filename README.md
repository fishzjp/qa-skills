# QA Skills

面向软件测试全流程的两个 [Claude Code Agent Skill](https://docs.claude.com/en/docs/claude-code/skills)，覆盖「编写测试用例」与「E2E 自动化测试」，形成从需求到自动化执行的闭环。

- **test-case-writing** —— 根据需求文档 / 设计方案 / API 文档 / Bug 报告，编写系统化的手动测试用例（markmap 格式），并支持覆盖度审查与需求变更后的增量更新。
- **automated-e2e-testing** —— 将手动测试用例转为 Playwright E2E 测试、进行探索性自动化测试、记录 Bug 报告。

两个 skill 互相引用：`test-case-writing` 产出用例，`automated-e2e-testing` 把用例变成可自动执行的代码。

## 适用场景

| 你想做的事 | 用哪个 skill |
|------------|--------------|
| 给定 PRD / 设计文档，编写测试用例 | test-case-writing |
| 审查已有用例的覆盖盲区 | test-case-writing |
| 需求变更后增量更新用例 | test-case-writing |
| 把用例 Markdown 转成 Playwright 自动化 | automated-e2e-testing |
| 对 Web 应用做探索性自动化测试 | automated-e2e-testing |
| 自动化测试中记录 Bug 报告 | automated-e2e-testing |

## 安装

把对应目录复制到 Claude Code 的 skills 目录即可：

- **仅当前项目可用**：复制到 `<项目>/.claude/skills/`
- **所有项目可用**：复制到 `~/.claude/skills/`

```bash
# 示例：安装到当前项目
cp -r test-case-writing      <项目>/.claude/skills/
cp -r automated-e2e-testing  <项目>/.claude/skills/
```

安装后在 Claude Code 中描述你的任务（如「根据这份 PRD 写测试用例」），skill 会自动触发；也可用 `/test-case-writing`、`/automated-e2e-testing` 显式调用。

## 使用 automated-e2e-testing 的前置条件

该 skill 是方法论 + 代码模板，**不绑定具体项目**。落地时你需要：

1. **一个 Playwright 项目**：`npm init playwright@latest`，按 skill 中「代码架构」组织 `tests/`、`pages/`、`helpers.ts`、`constants.ts`。
2. **环境与账号配置**：在 `tests/constants.ts` 或 `.env` 中配置 `BASE_URL` 和角色账号（skill 不硬编码任何环境地址或账号）。
3. **通用 Helper**：按 skill 中「通用 Helper 参考实现」一节落地 `tests/helpers.ts`（登录、多用户会话、Bug 证据收集等），再按你的系统调整选择器。

`test-case-writing` 无前置条件，装好即用。

## 目录结构

```
qa-skills/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── test-case-writing/
│   ├── SKILL.md
│   ├── references/coverage_checklist.md   # 覆盖度检查表（18 个维度）
│   └── templates/markmap_template.md      # 用例文件拼装模板
└── automated-e2e-testing/
    └── SKILL.md                            # 含通用 Helper 参考实现
```

## 设计理念

- **先澄清再动手**：需求模糊或定位失败时，向用户提问而非猜测。
- **一条用例只测一个点**：手动用例与自动化 test 一一对应，预期结果唯一。
- **状态机驱动**：按状态流转组织用例，发现更多边界。
- **先熟悉业务再写测试**：对功能不熟时，先用探索脚本理解真实行为。
- **每个 test 自建数据、自清理**，正式测试一律用 Page Object。

## 许可证

MIT，详见 [LICENSE](./LICENSE)。
