[简体中文](./README.md) | [English](./README.en.md)

<p align="center">
  <img src="./assets/hero.png" alt="QA Skills — 面向 AI Coding Agent 的全生命周期测试工程 Skill 框架" width="800">
</p>

<p align="center">
  <em>让 AI 像资深测试工程师一样工作——一句"帮我测试这个需求"，跑完从需求理解到测试报告的完整流水线。</em>
</p>

<p align="center">
  <a href="https://github.com/fishzjp/qa-skills/actions/workflows/ci.yml"><img src="https://github.com/fishzjp/qa-skills/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/fishzjp/qa-skills/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
  <a href="./skills/"><img src="https://img.shields.io/badge/skills-10-blue" alt="Skills"></a>
  <a href="./eval/"><img src="https://img.shields.io/badge/benchmark-golden%20set%20%2B%20harness-orange" alt="Benchmark"></a>
</p>

qa-skills 是一套面向 [Claude Code 等 Agent](https://docs.claude.com/en/docs/claude-code/skills) 的**测试工程 Skill 框架**：不是几段测试 Prompt 的集合，而是"方法论 + Skills + Benchmark"三层体系，对外呈现的每一个数字都经过实测。

---

## 快速开始

```bash
git clone https://github.com/fishzjp/qa-skills.git
cd qa-skills

./install.sh            # 交互式选择宿主目录（自动检测 ~/.agents/skills 等）
./install.sh --auto     # 自动安装到第一个检测到的目录
./install.sh --target <项目>/.claude/skills --link   # 项目级 + 软链（git pull 即升级）

# 然后对 Agent 说一句：
# "帮我测试这个需求：{需求描述 + 仓库地址}"
```

- 卸载：`./uninstall.sh`
- 手动安装：`cp -r skills/* <你的 skills 目录>/`（**core/ 必须一起复制**，各 skill 通过相对路径引用它）
- 单阶段任务（写用例 / 审查 / 转自动化 / 回归范围）直接描述即可触发对应 skill，无需完整流水线

### 宿主兼容性

Skill 是纯 Markdown 指令文件（frontmatter + 相对路径引用），不依赖特定宿主特性：

| 宿主 | 安装目录 | 状态 |
|------|---------|------|
| Claude Code | `~/.claude/skills/` 或 `<项目>/.claude/skills/` | ✅ 主要适配对象，评测基于此 |
| 跨宿主共享目录 | `~/.agents/skills/` | ✅ 多 Agent 共读一份，`install.sh` 默认推荐 |
| Codex CLI | `~/.codex/skills/` | 🔶 按约定应可用，未系统评测 |
| 其他支持 Skills 的 Agent | 各自的 skills 目录 | 🔶 同上 |

> `qa` 流水线的"阶段间上下文隔离"依赖宿主的子会话 / 子代理能力；宿主不支持时自动退化为顺序会话 + 文件衔接，正确性不受影响（见 [DESIGN.md](./docs/DESIGN.md) 编排会话模型一节）。

## 能力总览

| 你说 | 框架做 | 产出 |
|------|--------|------|
| "帮我测试这个需求" | `qa` 编排 9 阶段流水线，澄清 / 执行策略 / Bug 定性检查点等你裁决 | 全套测试资产 + 测试报告 |
| "根据这份 PRD 写用例" | 代码优先：主动索取仓库、读实现、审出潜在 Bug 再写用例 | 双轨用例：markmap（人执行）+ schema.yaml（机器消费） |
| "这个功能应该怎么测" | Risk Map（Impact × Likelihood，评级强制挂证据）→ 范围 / 深度 / 理由 | `测试策略.md` |
| "审一下这份存量用例" | 独立审查：可测点基准分母 + 覆盖 + 可执行性双线 | 直接修订用例文件 + 审查记录 |
| "把用例转成自动化" | Page Object 规范、监听先于操作、自建数据自清理 | 可运行的 Playwright / pytest 代码 |
| "这个 Bug 帮我定位一下" | 复现 → 读代码到行 → 影响三面分析 → 回归建议 | Bug 条目（根因 / 证据 / 回归） |

另有 `exploratory-testing`（charter 驱动探索）、`api-testing`（接口级）、`bug-analysis`、`regression-testing`（diff → 回归范围）各自独立可用。

`测试用例_markmap.md` 是标准 Markdown（markmap 语法），渲染脑图的三种方式：VS Code 装 [Markmap 扩展](https://marketplace.visualstudio.com/items?itemName=gera2ld.markmap-vscode)、`npx markmap-cli 测试用例_markmap.md` 生成交互式 HTML、或粘贴到 [markmap.js.org/repl](https://markmap.js.org/repl)。

## 它解决什么问题

### 问题一：AI 写出的用例看似专业，实则无法执行

直接让 AI 编写测试用例，产出常常是这样：

```markdown
- 验证优惠券创建功能,输入合法数据,功能正常        ← 判定模糊:怎么算"正常"?
- 填写 {优惠券名称},点击 {提交按钮}               ← 占位符:执行的人填什么?
- 到达有效期后,状态自动变更为已结束               ← 多久没变算失败?
- 打开活动页,验证领取逻辑                        ← 入口在哪?新人根本找不到页面
```

同一个需求，本框架的产出是这样的：

```markdown
> 前置:运营账号已登录,进入「营销中台 → 券工场 → 活动列表」

- **TC-02-05 到期自动结束** [P1]
  - 操作步骤: 1. 选一张结束时间为 2 分钟后的已发布券「满100减20-测试」 2. 等待到期
  - 预期结果: 到期后 1 小时内状态自动变为「已结束」,超过 1 小时未变判失败
```

**本框架的核心产出标准只有一条：没读过需求、没人讲解的人，拿着文件能直接开工。** 这背后是 `skills/core/executability.md` 的 8 条硬标准；在评测中它是一票否决项——**不可执行的用例，覆盖再全也计零分**。完整 before/after 对照见 [examples/](./examples/)。

### 问题二：指令堆叠越多，Agent 遵循越差

把方法论、模板、规则全部塞进一个 SKILL.md，Agent 有效遵循的规则反而更少（[Red Hat ACE 的 Agent Skill 实践总结](https://next.redhat.com/2026/07/28/building-skills-for-ai-agents-pitfalls-and-best-practices/)：指令超过 500 行后性能开始退化）。本框架的解法是**三层架构**：

```text
L1  SKILL.md 头部      触发边界：什么时候用、什么时候不用、交给谁
L2  SKILL.md 正文      工作流：每次触发都要走的主干（≤500 行红线）
L3  references/ + core/  方法 / 规则 / 模板：按需加载，工作流步骤里显式引用
```

"写用例"由此被拆解为：SKILL.md 只负责流程编排，状态机方法、边界值公式、权限矩阵、格式硬约束全部下沉、按需加载——Agent 每一步只面对当前需要的指令。

## 工作原理

**文件即流水线状态**——每个阶段的产出落盘为文件，下一阶段只消费上一阶段的**文件**而非会话记忆。长流水线不依赖上下文，中断后新会话读取文件即可续跑：

```text
PRD / 代码
   │  requirement-analysis
   ▼
需求模型.md ·················· ⏸ 澄清检查点（模糊项等你裁决，不硬猜）
   │  test-strategy（风险 → 策略）
   ▼
测试策略.md（Risk Map）
   │  test-case-writing
   ▼
测试用例 markmap（给人）+ schema.yaml（单向抽取给机器）
   │  test-case-review
   ▼
⏸ 执行策略裁决（手动 / Playwright / API）
   │  automated-e2e-testing / api-testing
   ▼
执行产物 + Bug 证据
   │  bug-analysis → regression-testing
   ▼
回归清单.md → 测试报告.md
```

**证据与风险模型**——结论必须可追溯：

- **证据体系（E0–E4）**：每条结论标注证据等级（用户陈述 → 文档 → 代码 → 运行结果 → 交叉验证）与状态（事实 / 推断 / 风险 / 假设）。静态问题以代码为准（测准声明），文档偏离记入附录——AI 不再凭 PRD 想象系统行为。
- **风险模型（Impact × Likelihood）**：评级必须挂证据，没有证据的评级视为无效。推导链全程可追溯：证据 → 风险 → 策略 → 用例。

**人在环路的检查点**——端到端不等于零人工：澄清、执行策略、Bug 定性三类决策由你裁决，Agent 只提案、不代答；裁决落盘后，后续阶段不得推翻。

> 设计动机与关键决策（为什么是 10 个窄 skill 而不是 1 个全能 skill、为什么 markmap 是唯一维护源、为什么评测先于扩容）见 **[DESIGN.md](./docs/DESIGN.md)**。

## 实测效果（Skill On / Off）

黄金集 12 个任务，同模型、同 harness，唯一差异是是否注入本框架；数字以异构裁判复评轮为准（裁判与生成模型不同族）。方法学与完整报告见 [eval/harness/README.md](./eval/harness/README.md) 与 [📄 评测研究论文（PDF）](./eval/reports/2026-08-21-benchmark-study.pdf)：

| 指标 | 无 Skill | 有 Skill |
|------|:---:|:---:|
| 用例规格符合度 | 0.26 | **0.98** |
| E2E 代码真实执行（单任务 × 3 采样） | 0/3 可运行 | 1 全过 + 2×(2/3) |
| 植入 Bug 检出率 | — | **75%** |
| 产出质量（LLM judge） | 0.70 | **0.76** |
| API 代码真实执行通过率 † | **74%** | 52% |
| Token 成本 | 1× | 3.3× |

**逐项口径**：

- **用例规格符合度**（旧称"可执行性"）：编号 / 导读格式 × 内容红线复合，无 judge。差距主要由格式采纳驱动，内容红线层两臂基线均近满分（论文 §5.1）；无格式计 0 同口径（早期 0.77 系修复前口径，勘误见 eval 文档）；跨两个生成模型复现（0.20→0.99）。
- **E2E 真实执行**：真实浏览器 + 被测应用，无 judge；On 侧 2 个采样的同一失败测试稳定复现，Off 侧含未产出代码与执行失败两种情况（论文 §5.1）。
- **植入 Bug 检出率**：代码审查类任务；异构裁判口径，同源裁判下为 100%。
- **产出质量**：异构裁判；Δ+6.1pp（95%CI 含零，同源口径下显著）。
- **API 真实执行通过率 †**：如实披露的反向结果——skill 要求的状态码 + 业务码 + 字段三件套严断言更易暴露失败，弱断言易通过；完整 3 采样口径（早期 87% 系 2 采样均值），诊断见 [eval/EXPECTED.md](./eval/EXPECTED.md)。
- **Token 成本**：如实披露——更好但更贵；单文件消融实验证明增益不可由"只拿走核心标准文档"替代（论文 §5.3）。

预注册门判定：同源裁判 4/7、异构裁判 5/8（两者构成不同，含 G1b 方向翻转，完整对照见论文表 6）。覆盖类增益（异构裁判）：tcw 口径 **+8.7pp**（CI[0.5, 15.4]，显著）、全任务 **+13.2pp**（CI[2.8, 26.3]，显著）、缺陷检出 **+9.7pp**（CI[3.3, 16.4]，显著）——同源裁判口径为 +3.8pp，同源宽容偏差的量化与勘误详见 [eval/EXPECTED.md](./eval/EXPECTED.md)。早期单采样表观的 +29pp 经多样本复验证实为噪声。

> **口径边界**：评测的 Skill On 通道将 skill 全部指令文件预注入（真实宿主为按需加载），On 侧数字是"指令全部在场"的上界——in-situ 探针（n=1）未观测到衰减；成对评审在三种裁判下平局率均超限，胜率指标作废（机制问题，详见论文 §6）。

## 仓库结构

```text
skills/                  产品本体（10 个 skill + core 共享知识库）
  qa/                    编排入口（薄，无领域知识）
  core/                  共享知识库（无 SKILL.md，不参与触发）：evidence / risk-model /
                         executability / testing-principles / report-template / case-format /
                         coverage / schema-extraction / clarify-pattern + methods/（4 篇设计
                         方法细则）+ scripts/（Schema 校验器）——被多 skill 消费的内容统一在此
  requirement-analysis/  test-strategy/  test-case-writing/
  test-case-review/      automated-e2e-testing/  api-testing/
  exploratory-testing/   bug-analysis/  regression-testing/
eval/                    黄金集 + 评测 harness（多样本 / 统计推断 / 成对评审 / 真实执行）
docs/                    设计文档（DESIGN / v2 规划）
examples/                Skill On / Off 产出对照
tests/                   harness 单测
```

## 更多文档

- [DESIGN.md](./docs/DESIGN.md) —— 设计动机与关键决策
- [评测研究论文（PDF）](./eval/reports/2026-08-21-benchmark-study.pdf) —— 预注册基准评测与增益归因
- [eval/harness/README.md](./eval/harness/README.md) —— 评测方法学与 harness 使用说明
- [examples/](./examples/) —— 同一 PRD 的 Skill On / Off 产出对照
- [CHANGELOG.md](./CHANGELOG.md) —— 版本历史

## 贡献与社区

- **贡献指南与架构红线**：[CONTRIBUTING.md](./CONTRIBUTING.md)；本地一条命令自检 `python3 scripts/validate_skills.py`（与 CI 同一校验）
- 🐛 缺陷 / 💡 功能建议：先到 [Discussions](https://github.com/fishzjp/qa-skills/discussions)（使用问答与经验分享），确认是缺陷或明确诉求后再提 [Issue](https://github.com/fishzjp/qa-skills/issues)
- 🛡️ 安全漏洞：请勿公开讨论，按[安全策略](./.github/SECURITY.md)私密报告
- 📜 行为准则：[CODE_OF_CONDUCT.md](./.github/CODE_OF_CONDUCT.md) · 📋 版本历史：[CHANGELOG.md](./CHANGELOG.md)

## 许可证

[MIT](./LICENSE)
