[简体中文](./README.md) | [English](./README.en.md)

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/hero-dark.png">
    <img src="./assets/hero.png" alt="QA Skills —— 知识 × 工具 × 决策的测试工程 Skill 框架：十轴类型决策矩阵与完整测试流水线" width="800">
  </picture>
</p>

<h1 align="center">qa-skills</h1>

<p align="center"><strong>让 AI 像资深测试工程师一样工作。</strong></p>

<p align="center">面向 AI 编程 Agent 的测试工程 Skill 框架。<br>从需求澄清、风险决策，到可执行用例、自动化与测试报告。</p>

<p align="center">
  <a href="https://github.com/fishzjp/qa-skills/actions/workflows/ci.yml"><img src="https://github.com/fishzjp/qa-skills/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="./skills/"><img src="https://img.shields.io/badge/skills-12-blue" alt="Skills"></a>
  <a href="https://www.skills.sh/fishzjp/qa-skills"><img src="https://img.shields.io/badge/skills.sh-npx%20skills%20add-black" alt="Install via skills.sh"></a>
  <a href="https://github.com/fishzjp/qa-skills/releases"><img src="https://img.shields.io/badge/release-%E5%A2%9E%E7%9B%8A%E7%9F%A9%E9%98%B5%E5%BF%AB%E7%85%A7-orange" alt="Release gain matrix"></a>
  <a href="https://github.com/fishzjp/qa-skills/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
</p>

---

把测试方法、流程与产出标准装进你的 Agent：**12 个测试 skill + 一个共享知识库 `core/`**。可以跑完整流水线，也可以只写用例、审查、测接口或治理 flaky 测试。先看[五组真实产出对照](./examples/)，了解安装前后的区别。

[快速开始](#快速开始) · [选择 skill](#选择-skill) · [工作原理](#工作原理) · [兼容性与边界](#兼容性与边界) · [实测效果](#实测效果) · [文档导航](#文档导航)

## 快速开始

### 1. 安装全部 skill

在终端执行（需要 Node.js / npm 提供 `npx`）：

```bash
npx skills add fishzjp/qa-skills --skill '*'
```

按安装器提示选择宿主与安装范围。**保留 `--skill '*'`：`core/` 是必需的共享依赖，不是独立触发的 skill。** 单装某个 skill 而不带 `core/` 会使相对路径引用断开；补救时重新执行上面的全量安装命令。

<details>
<summary><strong>其他安装方式、升级与卸载</strong></summary>

**仓库安装脚本**（需要 Git 与 Bash）：

```bash
git clone https://github.com/fishzjp/qa-skills.git
cd qa-skills
./install.sh                 # 交互选择宿主目录
```

明确知道目标目录时可指定路径，目录不存在会自动创建：

```bash
./install.sh --target ~/.agents/skills
```

请先确认宿主会读取该目录。`./install.sh --auto` 只选择**已有**目录中的首个候选，依次为 `~/.agents/skills`、`~/.claude/skills`、`~/.codex/skills`、`~/.dsh/skills`、本仓库 `.claude/skills`；没有候选时会退出。

| 安装方式 | 升级 | 卸载 |
|------|------|------|
| skills.sh | 重跑全量安装命令 | 使用 skills.sh 的移除功能，按其提示选择条目 |
| `install.sh` 拷贝 | `git pull` 后重跑原安装命令 | `./uninstall.sh --target <原安装目录>` |
| `install.sh --target <目录> --link` 软链 | `git pull` 即更新内容；保留仓库原路径 | 同上；卸载前保留源仓库 |
| dsh 插件 | 由 dsh 插件管理器升级 | 由 dsh 插件管理器移除 |

软链安装的 `qa-skills.VERSION` 是安装时快照，`git pull` 不会重写它；要刷新标记可重跑安装脚本。

**dsh 插件**（需先安装 DeepSeek Harness，`web` 为示例 profile）：

```bash
dsh plugin --profile web add dsh-qa-skills
```

**手动复制**：把 `skills/` 下全部一级目录复制到宿主 skills 目录，保持各 skill 与 `core/` 同级；已有同名目录时先核对归属，避免覆盖其他内容。手动复制不生成版本标记。

</details>

### 2. 检查安装与装载

安装目标应包含下方[技能清单](#选择-skill)中的目录及 `core/`，例如 `qa/SKILL.md` 与 `core/executability.md`。**只有仓库 `install.sh` 会额外写入 `qa-skills.VERSION`**，其他方式不能用该文件判断成功与否。

按宿主要求刷新技能或新开会话，试一句“请使用 test-strategy，为这个需求制定测试策略”。从宿主的装载记录确认 `test-strategy/SKILL.md` 及所需 `core/` 文件已读取；没有装载记录时，可要求 Agent 列出实际读取的文件路径。仅目录存在不代表触发已成功。

### 3. 提供输入，开始测试

在被测项目中对 Agent 说：

```text
帮我测试这个需求：优惠券到期后自动结束。
需求：<替换为你的 PRD 路径>
代码：当前仓库；回归对比基线：main
先完成需求分析和测试策略，列出需要我确认的问题。
```

需求可以是文字、PRD、接口文档或已有用例。提供代码可补充实现证据；只有文档时会保留待确认项。进入执行阶段前，还需要可访问的测试环境、测试账号与运行工具：Web E2E 使用 Playwright，API 测试使用 Python / pytest 等，压测按需使用 k6。**安装 skill 不会同时安装这些工具或被测系统。**

完整流程会在需求澄清、执行策略、Bug 定性与预算裁决处等待你确认。只需要一步时，直接使用下面对应的请求。

## 选择 skill

| 你的需求 | Skill | 主要产出 |
|------|------|------|
| “帮我完整测试这个需求” | [qa](./skills/qa/SKILL.md) | 阶段编排、流水线状态与最终测试报告 |
| “梳理这份需求，有疑问先问我” | [requirement-analysis](./skills/requirement-analysis/SKILL.md) | 需求模型、范围与澄清记录 |
| “这个功能应该怎么测，哪些不测” | [test-strategy](./skills/test-strategy/SKILL.md) | 风险图、十类测试决策 `type_scope`、专项移交包 |
| “根据 PRD / 代码写测试用例” | [test-case-writing](./skills/test-case-writing/SKILL.md) | markmap 用例 + 机器可读 Schema |
| “审查这份已有用例” | [test-case-review](./skills/test-case-review/SKILL.md) | 覆盖与可执行性审查、修订文件和记录 |
| “把用例转成 Web 自动化并执行” | [automated-e2e-testing](./skills/automated-e2e-testing/SKILL.md) | Playwright 工程、执行结果与缺陷证据 |
| “根据 OpenAPI 测这些接口” | [api-testing](./skills/api-testing/SKILL.md) | API 测试脚本、执行结果；按需 k6 移交 |
| “文档不全，先探索这个系统” | [exploratory-testing](./skills/exploratory-testing/SKILL.md) | charter、探索笔记、风险与测试想法 |
| “定位这个已确认 Bug 的根因” | [bug-analysis](./skills/bug-analysis/SKILL.md) | 根因、影响、证据与回归建议 |
| “这次改动应该回归哪些用例” | [regression-testing](./skills/regression-testing/SKILL.md) | diff → 功能 → 用例的分级回归清单 |
| “用例时好时坏，重跑绿了能信吗” | [test-reliability](./skills/test-reliability/SKILL.md) | flaky 取证、隔离与重试策略、套件健康度 |
| “沉淀 / 读取这个项目的测试经验” | [qa-memory](./skills/qa-memory/SKILL.md) | 项目 `.qa/` 知识库、索引与校验结果 |

`core/` 是以上 skill 共用的方法、模板与脚本，完整索引见 [core/SKILL.md](./skills/core/SKILL.md)，无需单独调用。

## 工作原理

**阶段产出保存为文件，后续阶段按文件衔接。** 流水线中断后，在新会话中提供产物目录，让 `qa` 根据阶段完成判据续跑。

```text
PRD / 代码 ──（文档不足时先探索）
   ↓ requirement-analysis
需求模型.md                         ⏸ 澄清
   ↓ test-strategy
测试策略.md + type_scope            ⏸ 预算（触及裁决条件时）
   ↓ test-case-writing → test-case-review
测试用例_markmap.md + schema.yaml   ⏸ 执行策略
   ↓ Playwright / API / 手动执行
执行记录 + 缺陷证据                  ⏸ Bug 定性
   ↓ bug-analysis / regression-testing（按需）
Bug 条目 / 回归清单 → 测试报告
```

- **可执行的用例**：写清前置条件、操作入口、步骤、可判定结果与异步时限。标准见 [executability.md](./skills/core/executability.md)，完整产物见[用例示例](./examples/test-cases_with-skills.md)。
- **有证据的范围决策**：证据分级 E0–E4；风险评级附依据，十个测试类型逐一决定纳入、深度或排除，记录在可校验的 `type_scope` 中。
- **按需装载**：SKILL.md 保留触发边界与工作流，方法和模板放在 `core/`、`references/` 中。宿主支持子会话时按阶段隔离上下文；否则用顺序会话与文件衔接，具体遵循效果仍需在该宿主验证。
- **跨会话知识**：阶段状态留在产物文件中；可复用的项目经验由 `qa-memory` 管理，避免与流水线状态混写。

<details>
<summary><strong>渲染用例脑图与装载项目知识库</strong></summary>

**脑图**：`测试用例_markmap.md` 可用 [VS Code Markmap 扩展](https://marketplace.visualstudio.com/items?itemName=gera2ld.markmap-vscode) 预览，或运行 `npx markmap-cli 测试用例_markmap.md` 生成 HTML。

**项目知识库**：`qa-memory` 在被测项目维护 `.qa/INDEX.md` 与主题条目，skill 触发时主动读取。要让宿主在后续会话发现索引，可在其项目指令文件加入入口：

| 宿主支持的入口 | 配置 |
|------|------|
| `AGENTS.md` | 写明“测试任务开始时先读取 `.qa/INDEX.md`，再按需读取相关条目” |
| Claude Code 的 `CLAUDE.md` | 加入 `@.qa/INDEX.md`，或经现有 `@AGENTS.md` 导入链装载 |
| Aider | 在 `.aider.conf.yml` 配置 `read: .qa/INDEX.md`，或启动时加 `--read` |
| 其他宿主 | 按该宿主的项目指令机制配置，或由 skill 触发时读取 |

这些入口依赖宿主的文件发现与读取行为，不等于自动展开所有 Markdown 链接。入口自举会先展示改动、经你确认再写；知识条目按 [memory_validate.py](./skills/qa-memory/scripts/memory_validate.py) 的校验结果处理。

</details>

## 兼容性与边界

产品以 Markdown 指令、相对路径引用与按需运行的辅助脚本分发。宿主需要支持 skill 发现、文件读取；实际执行还需要终端或浏览器工具。

| 宿主 / 方式 | 目录或载体 | 已有验证的范围 |
|------|------|------|
| Claude Code | `~/.claude/skills/` 或项目 `.claude/skills/` | 主要适配对象；安装形态有实测记录 |
| 共享目录 | `~/.agents/skills/` | 安装脚本优先候选；是否读取由宿主决定 |
| DeepSeek Harness（dsh） | 插件，或 `~/.agents/skills/`、`~/.dsh/skills/` | 有端到端实测记录 |
| Codex | skills.sh 安装实测落在 `~/.agents/skills/`；仓库脚本也可指定 `~/.codex/skills/` | 安装与引用路径验证；尚未系统评测产出效果 |
| 其他支持 Agent Skills 的宿主 | 依其安装规则 | 结构可适配，触发、装载与产出质量需分别验证 |

安装实测的日期与具体命令见 [RELEASING 安装矩阵](./RELEASING.md#安装形态实测矩阵触达安装面引用路径的发版必登记)。**安装成功、触发正确、产出质量是三个不同的验证层次。**

**语言**：README 与官网提供中英文；12 个 skill 中 11 个的 description 为双语，`bug-analysis` 暂保留中文以避免已观测到的路由回退；skill 指令正文仍为中文。

**范围**：聚焦系统级黑盒测试的决策与执行。不提供单元 / 集成测试、移动真机自动化、前端组件测试、专业渗透 / SAST / 依赖扫描或混沌工程工具链；这些领域可作为风险信号或专项移交内容，不能把移交视为已经执行。

## 实测效果

以下是**历史实验结果**，并非对当前工作区重新评测，也不代表每个模型、每个宿主都能获得同样提升。数字来自早期 12 任务的注入式 On/Off 对照及后续执行专项复验，具体见逐项口径。同一对照内模型与评测链路相同；裁判类指标采用与生成模型不同源的裁判。各轮样本量与任务范围不同，不能合并计算。

版本对应的证据请看[里程碑 Release 增益矩阵快照](https://github.com/fishzjp/qa-skills/releases)，后续变更与勘误见 [CHANGELOG](./CHANGELOG.md)；[examples/](./examples/) 展示单任务产出。评测 harness、任务池与原始数据在维护者本地维护，不随仓库分发。

<details>
<summary><strong>展开历史指标、成本与适用边界</strong></summary>

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
- **API 真实执行通过率 †**：修复评测缺陷后的干净复验（主模型 glm-5.2，n=3）：无/有 skill 100% / 99.2%，差距在噪声范围内、基本持平；另一轮弱模型结果为无 / 有 skill 0.30 / 0.67，有 skill 更优；两轮应分别解读。更早的反向结果经逐条失败归因，定案为评测侧缺陷而非 skill 缺陷，勘误见 [CHANGELOG](./CHANGELOG.md)。
- **Token 成本**：指令装载与工作流增加了成本。总 token 消耗比（任务级均值，含 skill 全量注入）：主模型轮 3.3×，弱模型轮最高 9.5×；对照实验显示，只注入核心标准文档时增益不复现——收益来自整套框架，不是某一份文档。
</details>

<details>
<summary><strong>预注册门判定与覆盖增益</strong></summary>

评测前预注册了通过门槛（防事后挑指标）：同源裁判口径通过 4/7，异构裁判口径通过 5/8（两侧门槛清单不同，其中一项在两个口径下方向相反）。覆盖增益（异构裁判）：用例编写 **+8.7pp**（95% CI [0.5, 15.4]）、全任务 **+13.2pp**（95% CI [2.8, 26.3]）、缺陷检出 **+9.7pp**（95% CI [3.3, 16.4]），均显著；同源口径 +3.8pp（裁判宽容偏差已量化并勘误，见 [CHANGELOG](./CHANGELOG.md)）。早期 +29pp 的单采样增益经多样本复验证实为噪声。

**口径边界**：评测时把 skill 全部指令一次性预注入，真实宿主是按需加载，不能直接据此推断所有宿主与模型的增益。真实宿主抽查（n=1）未观察到衰减，样本不足以证明两种装载方式等效。成对评审（两份产出对比打分）在三种裁判下平局都过多，胜率指标作废（机制问题）。
</details>

</details>

## 文档导航

| 文档 | 适合何时阅读 |
|------|------|
| [examples/](./examples/) | 看五组 On/Off 产物、选样规则与判读说明 |
| [core/SKILL.md](./skills/core/SKILL.md) | 查共享方法、标准、模板与辅助脚本 |
| [CHANGELOG.md](./CHANGELOG.md) | 查版本变更、历史评测与勘误 |
| [Releases](https://github.com/fishzjp/qa-skills/releases) | 查里程碑版本的增益矩阵快照 |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 贡献内容、理解架构约束、运行公开自检 |
| [RELEASING.md](./RELEASING.md) | 维护者发版、安装实测与分发同步 |
| [llms.txt](./llms.txt) | 供 Agent 检索的产品摘要 |

<details>
<summary><strong>仓库结构</strong></summary>

```text
skills/       产品：各 skill 的 SKILL.md、references/、templates/、scripts/
  core/       共享知识库，文件索引见 core/SKILL.md
examples/     真实 On/Off 产出与判读指南
scripts/      架构与仓库校验器
tests/        产品脚本、守门脚本回归测试与安装器冒烟
.dsh/         dsh 插件与配置
assets/       README / 社交图片与落地页字体
install.sh    仓库安装器（拷贝或软链）
uninstall.sh  对应卸载器
index.html    官网落地页源文件
llms.txt      机器可读产品摘要
```

设计、规划与评测链路（`docs/`、`eval/` 等）由维护者本地维护，不随公开仓库分发。

</details>

## 贡献与反馈

欢迎按[贡献指南](./CONTRIBUTING.md)提交改进。使用问题与经验分享到 [Discussions](https://github.com/fishzjp/qa-skills/discussions)，可复现缺陷与具体需求提交 [Issues](https://github.com/fishzjp/qa-skills/issues)。安全漏洞请按[安全策略](./.github/SECURITY.md)私密报告。

[行为准则](./.github/CODE_OF_CONDUCT.md) · [MIT 许可证](./LICENSE)
