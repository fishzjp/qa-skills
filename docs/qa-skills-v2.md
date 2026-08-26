# QA Skills v2 产品与架构规划文档

> **文档状态**：v2.4（2026-08-20）
>
> **v2.4 变更**（第三轮审查修复，冻结基线）：① Test Case Schema 落盘路径定为 `{项目}/测试用例.schema.yaml`（7.4 补存放约定，5.3 落盘表同步，审查修订后重新抽取）；② exploratory-testing 补输入 / 输出定义与落盘行（`探索笔记_{主题}.md`），补齐第 8 章统一模板；③ 5.4 会话模型补降级路径——宿主不支持子会话时退化为顺序会话 + 文件衔接，正确性不变；④ Phase 1 显式列入 `core/executability.md` 落地时点；⑤ 风险 ↔ 用例双向引用声明主从（`case.risk_ref` 权威、`risk.anchors` 派生）；⑥ 第 11 章点明执行策略裁决与 `automation_plan` 的提案 / 确认关系；⑦ 12.4 补 Skill 版本纪律（PR + 版本号 + 质量门合入）。
>
> **v2.3 变更**（第二轮审查修复）：① 报告模板统一为 `core/report-template.md` 单一来源，消除三处引用两种路径的不一致；② 第 16 章依赖链与第 13 章 Phase 归属对齐（Schema 属 Phase 1）；③ 新增 `core/executability.md`，可执行性标准独立成文件，不再与测试原则混装；④ 新增 5.4 编排会话模型——阶段间上下文隔离，正面回应"每任务 1–3 个 Skill"经验阈值；⑤ Test Case Schema 新增 `code_refs` 字段，regression-testing 追溯映射 v0 明确落到代码证据清单；⑥ 6.2 补 description 划界约束、5.1 与第 11 章补 exploratory-testing 旁路、Phase 1 补黄金集标注成本预估、第 10 章补 SkillOpt 工具参考。
>
> **v2.2 变更**：明确 v2 改造的两个核心动机并贯穿全文——① Skill 过载（知识库 / 工作流 / 规则引擎 / 输出模板 / QA 方法论五种角色混装，规则越多 ≠ Agent 越强）；② 用例可执行性（"看似专业但不可执行"是当前最大质量问题）。相应新增 1.3 设计动机、7.6 用例可执行性标准；第 10 章升级为硬规范（SKILL.md ≤ 500 行红线 + 职责分离，引用 Red Hat ACE 实践总结）；12.2 新增 Executability 一票否决指标；tcw 拆分从"优化项"升级为 Phase 1 正式动作。
>
> **v2.1 变更**（经全面审查修订）：
> 1. 新增**编排层设计**（`qa` 入口 Skill）与**产出落盘原则**，解决"帮我测试这个需求"终态与平级 Skill 触发冲突的矛盾
> 2. 新增**能力迁移矩阵**，消除"现有能力继续保留"与新 Skill 职责重叠的矛盾
> 3. `core/` 去掉 SKILL.md，改为纯共享引用目录，不会被独立触发
> 4. 风险模型改为 **Impact × Likelihood 两因子**，风险等级与用例优先级两套体系脱钩，评级强制挂证据
> 5. 合并两处证据表述为**统一 E0–E4 体系**，补充静态 / 动态 / 意图三类裁决规则
> 6. Test Case Schema 改为**双轨制**（markmap 给人、Schema 给机器）并补全字段；多端扇出标注为远期独立项目
> 7. Eval 补齐方法学（Ground Truth / Evaluator / 环境固定 / 合规），**黄金集前置到 Phase 1** 并作为 Benchmark 种子
> 8. `test-report` 降级为报告模板（qa 收尾步骤）；`test-review` 更名 `test-case-review`；性能 / 安全不再自研 Skill，改为集成点
> 9. 全文格式统一：标题层级、章节编号、示意数据标注、清单一致性

## 目录

- [1. 项目定位](#1-项目定位)
- [2. 核心设计理念：四大支柱](#2-核心设计理念四大支柱)
- [3. 统一证据体系（Evidence System）](#3-统一证据体系evidence-system)
- [4. 统一风险模型（Risk Model）](#4-统一风险模型risk-model)
- [5. 总体架构与编排层](#5-总体架构与编排层)
- [6. Skill 体系与目录结构](#6-skill-体系与目录结构)
- [7. 产物 Schema 体系](#7-产物-schema-体系)
- [8. 各 Skill 职责定义](#8-各-skill-职责定义)
- [9. 能力迁移矩阵](#9-能力迁移矩阵)
- [10. 三层架构规范（L1 / L2 / L3）](#10-三层架构规范l1--l2--l3)
- [11. QA Agent 完整工作流](#11-qa-agent-完整工作流)
- [12. Eval 体系与 Benchmark](#12-eval-体系与-benchmark)
- [13. 开发优先级](#13-开发优先级)
- [14. 最终产品形态](#14-最终产品形态)
- [15. 项目核心竞争力](#15-项目核心竞争力)
- [16. 实施建议](#16-实施建议)

---

## 1. 项目定位

### 1.1 项目目标

构建一套面向软件测试工程师的 Agent Skills，使 AI 能够参与软件测试全流程：

> **需求理解 → 风险分析 → 测试策略 → 测试设计 → 测试用例 → 自动化执行 → 缺陷分析 → 回归验证 → 测试报告**

### 1.2 当前基础

项目已具备两个 Skill，形成从**测试设计到自动化执行**的初步闭环：

- `test-case-writing`：测试用例设计与覆盖度自审（代码优先、测准声明、Cx/Dn 缺陷记录）
- `automated-e2e-testing`：Playwright E2E 自动化、业务熟悉探索、Bug 证据记录

### 1.3 设计动机：v2 要解决的两个真实问题

**问题一：Skill 过载，规则越多 ≠ Agent 越强。** 当前两个 Skill 同时承担"知识库 + 工作流 + 规则引擎 + 输出模板 + QA 方法论"五种角色。外部实践已验证这条红线的存在——Red Hat ACE 团队对 Agent Skill 的实践总结（2026-07）明确指出：L2 指令超过 500 行后性能开始退化；"试图覆盖整个领域的全能型 Skill 往往使性能退化"；大量 Skill 正文是不可执行的非动作性内容，压缩反而提升质量。超出 Agent 有效遵循能力的规则只是噪音，还会稀释真正重要的约束。**解法**：第 10 章三层架构硬规范——SKILL.md 只装触发边界与工作流，方法 / 规则 / 模板 / 方法论下沉 references 与 core/。

**问题二：生成"看似专业但不可执行"的用例。** 容易产出一堆覆盖矩阵漂亮、术语专业，但根本不符合实际测试场景的用例——测试工程师拿着无法执行：入口是虚构的、数据是占位符、判定无时限、断言超出可验证范围。**解法**：7.6 用例可执行性标准（框架级硬标准）+ 12.2 Eval 的 Executability 一级指标（不可执行的用例，覆盖再全也计零分）。

> 本章之后的所有设计（编排层、Schema、Eval、拆分）都服务于这两个问题。评审任何新增规则时先问一句：它让 Agent 更强了，还是只是更长了？

### 1.4 演进方向

下一阶段不是简单增加 Skill 数量，而是从：

> **QA Skills 工具集**

升级为：

> **面向软件测试全生命周期的 QA Agent Skills Framework**

关键升级动作不是"加 Skill"，而是：补编排层、统一模型（风险 / 证据 / Schema）、建立度量（Eval）。

---

## 2. 核心设计理念：四大支柱

### 2.1 Code-aware

理解真实代码，而不是只读 PRD。代码是静态事实的最高来源（详见 [第 3 章](#3-统一证据体系evidence-system) 裁决规则）。现有 `test-case-writing` 的"代码优先 + 测准声明"已是这一支柱的落地形态。

### 2.2 Risk-driven

围绕风险设计测试，而不是机械生成测试用例。测试不再是"想到什么测什么"，而是**风险 → 策略 → 用例**的推导链（详见 [第 4 章](#4-统一风险模型risk-model)）。

### 2.3 Evidence-driven

所有测试结论都尽可能建立在真实证据之上，而不是模型猜测。每个发现标注证据等级、来源、置信度与验证状态（详见 [第 3 章](#3-统一证据体系evidence-system)）。

### 2.4 Evaluated

所有 Skill 都有量化指标，能回答"用了 Skill 后，Agent 的测试能力到底提升了多少"，而不是"这个 Skill 看起来好不好"（详见 [第 12 章](#12-eval-体系与-benchmark)）。

---

## 3. 统一证据体系（Evidence System）

> 本章是全框架唯一的证据规范，所有 Skill 统一引用 `core/evidence.md`，不得各自发明证据语言。

### 3.1 证据强度等级

```text
E0  用户初始陈述    ← 未经核实的用户描述（最低）
E1  文档证据        ← PRD / 设计文档 / API 文档 / FAQ
E2  代码证据        ← 文件:行、接口签名、数据结构
E3  运行/执行证据   ← 实际运行结果、测试执行结果、日志、截图
E4  交叉验证        ← 多来源互相印证（最高）
```

### 3.2 三类裁决规则

证据等级解决"信什么"，裁决规则解决"冲突时听谁的"：

| 问题类型 | 裁决规则 |
|---------|---------|
| **静态问题**（代码是怎么写的） | E2 为王。E1 与 E2 冲突 → 默认以代码为准（测准声明），偏离记入附录并提交澄清 |
| **动态问题**（系统实际怎么表现） | E3 为王。E2 与 E3 冲突（代码与运行不符）→ 这本身就是发现（死代码 / 路径未覆盖 / 环境差异），转澄清或缺陷记录 |
| **意图问题**（应该是什么行为） | **用户在澄清环节的明确答复具有最终裁决力**，可推翻任何证据等级。裁决记入产物（澄清记录），后续 Skill 不得再用代码推翻已裁决项 |

> 注意：E0（用户初始陈述）是低证据，但用户**在澄清环节的裁决**不是证据、是决策——两者必须区分。前者可被代码推翻，后者不可。

### 3.3 结论的状态标注

所有 Skill 的输出必须区分：

```text
Fact        事实（有证据支撑的确定结论）
Inference   推断（由证据合理推出，未直接验证）
Risk        风险（可能出问题，尚无证据）
Hypothesis  假设（待验证的猜想）
Verified    已验证（有 E3 及以上证据）
```

### 3.4 标注格式

```yaml
finding:
  title: 删除用户后可能存在数据残留
  evidence:
    level: E2                    # E0–E4
    source: user_service.go:124
  confidence: medium             # high / medium / low
  status: needs_verification     # fact / inference / risk / hypothesis / verified
```

禁止不加标注直接输出"这里存在 Bug"——这是证据体系要消灭的幻觉式结论。

---

## 4. 统一风险模型（Risk Model）

> 所有 Skill 统一引用 `core/risk-model.md`。风险模型与证据体系强制挂钩：**没有证据的风险评级视为无效评级**。

### 4.1 风险评分

```text
Risk Score = Impact × Likelihood
```

- Impact（影响）、Likelihood（可能性）各取 1–5，乘积 1–25
- **Change Scope（变更范围）与 Complexity（实现复杂度）不是乘子**，它们是估计 Likelihood / Impact 的启发式输入（见 4.2）

### 4.2 两个因子的估计方法

| 因子 | 估计输入 |
|------|---------|
| Impact | 失败后果分级：数据丢失 / 资损 / 安全 > 核心功能不可用 > 部分功能降级 > 体验问题 |
| Likelihood | 变更范围（diff 大小与涉及面）、实现复杂度、历史缺陷密度、代码证据（如边界未防护、事务不完整） |

### 4.3 风险等级（与用例优先级是两套体系）

```text
Critical   20–25
High       10–19
Medium     4–9
Low        1–3
```

> **命名脱钩**：风险等级用 Critical / High / Medium / Low；用例优先级沿用 P0 / P1 / P2（`test-case-writing` 现行体系）。不用 P0–P3 给风险命名，避免同名歧义。

风险等级到用例优先级的**映射建议**（策略阶段可调整，但必须显式说明理由）：

| 风险等级 | 用例优先级要求 |
|---------|---------------|
| Critical | 必须有 P0 用例，且作为回归锚点 |
| High | P0 或 P1 |
| Medium | P1 |
| Low | P2 或按需 |

### 4.4 Risk Map 标注格式

```yaml
risk:
  id: R1
  feature: 用户删除
  dimension: 数据一致性          # 维度如：权限 / 数据一致性 / 边界 / 状态流转 / 并发 / 兼容性
  impact: 5                      # 删除后残留导致隐私与合规问题
  likelihood: 3                  # user_service.go:124 删除事务未覆盖关联表
  level: High                    # 15 = 5 × 3
  evidence:
    level: E2
    source: user_service.go:124
  confidence: medium
  status: needs_verification
  anchors: [TC-07-02]            # 覆盖此风险的用例编号（派生索引，主从规则见下）
```

> **双向引用主从规则**：`case.risk_ref`（7.4）为权威方向，只在用例侧维护；`risk.anchors` 是由 Schema 抽取派生的反向索引，每次抽取再生、不接受手工编辑——避免两侧漂移。

### 4.5 推导链

```text
Evidence（评级依据）
    ↓
Risk Map（每条风险：等级 + 证据 + 置信度）
    ↓
Test Strategy（风险决定测什么、测多深）
    ↓
Test Case（risk_ref 反向追溯到风险锚点）
```

---

## 5. 总体架构与编排层

### 5.1 能力体系总览

```text
                          qa（编排入口）
                                │
              ┌─────────────────┴─────────────────┐
              │                                   │
         Understand                            Execute
              │                                   │
              ↓                                   ↓
    requirement-analysis                automated-e2e-testing
              ↓                                   api-testing
        test-strategy（Risk Map）                   │
              ↓                                   ↓
        test-case-writing                       Evidence
              ↓                                   ↓
        test-case-review                     bug-analysis
              │                                   ↓
              └─────────────────┬──────────── regression-testing
                                ↓
                          测试报告（qa 收尾）
```

> 旁路：文档缺失 / 系统陌生时，`exploratory-testing` 在 requirement-analysis 之前先行，探索产出（系统理解 + 风险清单）作为需求建模的输入。

### 5.2 编排层：`qa` 入口 Skill

**矛盾与解法**：终态愿景是用户只需说"帮我测试这个需求"，但 Skill 靠 description 触发，多个阶段 Skill 的 description 必然重叠（"帮我测这个需求"同时命中需求分析 / 策略 / 用例编写）。解法是**唯一端到端入口 + 阶段 Skill 各司其职**：

- `qa` 是唯一面向"端到端测试"意图的入口 Skill
- 阶段 Skill 服务于"只要这个阶段产出"的意图（如"帮我审一下这份用例"）

`qa` 的职责（**薄编排，不含领域知识**）：

1. **意图识别与路由**：判断用户要端到端流水线还是单阶段，单阶段直接移交给对应 Skill
2. **流水线串联**：按第 11 章工作流调度阶段 Skill，以上一阶段的**落盘产物**为下一阶段输入；各阶段在独立上下文中运行（见 5.4 会话模型）
3. **检查点管理**：在需要人工输入的环节暂停等待（澄清答复、执行策略裁决、Bug 定性裁决，见 14.2）
4. **收尾**：汇总各阶段产物，按 `core/report-template.md` 生成测试报告
5. **断点续跑**：流水线状态全部在文件里，新会话读文件即可继续

`qa` 不做：不包含任何测试方法、框架知识（全部在阶段 Skill 与 `core/`）；不替用户做裁决。

### 5.3 产出落盘原则（文件即流水线状态）

> 每个阶段的产出必须落盘为文件，跨会话可续。这是长流水线在上下文限制下能跑通的前提，也是回归追溯的数据基础。

| 阶段 | 落盘产物 |
|------|---------|
| exploratory-testing（旁路） | `{项目}/探索笔记_{主题}.md`（charter、系统理解、风险清单、测试想法），作为需求建模输入 |
| requirement-analysis | `{项目}/需求模型.md`（含澄清记录） |
| test-strategy | `{项目}/测试策略.md`（含 Risk Map） |
| test-case-writing | `{项目}/测试用例_markmap.md` + `{项目}/测试用例.schema.yaml`（机器可读抽取产物，见 7.4） |
| test-case-review | 直接修订用例文件（修订后重新抽取 Schema）+ 审查记录（文件末尾附录） |
| 执行 | `playwright/` 测试代码 或 API 脚本 + 运行结果 |
| bug-analysis | Bug 条目（根因 / 影响 / 回归建议）追加进测试报告 |
| regression-testing | `{项目}/回归清单_{日期}.md` |
| qa 收尾 | `{项目}/测试报告_{日期}.md` |

### 5.4 编排会话模型（阶段间上下文隔离）

> 外部实践指出：单任务同时激活的 Skill 超过 1–3 个后，认知开销与指令冲突会"主动伤害"效果。`qa` 流水线端到端要经过 6–8 个阶段 Skill——**不与该阈值冲突的前提是阶段间上下文隔离**，而不是把所有 Skill 装进一个会话。

会话模型：

- **每个阶段运行在独立上下文中**（独立子会话 / 子代理）：只加载当前阶段 Skill 的 SKILL.md + 按需 references + 上一阶段的落盘产物文件
- **qa 主会话只持有流水线状态**：阶段清单、各产物文件路径、检查点状态——不加载任何阶段 Skill 的领域知识
- **任一时刻活跃指令 ≤ 1–2 个 Skill**（当前阶段 + qa 编排），符合经验阈值
- 反模式：单会话内顺序累加加载全部 SKILL.md（8 个 × 数百行 = 数千行指令同时在场），正是"指令冲突"的教科书场景
- **降级路径**：会话模型依赖宿主的子会话 / 子代理能力。宿主不支持、或用户在单会话内手动走流水线时，退化为**顺序会话 + 落盘文件衔接**——正确性不受影响（5.3 保证状态在文件里），损失的只是上下文卫生（历史阶段的指令仍占上下文）

> 5.3 的落盘原则因此有双重身份：不只是"跨会话可续"的恢复机制，更是阶段间上下文隔离的**传递介质**——文件是阶段之间唯一的耦合方式。

### 5.5 触发与反触发原则

- 每个阶段 Skill 的 SKILL.md **必须**有 When NOT to Use，且指明"交给谁"
- 阶段 Skill 之间职责重叠的边界，以第 9 章迁移矩阵为准
- 完整触发 / 反触发表见 6.2

---

## 6. Skill 体系与目录结构

### 6.1 目录结构

```text
qa-skills/
│
├── qa/                          # 编排入口（唯一面向"帮我测试这个需求"的 Skill）
│   └── SKILL.md                 # 报告模板等共享资源引用 core/，不在本目录重复存放
│
├── core/                        # 共享知识库（无 SKILL.md，不是 Skill，不会被独立触发）
│   ├── testing-principles.md    # 测试原则、测试设计方法选择（方法索引 → methods/）
│   ├── methods/                 # 设计方法细则：boundary / data-driven / permission / state-machine
│   ├── risk-model.md            # 统一风险模型（第 4 章）
│   ├── evidence.md              # 统一证据体系（第 3 章）
│   ├── executability.md         # 用例可执行性标准（7.6，供所有产用例的 Skill 引用）
│   ├── report-template.md       # 测试报告模板（唯一来源，qa 收尾引用）
│   ├── case-format.md           # 用例格式硬约束（产用例 / 修订用例的 Skill 统一遵守）
│   ├── coverage.md              # 覆盖度检查表（19 维 + 代码审查发现模式清单）
│   ├── schema-extraction.md     # Test Case Schema 抽取规则（唯一来源）
│   ├── clarify-pattern.md       # 统一澄清 / 确认提问格式与裁决落盘规则
│   └── scripts/                 # validate_schema.py（Schema 校验器，零第三方依赖）
│
├── requirement-analysis/
│   └── SKILL.md
│
├── test-strategy/
│   └── SKILL.md
│
├── test-case-writing/
│   ├── SKILL.md
│   └── templates/
│       └── markmap_template.md  # 用例文件拼装起点模板（含详细格式范例）
│
├── test-case-review/
│   └── SKILL.md
│
├── automated-e2e-testing/
│   ├── SKILL.md
│   └── references/
│       ├── playwright-conventions.md   # 脚手架 / 配置 / 场景代码模板 / Page Object 规范
│       └── helpers_reference.md        # 通用 Helper 脱敏参考实现
│
├── api-testing/
│   └── SKILL.md
│
├── exploratory-testing/
│   └── SKILL.md
│
├── bug-analysis/
│   └── SKILL.md
│
├── regression-testing/
│   └── SKILL.md
│
└── eval/                        # 黄金集与 Benchmark（非 Skill，见第 12 章）
    ├── harness/                 # 评测脚本（跑任务、算指标）
    ├── golden/                  # 黄金集任务（Input / 标注 / Expected）
    └── results/                 # 评测结果归档
```

> **布局注记（2026-08-22 收敛后；2026-08-26 补充过期项清单）**：本树为 v2 规划时的仓库布局；公开仓库现已收敛为 skills 产品内容，`eval/` 与 `tests/` 转为维护者本地目录，公开侧证据链改为每版 Release 附增益矩阵快照。
> 三处按 v2 时点冻结、已被后续迭代取代的表述——①② 在本节，③ 在 §7.4：① 目录树中 core/ 注释「无 SKILL.md」且 scripts/ 只列 validate_schema.py——现行 core/SKILL.md 已存在（安装依赖单元，frontmatter 声明不可独立触发），scripts/ 另含 scan_signals.py（类型信号扫描器）；② 下文「关于 core/ 的两条硬规则」第 1 条同此演进；③ §7.4 Schema 的 type 枚举未含后续新增的 security_business / performance / compatibility / i18n。现行结构以 skills/ 实际内容、[CONTRIBUTING](../CONTRIBUTING.md) 架构红线与 [decision-layer-design](./decision-layer-design.md) 为准。

关于 `core/` 的两条硬规则：

1. **`core/` 不含 SKILL.md**——含 SKILL.md 的目录就是一个可被独立触发的 Skill，会让 `core` 加入触发竞争。`core/` 是纯共享引用目录
2. 各 Skill 通过相对路径按需引用（如 `../core/risk-model.md`），在自己的工作流步骤中标注"此时加载"，遵循渐进披露

### 6.2 Skill 清单与触发边界

| Skill | 触发（何时用） | 反触发（何时不适用 → 交给谁） |
|-------|--------------|------------------------------|
| `qa` | "帮我测试这个需求 / 功能"等端到端意图 | 只要单阶段产出 → 对应阶段 Skill |
| `requirement-analysis` | 需要系统性建模某需求 / 系统（目标、范围、规则、异常、依赖、不明确项） | 已有需求模型、直接写用例 → `test-case-writing` |
| `test-strategy` | "这个功能应该怎么测"（范围、类型、深度、优先级） | 已有策略、直接写用例 → `test-case-writing` |
| `test-case-writing` | 从需求 / 代码产出可执行的手动用例文件 | 写自动化代码 → `automated-e2e-testing`；审已有用例 → `test-case-review` |
| `test-case-review` | 审查已有用例（存量 / 他人写的）的覆盖与质量 | 从零写用例 → `test-case-writing`；写时自审 → `test-case-writing` 阶段四 |
| `automated-e2e-testing` | 用例 → Playwright、Web UI 自动化执行、Bug 证据记录 | 纯 API 接口 → `api-testing`；性能 / 安全 → 专项（见 6.3）；独立探索会话 → `exploratory-testing` |
| `api-testing` | 接口级测试（参数 / 边界 / 鉴权 / 幂等 / 并发） | Web UI 流程 → `automated-e2e-testing` |
| `exploratory-testing` | 无文档 / 新系统的独立探索式测试会话（charter 驱动） | 为写自动化踩点 → `automated-e2e-testing` 工作流零 |
| `bug-analysis` | 已确认 Bug 的根因定位、影响分析、回归建议 | 仅记录 Bug 证据 → `automated-e2e-testing` 工作流二；审查发现类疑似缺陷 → `test-case-writing` Cx 记录 |
| `regression-testing` | 代码变更 → 回归范围选择（必须 / 建议 / 可选） | 用例文件的增量修改本身 → `test-case-writing` 增量更新流程 |

> 本表同时约束 **description 措辞**：各 Skill 的 SKILL.md description 撰写必须按本表划界——`qa` 独占"端到端 / 全流程 / 帮我测试"意图词，阶段 Skill 的 description 只描述本阶段意图，必要时写明"不要用于 X"（L1 负向约束）。否则触发层的语义竞争会让本表形同虚设。

### 6.3 性能与安全：不自研，作为集成点

> **取代注记（2026-08-23）**：本章决策已由 `docs/decision-layer-design.md` 升级为「**方法论与决策自研，执行层对接专业工具**」——性能 / 安全成为类型域正式轴（`core/test-type-matrix.md`），handoff 协议做实（移交包 + 回收格式 + V5 校验）。本章保留下文作历史决策记录。

性能测试与安全测试**不在本框架自研 Skill 清单内**。理由：两者已有成熟专业工具与生态，自研 Skill 只会稀释焦点。落地方式：

- `test-strategy` 的输出中，性能 / 安全维度用 `handoff` 标注移交（如 `performance: { include: false, handoff: "专项：k6" }`）
- 需要时对接专业工具（k6 / locust、安全审计类 Skill / 工具），本框架只负责在策略层面识别"需要专项"并在测试报告中预留入口

---

## 7. 产物 Schema 体系

### 7.1 三大产物与流转关系

Skill 之间靠**落盘产物**衔接，三大核心产物各有 Schema：

```text
PRD / Code
    ↓
需求模型（requirement-model）── requirement-analysis 产出
    ↓
测试策略（test-strategy，含 Risk Map）── test-strategy 产出
    ↓
测试用例（test-case，双轨：markmap + Schema）── test-case-writing 产出
    ↓
执行 / 审查 / 回归 各 Skill 消费
```

### 7.2 Requirement Model Schema（轻量）

```yaml
requirement_model:
  goal:                     # 需求目标
  scope:                    # 功能范围（含明确的非目标）
  roles: []                 # 角色 → 能做什么 / 不能做什么
  inputs: []                # 输入
  outputs: []               # 输出
  states: []                # 状态与流转
  rules: []                 # 业务规则（每条带 evidence）
  exceptions: []            # 异常情况
  dependencies: []          # 依赖关系
  open_questions: []        # 不明确事项 → 澄清记录（含用户裁决）
```

### 7.3 Test Strategy Schema（轻量）

```yaml
test_strategy:
  feature:
  scope:
    functional:    { include: true, depth: full,     rationale: "核心资损路径" }
    boundary:      { include: true, depth: standard }
    permission:    { include: true, depth: full,     rationale: "R2 权限风险 High" }
    regression:    { include: true, depth: standard }
    compatibility: { include: true, depth: light }
    performance:   { include: false, handoff: "专项：k6" }
    security:      { include: false, handoff: "专项：安全审计" }
  automation_plan:          # 哪些用例自动化、用什么框架
  regression_plan:          # 回归策略
  risk_map_ref:             # 指向 Risk Map（每条风险含证据，见 4.4）
```

> 策略粒度是 **范围 + 深度 + 理由**（为什么测 / 测多深 / 为什么不测），不是布尔开关；每项纳入理由应能追溯到 Risk Map 中的风险编号。

> **扩展注记（2026-08-23）**：scope 已由决策层设计升级为 functional_scope + type_scope（类型域十轴全轴必答，G 级脚本扫描 + S 级复核）+ depth_budget（full ≤3 预算），性能 / 安全从 handoff 占位升级为正式轴——现行结构见 test-strategy 的 SKILL.md 与 `core/test-type-matrix.md`。

### 7.4 Test Case Schema（双轨制）

**双轨原则**：

- **markmap 文件是给人的交付物，也是唯一人工维护源**（source of truth for humans）——沿用现有 `test-case-writing` 的全部硬约束（正文零代码内部、TC 编号、导读四件套、执行模型判定、异步判定时限等）
- **Schema 是机器可读的元数据层**，由 Skill 在加工时**从 markmap 单向抽取**，作为 Skill 间流转接口（供 test-case-review、regression-testing、执行层消费），**不要求人维护两份**
- **存放约定**：抽取产物落盘为 `{项目}/测试用例.schema.yaml`，与 markmap 同目录；markmap 修改后（增量更新、审查修订）重新抽取，Schema 永远可由 markmap 再生

```yaml
test_case:
  id: TC-02-03                  # TC-{模块号}-{序号}
  title:
  module:                       # 所属模块（状态机节点 / 子模块）
  priority: P0 | P1 | P2        # 用例优先级（与风险等级两套体系，见 4.3）
  type: functional | boundary | exception | permission | regression | state | data
  execution_model: ui | dev-collab   # 有 UI 独立执行 / 无 UI 开发协作
  smoke:                        # 冒烟序号（如 SMOKE-1），非冒烟则省略
  preconditions: []             # 该条特有前置（共享前置在模块级声明，不重复）
  steps: []                     # 业务语言；dev-collab 时标注「请开发执行」
  expected: []                  # 明确唯一；异步行为必含判定时限
  test_data: {}                 # 具体数据，不写占位符
  risk_ref:                     # 关联的风险编号（Risk Map 的 id，如 R1）
  code_refs: []                 # 代码级追溯锚点（文件:行，由用例附录「代码证据清单」抽取，供 regression-testing 消费）
  evidence:                     # 该用例依据的证据（level / source / confidence）
  tags: []                      # [需真机] / [需Mock] / [需专业环境]
  automation:
    supported: yes | no | partial
    framework:                  # playwright / api / manual
  status: active | changed | deprecated   # 增量更新用
```

**存量迁移**：已有 markmap 用例文件通过抽取规则生成 Schema（TC 编号、优先级、模块结构都是现成的锚点），存量文件不需要人工重写。

### 7.5 多端执行扇出（远期独立项目）

从 Test Case Schema 自动生成多端测试代码（Web / API / Mobile）本质是一个**测试代码生成器**项目，有自己的工程量与验证体系，**不作为 Schema 的自然结果顺带实现**，单独立项、单独验证。近期执行策略由 `test-strategy` 的 `automation_plan` 人工裁决 + `automated-e2e-testing` / `api-testing` 落地。

> 注：性能测试不从功能用例派生（压测模型独立设计），不在扇出范围内，见 6.3。

### 7.6 用例可执行性标准（Executability）

> "看似专业但不可执行"是当前最大质量问题（见 1.3 问题二）。本标准是**框架级硬标准**，所有产出用例的 Skill（test-case-writing、test-case-review、bug-analysis 的回归用例建议）统一遵守，细则落在 `core/executability.md`。

**失败模式——AI 为什么会生成不可执行的用例**：

| # | 失败模式 | 典型表现 |
|---|---------|---------|
| 1 | 凭空想象系统 | 没见过真实页面 / 接口，凭 PRD 与通用经验虚构入口、字段、文案 |
| 2 | 写给评审者而非执行者 | 追求覆盖矩阵漂亮，不关心执行者下一步能不能操作 |
| 3 | 前置不可得 | 默认环境 / 账号 / 数据随手就有，不交代从哪获得 |
| 4 | 判定不可操作 | 预期结果写"功能正常"这类模糊判定；异步行为无判定时限 |
| 5 | 断言超出验证强度 | 两个样本就断言"全局唯一"；UI 操作就断言数据库约束 |

**硬标准**（test-case-writing 已落地的约束在此升格为框架标准）：

1. **代码优先**——有代码必读代码，以实现为行为基线，杜绝凭文档想象（失败模式 1 的根治手段）
2. **执行模型判定**——有 UI 独立执行 / 无 UI 转"测试-开发协作清单"，开工先判定
3. **具体数据**——操作步骤嵌真实编号 / 字段值，禁止占位符
4. **页面可达性**——每个入口写清从哪里到达；未知 → 澄清 + TODO
5. **判定时限**——异步行为必须写"多久不发生即判失败"
6. **断言范围 ≤ 验证强度**——用例名称与实际能证明的范围一致
7. **前置可得性**——环境 / 账号未知时列"TODO：向谁索取"，不省略
8. **零上下文新人复述**——定稿自检：没读过需求、没人讲解的人只拿这份文件能开工

**闭环**：标准靠 Eval 兜底——12.2 的 Executability 指标直接量化（零上下文执行成功率、首步受阻率），不可执行的用例覆盖再全也计零分。

---

## 8. 各 Skill 职责定义

> 每个 Skill 按统一模板描述：定位一句话 / 输入 / 输出（落盘产物）/ 边界。详细触发边界见 6.2。

### 8.1 `qa` — 编排入口

- **定位**：把"帮我测试这个需求"翻译成一条可断点续跑的流水线
- **输入**：需求 + 代码仓库 + 测试环境（用户提供，见 14.2）
- **输出**：各阶段落盘产物 + 最终测试报告
- **边界**：薄编排，无领域知识；单阶段意图移交给阶段 Skill

### 8.2 `requirement-analysis`

- **定位**：回答"这个需求到底要做什么"——建立对系统的正确理解，而不是写测试
- **输入**：PRD、设计文档、API 文档、Bug、Issue、代码
- **输出**：`需求模型.md`（按 7.2 Schema，含澄清记录与用户裁决）
- **边界**：不产出用例；澄清后仍模糊的项如实标注 `open_questions`，不硬猜

### 8.3 `test-strategy`

- **定位**：回答"这个功能应该怎么测"——把风险翻译成测试范围与深度
- **输入**：需求模型、代码、系统架构、历史 Bug
- **输出**：`测试策略.md`（按 7.3 Schema，含 Risk Map）
- **边界**：不写具体用例；策略位于"需求 → 风险分析 → **策略** → 测试设计 → 用例"链路中，跳过策略直接写用例是本框架明确反对的

### 8.4 `test-case-writing`

- **定位**：从需求模型 / 代码产出**人看得懂、能执行**的手动用例文件
- **输入**：需求模型（或原始输入源）、代码仓库、测试策略（可选，无则内置轻量风险判断）
- **输出**：`测试用例_markmap.md`（正文业务语言 + 附录代码证据，沿用现行全部硬约束）+ 抽取的 Test Case Schema
- **边界**：自动化代码 → `automated-e2e-testing`；审他人用例 → `test-case-review`

**设计方法选择**（引用 `core/testing-principles.md`，按功能特征选方法，不强制状态机）：

```text
明显状态流转        → State Machine
输入输出型功能      → Equivalence Partitioning + Boundary Value Analysis
权限系统            → Role × Action × Resource
API                 → Parameter Matrix
复杂业务流程        → Workflow
数据转换            → Input → Transform → Output
历史 Bug 较多       → Regression-focused Testing
```

**架构拆分**（Phase 1 正式动作，见第 13 章；**2026-08-21 已随"skill 自包含重构"落地**）：原 SKILL.md 436 行逼近 500 行红线（第 10 章）且混装方法知识与工作流。拆分动作：方法知识外移共享目录（`core/methods/` 四篇设计方法 + `core/` 格式 / 覆盖 / 抽取规则，清单见 6.1 目录树），SKILL.md 收敛为"触发边界 + 工作流 + 硬约束引用"。拆分红线：硬约束（正文零代码内部、导读四件套、判定时限等）外移后必须在工作流步骤中被显式引用执行，**不得**降级为可选参考。

### 8.5 `test-case-review`

- **定位**：回答"这些测试用例到底测得好不好"——独立审查存量 / 他人用例
- **输入**：PRD、代码、已有用例文件
- **输出**：直接修订用例文件 + 审查记录（缺失 / 冗余 / 错误 / 高风险未覆盖，按 TC 编号列出）
- **评估维度**：Functional / Boundary / Exception / Permission / Regression / Data / State Coverage（分母以黄金集人工标注的可测点清单为基准，见 12.3；日常使用时以审查者与需求模型共同确认的可测点为基准）
- **边界**：写时自审归 `test-case-writing` 阶段四；本 Skill 是**事后、独立**的审查

### 8.6 `automated-e2e-testing`

- **定位**：把手动用例转成 Playwright 测试并执行、记录 Bug 证据——E2E 只是 Test Execution 的一种实现
- **输入**：用例文件（markmap）
- **输出**：Playwright 测试代码、运行结果、Bug 记录（测试报告条目）
- **保留能力**：Page Object、Helper、测试数据管理、业务熟悉（工作流零，为写自动化踩点的小规模探索）、Bug 证据收集（工作流二）
- **移交能力**：独立探索会话 → `exploratory-testing`；Bug 根因分析 → `bug-analysis`（见第 9 章）
- **需同步改写**：description 与 When NOT to Use 中"纯 API → Python 脚本"改为指向 `api-testing`；"探索性测试"表述收窄为"业务熟悉探索"

### 8.7 `api-testing`

- **定位**：接口级测试——E2E 之外的另一条执行路径
- **输入**：API 文档 / 用例文件中 execution_model 可自动化的接口用例
- **输出**：API 测试脚本与运行结果
- **重点覆盖**：参数类型、缺失 / 非法参数、边界值、权限、鉴权、幂等、并发、状态码、错误响应、数据一致性

### 8.8 `exploratory-testing`

- **定位**：需求不完整、系统陌生、文档不足时的**独立**探索式测试会话（charter 驱动：目标 → 探索 → 记录风险 → 产出测试想法与 Bug）
- **输入**：被测系统入口（环境 + 账号）、探索主题或 charter、（可选）已有需求材料
- **输出**：`{项目}/探索笔记_{主题}.md`（charter、系统理解、风险清单、测试想法、发现的 Bug）——旁路场景下作为 requirement-analysis 的输入（见 5.1 / 11 章旁路）
- **与 e2e 的边界**：本 Skill 做以"理解系统 / 发现风险"为目的的完整探索会话；`automated-e2e-testing` 工作流零做以"写自动化前踩点"为目的的小规模探索
- **适用**：新系统、老系统、文档缺失、黑盒测试、Agent 自主测试

### 8.9 `bug-analysis`

- **定位**：对**已确认**的 Bug 做根因定位、影响分析、回归建议
- **工作流**：Bug 报告 → 复现 → 读代码 → 定位根因 → 影响分析 → 回归分析 → 生成回归用例建议
- **输出**：Bug 摘要（现象 / 复现步骤 / Root Cause / Evidence / 影响范围 / Severity / 修复建议 / 回归范围），追加进测试报告
- **边界**：与 `test-case-writing` Cx 缺陷记录（审查发现的**疑似**缺陷，待验证）不同，本 Skill 的输入是**已确认**的 Bug；与 `regression-testing` 衔接：本 Skill 产出回归用例建议，回归范围选择归 `regression-testing`

### 8.10 `regression-testing`

- **定位**：代码变更 → 自动判断应该回归哪些测试
- **输入**：Code Diff、Bug 修复、需求变更、已有用例（含 Schema）
- **分析链**：Changed Files → Changed Functions → Affected Features → Affected Test Cases → Regression Scope
- **输出**：`回归清单_{日期}.md`（必须回归 P0 / 建议回归 P1 / 可选回归 P2，逐条给依据）
- **前置依赖**：**持久的"用例 ↔ 代码 ↔ 功能"追溯映射**，v0 形态分三层：代码级锚点 = 用例附录「代码证据清单（TC ↔ 文件:行）」，由 Schema 抽取结构化为 `code_refs` 字段（7.4）；功能层 = 需求模型 + Schema 的 module / risk_ref；per-run 增量 = 改动文件映射附录（针对某次 diff 生成，只作增量补充）。三层全部来自落盘产物，不依赖会话记忆。没有这个数据结构，影响面分析就只是"让模型读一遍 diff 猜"——这是本 Skill 列入 Phase 3 而非更早的原因（依赖 Phase 2 的 Schema 落地）

---

## 9. 能力迁移矩阵

> v1 两个 Skill 的既有能力逐一裁决归属，消除"继续保留"与"新 Skill 职责"的矛盾。tcw = `test-case-writing`，e2e = `automated-e2e-testing`。

| # | 现有能力 | 现归属 | v2 归属 | 迁移后原 Skill 保留什么 |
|---|---------|--------|---------|------------------------|
| 1 | 输入研读、范围界定 | tcw 阶段一 | tcw 保留内联轻量版（够用即可）；系统性需求建模 → `requirement-analysis` | 轻量输入研读；深度建模消费 `需求模型.md` |
| 2 | 需求澄清 | tcw 阶段二 | tcw 保留（写用例前必须澄清）；澄清记录格式统一到需求模型的 `open_questions` | 保留 |
| 3 | 代码探索与审查、Cx 缺陷记录 | tcw 代码模式 | tcw 保留"审查发现 → Cx 记录"产出规范；已确认 Bug 的根因 / 影响分析 → `bug-analysis` | 保留审查与记录；根因分析移交 |
| 4 | 覆盖度审查（4A/4B） | tcw 阶段四 | tcw 保留**写时自审**（质控）；对存量 / 他人用例的独立审查 → `test-case-review` | 保留自审 |
| 5 | 增量更新 | tcw | tcw 保留用例文件增量修改；diff → 影响面分析 → 回归范围 → `regression-testing` | 保留修改动作与变更报告 |
| 6 | 业务熟悉（工作流零） | e2e | e2e 保留"为写自动化踩点"的小规模探索；独立探索会话 → `exploratory-testing` | 保留踩点 |
| 7 | Bug 记录（工作流二） | e2e | e2e 保留证据收集与报告条目；根因 / 影响分析 → `bug-analysis` | 保留记录 |
| 8 | 测试报告 | e2e（`测试报告_{来源}.md`） | 格式统一到 `core/report-template.md`；流水线收尾汇总由 `qa` 完成 | 保留执行报告，格式对齐模板 |
| 9 | "纯 API → Python 脚本"指引 | e2e When NOT to Use | 改为指向 `api-testing` | — |

**同步改写清单**（新 Skill 上线时必须一起做，否则触发边界失效）：

- tcw：description 收窄（不再宣称覆盖深度需求建模与外部审查）
- e2e：description 收窄（探索性测试表述收窄；API 指引改指向 `api-testing`）
- 每个新 Skill：SKILL.md 必须含 When NOT to Use（见 6.2）

---

## 10. 三层架构规范（L1 / L2 / L3）

> 本章直接回应 [1.3 问题一](#13-设计动机v2-要解决的两个真实问题)：**一个 Skill 不应同时承担"知识库 + 工作流 + 规则引擎 + 输出模板 + QA 方法论"**。规则越多不等于 Agent 越强——超出 Agent 有效遵循能力的规则只是噪音，还会稀释真正重要的约束。

### 10.1 职责分离

```text
L1 — SKILL.md 头部 ：触发与边界（什么时候用 / 什么时候不用、输入、输出）
L2 — SKILL.md 正文 ：工作流步骤（每次触发都需要的主干，保留在 SKILL.md 内）
L3 — references/   ：方法 / 规则 / Checklist / 模板 / 框架知识（按需加载）
     core/         ：跨 Skill 方法论（风险模型 / 证据体系 / 测试原则，多 Skill 共享）
```

**SKILL.md 里只允许两类内容**：触发边界（L1）和工作流（L2）。其余一切——方法知识、Checklist、输出模板、QA 方法论——要么外移到本 Skill 的 references/，要么沉淀到 core/。

### 10.2 硬规则

1. **SKILL.md ≤ 500 行（红线，触线即拆）**：外部实践（Red Hat ACE 团队，2026-07）明确指出 L2 指令超过 500 行后性能开始退化——这不是风格建议，是性能阈值
2. **每次触发都需要的才进 SKILL.md**：只在特定分支需要的内容一律外移按需加载（gate everything）——不受控的 L3 引用是最大的 token 消耗项
3. **外移红线**：硬约束外移后仍必须在 SKILL.md 的工作流步骤中被显式引用（"此步执行 `../core/coverage.md` 全部检查项"），不得降级为"可选参考"
4. **宁窄而深，不做全能**："试图覆盖整个领域的全能型 Skill 往往使性能退化"——单 Skill 职责收窄，跨阶段协作交给编排层（第 5 章），而不是把整个流程塞进一个 Skill
5. 原则：**不要为了完整而把所有知识加载进 Agent——需要什么，再加载什么**

> 外部参考：[Building Skills for AI Agents: Pitfalls and Best Practices（Red Hat，2026-07）](https://next.redhat.com/2026/07/28/building-skills-for-ai-agents-pitfalls-and-best-practices/)。其"轻量路由 Skill""L1 负向约束（明确何时不适用）""Eval 作为 Skill 迭代的质量门"等建议，与本框架的 `qa` 编排（5.2）、触发 / 反触发表（6.2）、黄金集质量门（12.4）相互印证。其 SkillOpt 工具（自动压缩 L2 指令，报告 90.4% 体积削减而不损质量）可在 Phase 1 拆分时先行尝试，再手工精修。

---

## 11. QA Agent 完整工作流

```text
用户："帮我测试这个需求"
        ↓
qa（编排：意图识别，端到端 → 启动流水线）
        ↓
requirement-analysis ──→ 需求模型.md（含澄清记录）   ⏸ 澄清检查点（等待用户裁决）
        ↓
test-strategy ─────────→ 测试策略.md（含 Risk Map）
        ↓
test-case-writing ─────→ 测试用例_markmap.md + Test Case Schema
        ↓
test-case-review ──────→ 修订用例 + 审查记录
        ↓
执行策略裁决           ⏸（用户确认测试策略中 automation_plan 的提案：手动 / e2e / api）
        ↓
执行 ─────────────────→ 运行结果 + Bug 证据（E3）
        ↓
bug-analysis ─────────→ 根因 / 影响范围 / 回归用例建议   ⏸ Bug 定性检查点
        ↓
regression-testing ───→ 回归清单_{日期}.md
        ↓
qa 收尾 ───────────────→ 测试报告_{日期}.md
```

⏸ 为人工检查点（见 14.2）；所有箭头上的文件即流水线状态，会话中断后凭文件续跑（各阶段在独立上下文中运行，见 5.4）。

旁路：文档缺失 / 系统陌生时，`exploratory-testing` 在 requirement-analysis 之前先行，探索产出（系统理解 + 风险清单）作为需求建模的输入。

---

## 12. Eval 体系与 Benchmark

### 12.1 目标

回答：

> **"用了 Skill 后，Agent 的测试能力到底提升了多少？"**

而不是"这个 Skill 看起来好不好"。

### 12.2 指标体系

**用例质量（Executability / Coverage / Quality / Efficiency / Bug Finding）**：

```text
Executability ：零上下文执行成功率 / 首步受阻率 / 前置可得率   ← 一级指标，标准见 7.6
Coverage      ：Functional / Boundary / Exception / Permission / State / Regression
Quality       ：Correctness / Relevance / Specificity / Completeness
Efficiency    ：Redundant Cases / Invalid Cases / Token Usage / Execution Time
Bug Finding   ：Bug Detection Rate / Critical Bug Detection Rate / False Positive Rate
```

> **Executability 是一票否决指标**（直接回应 [1.3 问题二](#13-设计动机v2-要解决的两个真实问题)）：不可执行的用例，覆盖再全也计零分。评估方式见 12.3 ②。

**自动化（E2E / API）**：

```text
Test Generation Success Rate / Compilation Success Rate / Execution Success Rate
Assertion Accuracy / Selector Stability / Bug Detection Rate
```

### 12.3 方法学

Eval 是工程项目，四个硬问题各有明确答案后才算设计完成：

**① Ground Truth 从哪来（coverage 分母问题）**

- 黄金集每个任务由**人工**产出"全部可测点清单"并交叉复核——这是 Coverage 百分比的唯一合法分母
- 没有人工分母的覆盖率是 Agent 给自己批改作业，不进指标
- Bug 检测类任务标注已知 Bug 清单：以真实历史 Bug 为主，可控补充注入式 Bug（mutation 式）填补分布空缺

**② Evaluator 是谁**

- 客观指标自动判：编译 / 执行通过率、断言有效性（可执行验证）、选择器稳定性（固定环境重跑存活率）
- 主观质量（用例写得好不好）用 LLM-as-judge：多次采样取一致值 + **人工抽检约 20% 校准**；judge prompt 与评分 rubric 纳入版本管理
- **可执行性通过模拟执行评估**：评审者（人工，或 LLM judge 配合被测环境 / 代码）按用例逐步走一遍，记录卡点（首步受阻 / 前置不可得 / 判定不可操作 / 断言超强度），逐条归因到 7.6 的失败模式分类

**③ 环境固定**

- 被测应用容器化、版本锁定；每个 E2E 任务附带环境说明（compose / 启动脚本）
- 环境漂移的运行作废重跑，不进指标

**④ 数据合规**

- 真实 PRD / 代码 / Bug 入集前**脱敏 + 授权确认**；内部集与可公开集物理分离
- "真实数据构成壁垒"与"对外发布 Benchmark"之间的合规张力，在扩容前解决，不在发布前才解决

### 12.4 黄金集与 Benchmark 的关系

**Phase 1 就建黄金集 v0（10–20 个真实任务，人工标注）**，它同时承担两个角色：

1. Phase 1–4 迭代期间的**质量门**：每次改 Skill 跑一遍黄金集，指标回退或 token 成本异常上涨则拦截合入——Skill 也需要 CI。配套版本纪律：Skill 改动走 PR + 版本号、可回滚，质量门作为合入检查
2. **Phase 5 Benchmark 的种子**：同一套 harness 直接扩容，不建两次

> 把 Eval 留到最后 = 前 4 个 Phase 全凭感觉迭代，这是本规划明确避免的路径。

### 12.5 Skill On / Off 对比（示意）

> **下表为示意数据（illustrative），非实测结果**，用于说明最终呈现形态。

```text
                      Without Skill    With Skill
Code Compile              72%              96%
Test Pass                 61%              89%
Valid Assertion           54%              91%
Bug Detection             38%              67%
```

对比条件：同任务集、同模型、同 harness、多样本；差异报告附置信区间。

---

## 13. 开发优先级

> 纪律：不一次做完所有 Skill。每个 Phase 有明确依赖关系与同步改写动作。

### Phase 1：完善存量与度量基础

```text
test-case-writing / automated-e2e-testing（存量）
```

重点：

- **Risk Model 落地**（`core/risk-model.md`，tcw 接入）
- **Evidence 体系落地**（`core/evidence.md`，tcw 的 Cx/Dn 记录对齐标注格式）
- **可执行性标准落地**（`core/executability.md`，随 Skill 拆分从 tcw 现有硬约束外移升格；12.2 的一票否决指标依赖此文件）
- **Test Case Schema 定义**（含存量 markmap 抽取规则）
- **Eval 黄金集 v0**：10–20 个真实任务 + 人工标注 + harness（Benchmark 种子；标注含 Executability 维度——每个任务人工标注"可执行用例"的判定基准）。成本预期：每任务全量可测点清单 + 判定基准约需 4–8 小时专家时间，10–20 任务合计约 2–4 人周，排期时预留
- **Skill 拆分**：tcw（436 行，逼近 500 行红线）与 e2e 的非工作流内容外移 references（清单见 6.1），SKILL.md 收敛为"触发边界 + 工作流"——直接回应 1.3 问题一

### Phase 2：设计中枢 + 编排入口

新增：

```text
qa（薄编排：串联 需求 → 策略 → 用例 → 审查）
requirement-analysis
test-strategy
test-case-review
```

依赖：Phase 1 的 Schema 与 Risk Model。同步执行迁移矩阵 #1、#4 的改写。

### Phase 3：执行闭环

新增：

```text
api-testing
exploratory-testing
regression-testing
```

依赖：追溯映射随 Schema 与落盘产物沉淀（见 8.10）。同步执行迁移矩阵 #5、#6、#9 的改写。

### Phase 4：缺陷闭环

新增：

```text
bug-analysis
```

测试报告以模板形态在 `qa` 收尾生效（**不再作为独立 Skill**）。同步执行迁移矩阵 #3、#7、#8 的改写。

### Phase 5：Benchmark 扩容

- 复用 Phase 1 harness，扩任务集（含注入式 Bug 任务）
- 跑 Skill On / Off 对比，产出量化报告（如 12.5 形态，附真实数据与置信区间）

---

## 14. 最终产品形态

### 14.1 用户视角

最终用户面对的不是 `/test-case-writing`、`/automated-e2e-testing` 的命令选择，而是：

> **"帮我测试这个需求。"**

Agent 按 [第 11 章](#11-qa-agent-完整工作流) 流水线完成：理解需求 → 分析代码 → 识别风险 → 制定策略 → 生成用例 → 审查覆盖 → 选择执行方式 → 执行 → 发现 Bug → 分析根因 → 生成回归清单 → 输出测试报告。

### 14.2 用户必须提供 / 裁决的（诚实清单）

端到端自动化不等于零人工输入。以下环节需要用户，产物中对应位置留 TODO 指明"找谁拿什么"（沿用现有导读区环境表机制）：

| 环节 | 用户输入 |
|------|---------|
| 启动 | 需求、代码仓库、测试环境与账号（或指路：向谁索取） |
| 澄清检查点 | 意图裁决（模糊 / 矛盾项的最终答复，见 3.2） |
| 执行策略 | 手动 / 自动化、用哪个执行框架 |
| Bug 定性 | 预期行为 vs 缺陷的裁决 |

---

## 15. 项目核心竞争力

不以"我们有多少个 Skill"为竞争力，而是四个能力：

```text
① Code-aware        理解真实代码，而不是只读 PRD
② Risk-driven       围绕风险设计测试，而不是机械生成用例
③ Evidence-driven   所有结论有证据支撑（E0–E4 + 裁决规则）
④ Evaluated         所有 Skill 有 Benchmark 与量化指标

        四者叠加 → QA Agent（方法论 + Skills + Benchmark）
```

配套的长期壁垒是 **QA-Skills-Bench**：真实 PRD / 代码 / Bug / 用例 / 测试结果 / Git Diff 构成的任务集（经 12.3 ④ 的脱敏与授权），评估 Requirement Understanding / Test Strategy / Coverage / Bug Discovery / Automation Success / Regression Accuracy。

---

## 16. 实施建议

项目已完成第一阶段（0 → 1：能写用例、能跑 E2E）。下一阶段**不是继续加 Prompt 和规则**，而是按以下依赖链补基础设施：

```text
当前：test-case-writing + automated-e2e-testing
        ↓
Risk Model + Evidence 体系 + 统一 Test Case Schema（core/ 与 Phase 1，Phase 2 的前置）
        ↓
Test Strategy + Test Review（Phase 2 新增 Skill）
        ↓
qa 编排入口 + 落盘流水线 + 会话隔离（Phase 2）
        ↓
Bug / Regression / 追溯映射（Phase 3–4）
        ↓
Eval 黄金集（Phase 1 起步）→ Benchmark 扩容（Phase 5）
        ↓
QA Agent
```

**最值得优先投入的六项**：

1. **Risk Model**（评级有证据、与优先级脱钩）
2. **Test Strategy**（风险 → 策略 → 用例的推导链）
3. **Test Review**（独立审查，AI 不仅会写还会审）
4. **统一 Test Case Schema**（Skill 间的流转接口，双轨制）
5. **Evidence 机制**（E0–E4 + 三类裁决规则，压幻觉）
6. **Eval / QA-Skills-Bench**（黄金集 Phase 1 起步，量化 Skill On / Off）

这六项加编排入口完成后，QA Skills 不再是几个"测试 Prompt"，而是一套完整的 **Agentic QA 方法论 + Skills + Benchmark**。
