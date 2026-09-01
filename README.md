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

> `core/` 是共享知识库（不是可独立运行的 skill）：装任何一个 skill 都必须连它一起装，否则相对路径引用会断。

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

`qa` 流水线的每个阶段在独立子会话中运行、互不污染上下文；宿主不支持子代理时自动退化为顺序会话 + 文件衔接，正确性不受影响。
</details>

### 开始使用

装好后对 Agent 说一句：

> **帮我测试这个需求：{需求描述 + 仓库地址}**

一句话，流水线就从需求理解一路跑到测试报告。只需要其中某一步的产出（写用例 / 审查 / 转自动化 / 回归范围）时，直接说需求就行。

## 能力总览

| 你说 | 框架做 | 产出 |
|------|--------|------|
| "帮我测试这个需求" | `qa` 编排 9 阶段流水线，检查点等你裁决 | 全套测试资产 + 测试报告 |
| "根据这份 PRD 写用例" | 代码优先：索取仓库、读实现、审出潜在 Bug 再写 | 双轨用例：markmap（人）+ schema.yaml（机器） |
| "这个功能应该怎么测" | Risk Map（每个评级必须给出证据）→ 功能域 + 类型域两域决策（十个测试类型逐一必答） | `测试策略.md`（含 type_scope 与专项移交包） |
| "审一下这份存量用例" | 独立审查：先立可测点清单作分母，再查覆盖与可执行性 | 直接修订用例文件 + 审查记录 |
| "把用例转成自动化" | Page Object 规范、监听先于操作、自建数据自清理 | 可运行的 Playwright / pytest / k6 代码 |
| "这个 Bug 帮我定位一下" | 复现 → 读代码到行 → 影响五面分析 → 回归建议 | Bug 条目（根因 / 证据 / 回归） |

`exploratory-testing`（探索式测试，charter 驱动）、`api-testing`（接口级）、`bug-analysis`、`regression-testing`（diff → 回归范围）各自独立可用。

<details>
<summary><strong>测试用例脑图怎么渲染</strong></summary>

`测试用例_markmap.md` 是标准 Markdown（markmap 语法）：[VS Code Markmap 扩展](https://marketplace.visualstudio.com/items?itemName=gera2ld.markmap-vscode)、`npx markmap-cli 测试用例_markmap.md` 生成交互式 HTML、或粘贴到 [markmap.js.org/repl](https://markmap.js.org/repl)。
</details>

<details>
<summary><strong>范围边界（当前不做）</strong></summary>

本框架聚焦系统级黑盒测试的决策与执行。以下能力显式不做，各有明确理由：

- **单元 / 集成测试**——开发侧职责；测试策略的风险评级与"已覆盖"结论以该层已有保障为假设前提（未验证时在报告中标注）
- **移动端真机自动化**——兼容性矩阵暂限桌面浏览器，云真机是候选扩容方向
- **前端组件测试 / 前端性能自动化**——候选扩容方向，决策层验证后立项
- **渗透测试 / SAST 与依赖扫描**——渗透依赖专业人工与授权环境（右移安全专项）；SAST 是开发侧 CI 工具，只作业务安全轴的信号来源
- **混沌工程工具链**——故障注入提供设计方法与执行前提约定，专业工具链不随本框架分发

</details>

## 核心设计

### 可执行的测试用例

AI 写出的用例常常看似专业、实则无法执行——判定模糊、占位符、无判定时限、虚构入口。本框架的核心产出标准只有一条：**没读过需求、没人讲解的人，拿着文件能直接开工。** 同一个需求，产出长这样：

```markdown
> 前置:运营账号已登录,进入「营销中台 → 券工场 → 活动列表」

- **TC-03-05 到达结束时间后优惠券自动变为已结束** [P1]
  - 操作步骤: 1. 选一张结束时间为 10 分钟后的已发布券「满100减20-测试」 2. 等待到期
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

SKILL.md 只留流程编排，方法细节全部移到下层、用到才加载——Agent 每一步只看当前需要的那部分指令。

### 类型决策矩阵：决定测什么，更决定不测什么

未装 skill 的模型制定测试策略时，跨两个模型段位的 30 次评测采样里，**没有一次给出显式的类型决策**——输出里"提到"了性能与安全，却从不决定哪些纳入、测多深、哪些明确不测。提到不等于决策。

解法是**类型决策矩阵**：性能 / 业务安全 / 可靠 / 并发等十个测试类型**逐一必答**——纳入必须给出信号依据、排除必须留下记录、full 档有预算上限，每条决策落盘为机器可校验的 type_scope。实测：最弱模型类型查全率 0 → **0.88**（详见[实测效果](#实测效果)）。

## 工作原理

**文件即流水线状态**——每个阶段把产出存成文件，下一个阶段只读文件、不依赖会话记忆；流水线再长也不怕超上下文，中断后新会话读文件接着跑：

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

- **证据与风险模型**：每条结论标注证据等级（E0–E4）；风险评级必须给出证据，给不出证据的评级无效——证据 → 风险 → 策略 → 用例，全程可追溯。
- **类型决策矩阵**：十个测试类型逐一决策，纳入与排除都留痕；能机械扫描的信号由脚本生成预填表，弱模型照着预填表修订、而不是从空白硬编。
- **关键决策归你拍板**：澄清提问、执行策略、Bug 定性、预算上限，这四类事由你裁决，Agent 只提案、不代答；你裁决落盘后，后续阶段不得推翻。

## 实测效果

12 个评测任务：同一模型、同一评测链路，唯一差别是有没有装本框架。数字以异构裁判复评轮为准（裁判模型与被评测的模型不同源），如实披露、包括不利结果。完整方法学与原始数据在本地评测链路维护、不随仓库分发；跨模型增益矩阵快照按里程碑随 Release 附带（[Releases](https://github.com/fishzjp/qa-skills/releases)），Skill On / Off 产出对照见 [examples/](./examples/)：

| 指标 | 无 Skill | 有 Skill |
|------|:---:|:---:|
| 用例规格符合度 | 0.26 | **0.98** |
| E2E 代码真实执行（单任务 × 3 采样） | 0/3 可运行 | 1 全过 + 2×(2/3) |
| 植入 Bug 检出率 | — | **75%** |
| 产出质量（裁判模型评分） | 0.70 | **0.76** |
| API 代码真实执行通过率 † | 100% | 99.2% |
| Token 成本 | 1× | 3.3× |

> **类型决策矩阵首轮实测（2026-08-23，尚未进正式增益表）**：5 个类型决策任务（参考答案经双人独立标注复核），最弱模型 deepseek-v4-flash（n=3）：无 skill 组没有给出任何显式的类型决策——放宽判定标准也是 0，短板在决策纪律而非类型知识；有 skill 组类型查全率 **0 → 0.88**，需求未提、只写在代码里的可靠性/契约轴 0 → 8/9。任务池扩容、跨更多模型复现后进正式增益表。

<details>
<summary><strong>逐项口径</strong></summary>

- **用例规格符合度**：按格式与内容红线计分，纯规则判定、不经裁判模型；无格式产出的采样按 0 计（同一口径），差距主要来自格式采纳；跨两个生成模型复现（0.20→0.99）；早期 0.77 是修复前的口径，勘误见 [CHANGELOG](./CHANGELOG.md)。
- **E2E 真实执行**：真实浏览器里跑被测应用，不经裁判模型；无 skill 一侧包含没写出代码和跑不起来两种情形。
- **植入 Bug 检出率**：异构裁判口径，同源裁判下为 100%。
- **产出质量**：异构裁判评分，Δ+6.1pp（95% 置信区间跨零，主轮差异不显著；同源口径下显著）。
- **API 真实执行通过率 †**：修复评测缺陷后的干净复验（主模型 glm-5.2，n=3）：无/有 skill 100% / 99.2%，差距在噪声范围内、基本持平；弱模型上结论一致（0.30 / 0.67，有 skill 更优）。更早的反向结果经逐条失败归因，定案为评测侧缺陷而非 skill 缺陷，勘误见 [CHANGELOG](./CHANGELOG.md)。
- **Token 成本**：如实披露——效果更好，但更贵。总 token 消耗比（任务级均值，含 skill 全量注入）：主模型轮 3.3×，弱模型轮最高 9.5×；对照实验显示，只注入核心标准文档时增益不复现——收益来自整套框架，不是某一份文档。
</details>

<details>
<summary><strong>预注册门判定与覆盖增益</strong></summary>

评测前预注册了通过门槛（防事后挑指标）：同源裁判口径通过 4/7，异构裁判口径通过 5/8（两侧门槛清单不同，其中一项在两个口径下方向相反）。覆盖增益（异构裁判）：用例编写 **+8.7pp**（95% CI [0.5, 15.4]）、全任务 **+13.2pp**（95% CI [2.8, 26.3]）、缺陷检出 **+9.7pp**（95% CI [3.3, 16.4]），均显著；同源口径 +3.8pp（裁判宽容偏差已量化并勘误，见 [CHANGELOG](./CHANGELOG.md)）。早期 +29pp 的单采样增益经多样本复验证实为噪声。

**口径边界**：评测时把 skill 全部指令一次性预注入（真实宿主是按需加载），"有 skill" 一侧的数字因此是上界；真实宿主抽查（n=1）未观察到衰减。成对评审（两份产出对比打分）在三种裁判下平局都过多，胜率指标作废（机制问题）。
</details>

## 更多文档

- [examples/](./examples/) —— 同一 PRD 的 Skill On / Off 产出对照
- [CHANGELOG.md](./CHANGELOG.md) —— 版本历史（里程碑版本附增益矩阵快照）
- [RELEASING.md](./RELEASING.md) —— 发版规则与检查单（四面分发同步 / 版本策略 / 测试门）
- 设计文档与规划（DESIGN / 决策层设计稿 / v2 规划）—— 维护者本地资料，不随仓库分发

<details>
<summary><strong>仓库结构</strong></summary>

```text
skills/                  产品本体（10 个 skill + core 共享知识库）
  qa/                    编排入口（薄，无领域知识）
  core/                  共享知识库（作为依赖随 skill 一并安装，不独立触发）：evidence / risk-model /
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
scripts/                 CI 架构红线校验器（validate_skills.py）
tests/                   随产品分发脚本的回归测试（validate_schema / scan_signals / validate_skills）
index.html               官网落地页（GitHub Pages 构建源）
```
</details>

## 贡献与社区

- **贡献指南与架构红线**：[CONTRIBUTING.md](./CONTRIBUTING.md)；本地自检 `python3 scripts/validate_skills.py`（与 CI 同一校验）
- 🐛 缺陷 / 💡 功能建议：先到 [Discussions](https://github.com/fishzjp/qa-skills/discussions)（问答与经验分享），确认后提 [Issue](https://github.com/fishzjp/qa-skills/issues)
- 🛡️ 安全漏洞：请勿公开讨论，按[安全策略](./.github/SECURITY.md)私密报告
- 📜 行为准则：[CODE_OF_CONDUCT.md](./.github/CODE_OF_CONDUCT.md) · 📋 版本历史：[CHANGELOG.md](./CHANGELOG.md)

## 许可证

[MIT](./LICENSE)
