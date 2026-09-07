# Product Marketing Context

> 本文件是 qa-skills 的营销定位底座，供所有营销相关工作（落地页文案、README、目录提交、
> Release 物料、社区帖）引用，保证对外口径单一。格式沿用 marketingskills 库的
> `product-marketing` skill 约定（`.agents/product-marketing.md`）。
> 数字与结论的出处：README 实测效果节 + docs/2026-09-07-competitive-analysis.md。

**Document version:** v1
**Last updated:** 2026-09-07

## Product Overview
**One-liner:** qa-skills 把资深测试工程师的工作方法装进任何 AI 编程助手——11 个 Skill、一条流水线，AI 产出可直接执行的测试资产。
**What it does:** 以纯 Markdown Skill（Agent Skills 标准）形式，为 AI 编程助手提供从需求分析、测试策略、用例设计、用例评审、自动化执行、缺陷分析、回归测试到测试报告的完整测试工程方法，附跨会话项目知识库（qa-memory）与薄编排入口（qa）。核心产出标准：没读过需求的人拿着文件能直接开工。
**Product category:** Agent Skills / AI 编程助手的测试工程（QA）技能包——用户在 "QA skills for AI agents"、"testing skills" 货架上找我们。
**Product type:** 开源（MIT）非软件产品：11 个 skill 目录 + core 共享知识库，无运行时、无账号、无遥测。
**Business model:** 免费，无付费层。成本诚实披露：Token 消耗约为无 skill 的 3.3 倍（主模型轮）。

## Target Audience
**Target companies:** 用 Claude Code / Cursor / Codex 等 AI 编程助手做开发的团队与个人；规模不限，独立开发者到中型产研团队。
**Decision-makers:** ① QA 工程师 / 测试开发（向 AI 协作转型的先行者）；② 独立开发者 / 小团队（没有专职测试，AI 是唯一"测试同事"）；③ 工程效能负责人（关注 AI 产出质量的可验证性）。
**Primary use case:** 对 AI 助手说"帮我测试这个需求"，得到可执行用例、测试策略与报告，而不是看似专业、实则不可执行的输出。
**Jobs to be done:**
- 让 AI 产出的测试资产真的能执行、能判定、能交付
- 发布前有人（有 Agent）把住质量关：风险有证据、决策留痕
- 测试知识跨会话沉淀（环境怪癖、flaky 判定、缺陷模式）
**Use cases:**
- 从 PRD/需求描述生成用例（markmap 给人 + schema.yaml 给机器）
- 存量用例审查、用例转自动化（Playwright / pytest / k6）
- Bug 定位到代码行 + 回归范围推算

## Problems & Pain Points
**Core problem:** 通用大模型写测试输出"看似专业、实则无法执行"：判定模糊、占位符未替换、无时限、虚构入口；且从不给出显式的类型决策（提到性能安全 ≠ 决定测不测）。
**Why alternatives fall short:**
- 竞品 skill 包：片段化、无生命周期编排、无实测证据
- 官方 webapp-testing 等：单点工具，无方法论体系
- 直接问大模型：纪律缺失，输出质量靠运气
**What it costs them:** 用例写完不能跑；漏测上线缺陷；AI 输出无法验收。
**Emotional tension:** "AI 写得头头是道，我却在替它擦屁股"——产出无法信任的不安。

## Competitive Landscape
**Direct:** PramodDutta/qaskills（217★，分发机器强、内容浅）；naodeng/awesome-qa-skills（196★，79×2 广度+双语，单 skill 薄）；petrkindlmann/qa-skills（113★，50 skill 实用主义）；LambdaTest/agent-skills（367★，厂商背书生成器）。
**Secondary:** anthropics/skills 的 webapp-testing（单点工具）；addyosmani 的 TDD/browser-testing（个人品牌大库）；obra/superpowers（流程纪律类）。
**Indirect:** testzeus-hercules、stagehand、playwright-mcp 等执行运行器——互补而非竞对（它们是"手"，我们是"方法论"）。
**How each falls short:** 无一同时具备：十环生命周期闭环 × 预注册实测证据链 × 弱模型工程化。

## Differentiation
**Key differentiators:**
- 十环闭环（需求→…→报告→知识沉淀），生态内唯一
- 实测证据链唯一：预注册门判定、异构裁判、不利指标如实披露（用例规格符合度 0.26→0.98；类型查全率 0→0.88；植入 Bug 检出 75%）
- 弱模型工程化唯一：8 条可执行性硬标准一票否决、脚本预填表、预算纪律
- qa-memory 跨会话项目知识库唯一（含投毒威胁模型与门禁）
**How we do it differently:** 三层架构（触发边界 / 工作流 / 按需加载）让指令更少遵循更强；文件即流水线状态，中断可接力；关键决策人工裁决落盘不可推翻。
**Why that's better:** 增益来自整套框架（对照实验：只注入核心标准文档增益不复现），不是提示词技巧。
**Why customers choose us:** 每一个数字都来自实测——该品类唯一"敢把不好看的数字也放出来"的产品。

## Objections
| Objection | Response |
|-----------|----------|
| Token 成本 3.3 倍？ | 如实披露、写在首页：效果更好但更贵；对照实验证明收益来自整套框架；预算上限由你裁决 |
| 我的宿主支持吗？ | 纯 Markdown（frontmatter + 相对路径引用），不依赖宿主特性；Claude Code 端到端实测，skills.sh 一行装到 70+ 宿主；不支持子代理的宿主自动退化为顺序会话 |
| 和官方 webapp-testing 什么关系？ | 那是 Playwright 单点工具；我们提供从需求到报告的完整方法论，自动化执行环节按 Page Object 规范产出 Playwright 代码 |
| 全中文，英文团队能用吗？ | 产品本体当前中文（诚实边界）；英文层在路线图上；需求/代码为中英混合时可正常工作 |
| 会不会污染我的项目？ | 零运行时零遥测：装的是 Markdown 文件；产出与 .qa/ 知识库都在你自己的仓库里，随你的 git 管控 |

**Anti-persona:** 找单元测试 / TDD 方法论的纯开发侧（红海，有 85 万安装的 tdd 等）；找测试管理平台（TestRail/Jira 集成）的团队；找移动端真机 / 渗透 / 混沌工具链的团队（显式不做，边界即卖点）。

## Switching Dynamics
**Push:** AI 测试产出不可执行、不可验收；测试决策缺位导致漏测。
**Pull:** 实测数字（26%→98% 等）+ 一行命令安装 + 一句话开工。
**Habit:** "直接问大模型就行"——大多数场景下确实能用，直到产出要交付、要上 line。
**Anxiety:** 装一堆指令文件会不会把上下文搞乱？关键决策被 AI 抢走怎么办？——三层架构按需加载 + 四类检查点人工裁决是对焦回答。

## Customer Language
**How they describe the problem:**
- "AI 写的用例看着挺专业，实际跑不起来"
- "让它测点东西，它自己想当然"
**Words to use:** 可执行、判定、证据、流水线、裁决、实测
**Words to avoid:** 革命性、颠覆、完美、一站式、赋能
**Glossary:**
| Term | Meaning |
|------|---------|
| 类型决策矩阵 | 十个测试类型逐一必答（纳入/排除留痕），落盘为 type_scope |
| 可执行性 | 8 条硬标准；不可执行用例覆盖再全计零分 |
| 证据分级 E0–E4 | 每条结论标注证据等级，风险评级必须给证据 |
| 检查点裁决 | 澄清 / 执行策略 / Bug 定性 / 预算四类，AI 只提案不代答 |

## Brand Voice
**Tone:** 诚实、直接、克制——工程师写给工程师。
**Style:** 短句、具体数字、不利指标照样披露；不喊口号。
**Personality:** 严谨、透明、务实。

## Proof Points
**Metrics:** 用例规格符合度 0.26→0.98（跨两生成模型复现 0.20→0.99）；E2E 真实执行 0/9→通过（单任务×3 采样）；植入 Bug 检出 75%（异构裁判）；类型查全率 0→0.88（最弱模型）；覆盖增益 +8.7pp / +13.2pp / +9.7pp（CI 下限均 >0）。
**Customers:** 早期阶段，无 logo；以 examples/ 的 On/Off 产出对照代替证言。
**Value themes:**
| Theme | Proof |
|-------|-------|
| 可执行 | 8 条硬标准 + 26%→98% |
| 决策不缺位 | 类型查全率 0→0.88 + 决策留痕 |
| 诚实 | Token 3.3× 与不利指标公开在首页 |

## Goals
**Business goal:** 成为"QA skills for AI agents"品类的内容与信任第一名，装机量追平分发差距。
**Conversion action:** 复制执行 `npx skills add fishzjp/qa-skills --skill '*'`（skills.sh 安装数为北极星分发指标）。
**Current metrics:** skills.sh 收录、安装量两位数级（2026-09-07）；GitHub 24★；npm 断档 v0.7.0 待 OTP。

## Changelog
*Newest first. One line per revision: what changed and why.*
- v1 (2026-09-07) — Initial context. 依据 README 实测数据与 2026-09-07 竞品分析自动起草（marketingskills/product-marketing v2.1.0 流程 option 1）。
