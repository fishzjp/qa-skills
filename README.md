[简体中文](./README.md) | [English](./README.en.md)

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/hero-dark.png">
    <img src="./assets/hero.png" alt="QA Skills —— 知识 × 工具 × 决策的测试工程 Skill 框架：十轴类型决策矩阵与完整测试流水线" width="800">
  </picture>
</p>

<h1 align="center">qa-skills</h1>

<p align="center"><strong>让 AI 像资深测试工程师一样工作。</strong></p>

<p align="center">知识 × 工具 × 决策 —— 面向 Claude Code 等 Agent 的测试工程 Skill 框架。<br>每一个数字，都来自实测。</p>

<p align="center">
  <a href="https://github.com/fishzjp/qa-skills/actions/workflows/ci.yml"><img src="https://github.com/fishzjp/qa-skills/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="./skills/"><img src="https://img.shields.io/badge/skills-10-blue" alt="Skills"></a>
  <a href="https://github.com/fishzjp/qa-skills/releases"><img src="https://img.shields.io/badge/release-%E5%A2%9E%E7%9B%8A%E7%9F%A9%E9%98%B5%E5%BF%AB%E7%85%A7-orange" alt="Release gain matrix"></a>
  <a href="https://github.com/fishzjp/qa-skills/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
</p>

---

## 快速开始

### 安装

**方式一：安装脚本**（自动检测宿主 skills 目录）

```bash
git clone https://github.com/fishzjp/qa-skills.git
cd qa-skills

./install.sh            # 交互式选择宿主目录（自动检测 ~/.agents/skills 等）
./install.sh --auto     # 或全自动安装
```

**方式二：[skills.sh](https://skills.sh) 跨 Agent 安装**（Claude Code / Cursor / Codex / OpenCode 等 50+ 宿主）

```bash
npx skills add fishzjp/qa-skills            # 交互式勾选，全装用 --skill '*'
```

**方式三：dsh 插件**（npm 包 [`dsh-qa-skills`](https://www.npmjs.com/package/dsh-qa-skills)）

```bash
dsh plugin --profile web add dsh-qa-skills
```

> `core/` 是共享知识库依赖单元（不可执行任务）：安装任一 skill 时必须一并安装，否则引用路径断裂。

<details>
<summary><strong>手动安装、升级与卸载</strong></summary>

- 手动安装：`cp -r skills/* <skills 目录>/`——**`core/` 必须一起复制**，各 skill 以相对路径引用它。
- 验证：`ls <skills 目录>` 应见 10 个 skill 目录 + `core/` + `qa-skills.VERSION`。
- 升级：`./install.sh --target <目录> --link` 软链安装，`git pull` 后即更新。
- 卸载：`./uninstall.sh`。
</details>

<details>
<summary><strong>宿主兼容性</strong></summary>

Skill 是纯 Markdown（frontmatter + 相对路径引用），不依赖宿主特性：

| 宿主 | 安装目录 | 状态 |
|------|---------|------|
| Claude Code | `~/.claude/skills/` 或 `<项目>/.claude/skills/` | ✅ 主要适配对象，评测基于此 |
| 跨宿主共享目录 | `~/.agents/skills/` | ✅ 多 Agent 共读一份，`install.sh` 默认 |
| DeepSeek Harness (dsh) | `~/.agents/skills/`、`~/.dsh/skills/` 或 `<项目>/.agents/skills/` | ✅ 端到端实测通过 |
| Codex CLI | `~/.codex/skills/` | 🔶 未系统评测 |
| 其他支持 Skills 的 Agent | 各自的 skills 目录 | 🔶 同上 |

`qa` 流水线的阶段间上下文隔离依赖宿主子代理能力；不支持时自动退化为顺序会话 + 文件衔接，正确性不受影响。
</details>

### 开始使用

装好后对 Agent 说一句：

> **帮我测试这个需求：{需求描述 + 仓库地址}**

完整流水线从需求理解、风险与类型决策跑到测试报告；只需单个阶段（写用例 / 审查 / 转自动化 / 回归范围）时，直接描述需求即可。

## 能力总览

| 你说 | 框架做 | 产出 |
|------|--------|------|
| "帮我测试这个需求" | `qa` 编排 9 阶段流水线，检查点等你裁决 | 全套测试资产 + 测试报告 |
| "根据这份 PRD 写用例" | 代码优先：索取仓库、读实现、审出潜在 Bug 再写 | 双轨用例：markmap（人）+ schema.yaml（机器） |
| "这个功能应该怎么测" | Risk Map（评级挂证据）→ 功能域 + 类型域两域决策（十轴全轴必答） | `测试策略.md`（含 type_scope 与专项移交包） |
| "审一下这份存量用例" | 独立审查：可测点基准分母 + 覆盖 + 可执行性双线 | 直接修订用例文件 + 审查记录 |
| "把用例转成自动化" | Page Object 规范、监听先于操作、自建数据自清理 | 可运行的 Playwright / pytest 代码 |
| "这个 Bug 帮我定位一下" | 复现 → 读代码到行 → 影响五面分析 → 回归建议 | Bug 条目（根因 / 证据 / 回归） |

`exploratory-testing`（charter 驱动探索）、`api-testing`（接口级）、`bug-analysis`、`regression-testing`（diff → 回归范围）各自独立可用。

<details>
<summary><strong>测试用例脑图怎么渲染</strong></summary>

`测试用例_markmap.md` 是标准 Markdown（markmap 语法）：[VS Code Markmap 扩展](https://marketplace.visualstudio.com/items?itemName=gera2ld.markmap-vscode)、`npx markmap-cli 测试用例_markmap.md` 生成交互式 HTML、或粘贴到 [markmap.js.org/repl](https://markmap.js.org/repl)。
</details>

## 核心设计

### 可执行的测试用例

AI 写出的用例常常看似专业、实则无法执行——判定模糊、占位符、无判定时限、虚构入口。本框架的核心产出标准只有一条：**没读过需求、没人讲解的人，拿着文件能直接开工。** 同一个需求，产出长这样：

```markdown
> 前置:运营账号已登录,进入「营销中台 → 券工场 → 活动列表」

- **TC-02-05 到期自动结束** [P1]
  - 操作步骤: 1. 选一张结束时间为 2 分钟后的已发布券「满100减20-测试」 2. 等待到期
  - 预期结果: 到期后 1 小时内状态自动变为「已结束」,超过 1 小时未变判失败
```

背后是 `skills/core/executability.md` 的 8 条硬标准；评测中它是一票否决项——不可执行的用例，覆盖再全也计零分。

### 三层架构：指令更少，遵循更强

把方法论、模板、规则全部塞进一个 SKILL.md，Agent 有效遵循的规则反而更少（[Red Hat ACE 实践总结](https://next.redhat.com/2026/07/28/building-skills-for-ai-agents-pitfalls-and-best-practices/)：指令超过 500 行后性能退化）。解法是三层架构：

```text
L1  SKILL.md 头部      触发边界：什么时候用、什么时候不用、交给谁
L2  SKILL.md 正文      工作流：每次触发都要走的主干（≤500 行红线）
L3  references/ + core/  方法 / 规则 / 模板：按需加载，工作流步骤里显式引用
```

SKILL.md 只装流程编排，细则全部下沉、按需加载——Agent 每一步只面对当前需要的指令。

### 类型决策矩阵：决定测什么，更决定不测什么

未装 skill 的模型制定测试策略时，跨两个模型段位的 30 次评测采样中**零显式类型决策**——输出里"提到"性能与安全，却从不决定哪些纳入、测多深、哪些明确不测。提到不等于决策。

解法是**类型决策矩阵**：性能 / 业务安全 / 可靠 / 并发等十个测试类型**全轴必答**——纳入必须挂信号、排除必须留痕、full 档有预算上限，每条决策落盘为机器可校验的 type_scope。实测：最弱模型类型查全率 0 → **0.88**（详见[实测效果](#实测效果)）。

## 工作原理

**文件即流水线状态**——每阶段产出落盘为文件，下一阶段只消费文件而非会话记忆；长流水线不依赖上下文，中断后新会话读文件续跑：

```text
PRD / 代码
   │  requirement-analysis
   ▼
需求模型.md ·················· ⏸ 澄清检查点
   │  test-strategy（风险 → 两域决策）
   ▼
测试策略.md（Risk Map + 类型域十轴决策 type_scope）· ⏸ 预算裁决
   │  test-case-writing
   ▼
测试用例 markmap（给人）+ schema.yaml（给机器）
   │  test-case-review
   ▼
⏸ 执行策略裁决（手动 / Playwright / API）
   │  automated-e2e-testing / api-testing
   ▼
执行产物 + Bug 证据 → bug-analysis → regression-testing
   ▼
回归清单.md → 测试报告.md
```

- **证据与风险模型**：每条结论标注证据等级（E0–E4）；风险评级必须挂证据，无证据的评级无效，推导链证据 → 风险 → 策略 → 用例全程可追溯。
- **类型决策矩阵**：十轴全轴必答，纳入与排除都留痕；G 级信号由脚本扫描成预填表，弱模型从预填表修订、而非从空白生成。
- **人在环路的检查点**：澄清、执行策略、Bug 定性、预算上限四类事项由你裁决，Agent 只提案、不代答；裁决落盘后，后续阶段不得推翻。

## 实测效果

12 个评测任务，同一模型、同一评测链路，唯一差异是是否注入本框架；数字以异构裁判复评轮为准，如实披露（含反向结果）。完整方法学与原始数据在本地评测链路维护、不随仓库分发；每版 Release 附跨模型增益矩阵快照（[Releases](https://github.com/fishzjp/qa-skills/releases)），Skill On / Off 产出对照见 [examples/](./examples/)：

| 指标 | 无 Skill | 有 Skill |
|------|:---:|:---:|
| 用例规格符合度 | 0.26 | **0.98** |
| E2E 代码真实执行（单任务 × 3 采样） | 0/3 可运行 | 1 全过 + 2×(2/3) |
| 植入 Bug 检出率 | — | **75%** |
| 产出质量（LLM judge） | 0.70 | **0.76** |
| API 代码真实执行通过率 † | 100% | 99.2% |
| Token 成本 | 1× | 3.3× |

> **决策层首轮（2026-08-23，类别性判读，未进正式增益表）**：5 个类型决策任务（参考答案双人独立标注复核），最弱模型 deepseek-v4-flash（n=3）：无 skill 组**零显式类型决策**——宽容口径亦为 0，盲区在决策纪律而非类型知识；有 skill 组类型查全率 **0 → 0.88**，需求未提、只存在于代码的可靠性/契约轴 0 → 8/9。两个数字待任务扩容与跨模型梯度轮后进正式增益表。

<details>
<summary><strong>逐项口径</strong></summary>

- **用例规格符合度**：格式 × 内容红线复合计分，无 judge；无格式采样按 0 计（同口径），差距主要由格式采纳驱动；跨两个生成模型复现（0.20→0.99）；早期 0.77 为修复前口径，勘误见 [CHANGELOG](./CHANGELOG.md)。
- **E2E 真实执行**：真实浏览器 + 被测应用，无 judge；无 skill 一侧含未产出代码与执行失败两种情形。
- **植入 Bug 检出率**：异构裁判口径，同源裁判下为 100%。
- **产出质量**：异构裁判，Δ+6.1pp（95%CI 含零，同源口径下显著）。
- **API 真实执行通过率 †**：修复后干净复验口径（主模型 glm-5.2，n=3）：无/有 skill 100% / 99.2%，噪声带内持平；弱模型段位同向（0.30 / 0.67，有 skill 更优）。早期反向结果经逐失败归类定案为评测侧缺陷而非 skill 缺陷，勘误见 [CHANGELOG](./CHANGELOG.md)。
- **Token 成本**：如实披露——更好但更贵。总 token 比（任务级均值，含 skill 全量注入）：主模型轮 3.3×，弱模型轮最高 9.5×；单文件消融证明增益不可由"只拿走核心标准文档"替代。
</details>

<details>
<summary><strong>预注册门判定与覆盖增益</strong></summary>

预注册门判定：同源裁判 4/7、异构裁判 5/8（两者构成不同，含 G1b 方向翻转）。覆盖增益（异构裁判）：用例编写 **+8.7pp**（CI[0.5, 15.4]）、全任务 **+13.2pp**（CI[2.8, 26.3]）、缺陷检出 **+9.7pp**（CI[3.3, 16.4]），均显著；同源口径 +3.8pp（宽容偏差已量化勘误，见 [CHANGELOG](./CHANGELOG.md)）。早期 +29pp 单采样增益经多样本复验证实为噪声。

**口径边界**：评测通道将 skill 指令全量预注入（真实宿主为按需加载），"有 skill" 一侧数字是上界——in-situ 探针（n=1）未观测到衰减；成对评审三种裁判下平局率均超限，胜率指标作废（机制问题）。
</details>

## 更多文档

- [examples/](./examples/) —— 同一 PRD 的 Skill On / Off 产出对照
- [CHANGELOG.md](./CHANGELOG.md) —— 版本历史（各版本附增益矩阵快照）
- [RELEASING.md](./RELEASING.md) —— 发版规则与检查单（四面分发同步 / 版本策略 / 测试门）
- 设计文档与规划（DESIGN / 决策层设计稿 / v2 规划）—— 维护者本地资料，不随仓库分发

<details>
<summary><strong>仓库结构</strong></summary>

```text
skills/                  产品本体（10 个 skill + core 共享知识库）
  qa/                    编排入口（薄，无领域知识）
  core/                  共享知识库（仅作安装依赖单元，不参与任务触发）：evidence / risk-model /
                         executability / testing-principles / report-template / case-format /
                         coverage / schema-extraction / clarify-pattern / test-type-matrix（类型决策矩阵）/
                         triage（失败分流）/ pipeline-integration（非交互与 CI 集成）
                         + methods/（4 篇方法细则）+ scripts/（schema 校验器 + 类型信号扫描器）
  requirement-analysis/  test-strategy/  test-case-writing/
  test-case-review/      automated-e2e-testing/  api-testing/
  exploratory-testing/   bug-analysis/  regression-testing/
.dsh/                    dsh 插件三件套（清单见 package.json 的 dsh.bundle）
assets/                  视觉资产（hero 图、落地页配图 landing/、分享图 og.jpg、社交预览图）
examples/                Skill On / Off 产出对照
```
</details>

## 贡献与社区

- **贡献指南与架构红线**：[CONTRIBUTING.md](./CONTRIBUTING.md)；本地自检 `python3 scripts/validate_skills.py`（与 CI 同一校验）
- 🐛 缺陷 / 💡 功能建议：先到 [Discussions](https://github.com/fishzjp/qa-skills/discussions)（问答与经验分享），确认后提 [Issue](https://github.com/fishzjp/qa-skills/issues)
- 🛡️ 安全漏洞：请勿公开讨论，按[安全策略](./.github/SECURITY.md)私密报告
- 📜 行为准则：[CODE_OF_CONDUCT.md](./.github/CODE_OF_CONDUCT.md) · 📋 版本历史：[CHANGELOG.md](./CHANGELOG.md)

## 许可证

[MIT](./LICENSE)
