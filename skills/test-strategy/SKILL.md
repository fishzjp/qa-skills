---
name: test-strategy
slug: test-strategy
displayName: 测试策略
version: 0.6.0
description: 回答"这个功能应该怎么测"时使用——风险评级挂证据（Risk Map），翻译成功能域+类型域两域范围与深度：类型域十轴全轴必答（脚本扫描信号+预填修订），include挂信号、exclude挂理由、full有预算上限。不用于：已有策略直接写用例（test-case-writing）、需求建模（requirement-analysis）、端到端流水线（qa）。
---

# 测试策略（test-strategy）

回答"**这个功能应该怎么测**"——把风险翻译成**两域测试范围与深度**。策略位于"需求 → 风险分析 → **策略** → 测试设计 → 用例"链路中，跳过策略直接写用例是本框架明确反对的。

- **输入**：需求模型（`需求模型.md`；没有则内联轻量研读需求源）、代码仓库、系统架构、历史 Bug
- **输出（落盘）**：`{项目}/测试策略.md`（Risk Map + 两域 scope + depth_budget）；有 handoff / blocked / 外部执行器轴时另产 `{项目}/专项移交_{轴}_{日期}.yaml`
- **边界**：不写具体用例（→ `test-case-writing`）；不代替用户裁决（自动化提案、预算裁决均 ⏸ 等确认）；覆盖范围限于**系统级黑盒**（UI / API / 手动 / 专项移交）——单元/集成测试是开发侧职责，本策略的风险评级与"已覆盖"结论均以**该层已有保障为假设前提**（假设未验证时在测试报告标注，防"系统级全过 = 质量有保障"的误读）

## When to Use

- "这个功能应该怎么测"——需要范围 / 类型 / 深度 / 优先级的策略决策与理由
- 需要识别风险并评级（Risk Map），作为用例优先级与回归锚点的依据
- 需要决定测试类型取舍（性能 / 安全 / 可靠 / 兼容等哪些测、测多深、哪些明确不测）并留痕
- 需要制定自动化计划提案与长期回归策略

## When NOT to Use

- 端到端测试整个需求 → `qa` 编排
- 需要系统性需求建模 → `requirement-analysis`
- 已有策略、直接写用例 → `test-case-writing`
- 代码变更后判断回归范围 → `regression-testing`（本 skill 的 regression_plan 是长期回归策略，不是某次 diff 的范围选择）

## 测试策略 Schema（产出结构）

```yaml
test_strategy:
  feature:
  functional_scope:            # 功能域：范围+深度+理由（新增 state / data_consistency 两轴）
    functional:        { include: true, depth: full,     rationale: "核心资损路径", risk_refs: [R3] }
    boundary:          { include: true, depth: standard }
    permission:        { include: true, depth: full,     rationale: "越权高危", risk_refs: [R2] }
    state:             { include: true, depth: standard }
    data_consistency:  { include: true, depth: standard }
    regression:        { include: true, depth: standard }
  type_scope:                  # 类型域：十轴全轴必答，每轴单行 flow 风格（校验器按行解析）
    performance:        { decision: include, depth: full,     signals: ["PRD-4.2 SLA", "order_service.go:88"], risk_refs: [R3], executor: k6, execution_status: blocked, todo: "向运维索取独立压测环境", handoff_ref: "专项移交_performance_{日期}.yaml" }
    security_business:  { decision: include, depth: standard, signals: ["多角色", "内部信号:permission≥standard"] }
    reliability:        { decision: include, depth: standard, signals: ["retry: pay_service.go:41"] }
    concurrency:        { decision: include, depth: standard, signals: ["库存扣减", "S级复核: check-then-write 命中 cart_service.go:41"] }
    compatibility:      { decision: include, depth: light,    signals: ["有前端"] }
    accessibility:      { decision: include, depth: light,    signals: ["有前端"] }
    visual:             { decision: include, depth: light,    signals: ["有前端"] }
    i18n:               { decision: exclude,  rationale: "需求信号（海外/多语言/RTL）未命中；无代码仓库", scanned: ["需求信号(G)"] }
    migration:          { decision: include, depth: standard, signals: ["migrations/2026-08-x.sql"] }
    contract_integration: { decision: include, depth: standard, signals: ["外部风控依赖"] }
  depth_budget:                # full ≤3（两域合并计）；被裁 Critical 轴走预算裁决
    full_axes: [functional, permission, performance]
    ranking_rationale: "R3(资损 Critical) > R2(越权 High) > ..."
  automation_plan:            # 哪些用例自动化、用什么框架（提案，⏸ 等用户确认）
  regression_plan:            # 回归策略（锚点用例、回归节奏）
  risk_map_ref:               # 指向 Risk Map（本文档内嵌，每条风险含证据）
```

字段口径：`signals` 引用需求章节 / `文件:行` / 矩阵内部信号；`scanned` 为 exclude 的 G+S 双清单（项尾标 (G)/(S)）；`executor` 缺省视为 agent，非 agent（k6 / locust 等）必须带 `handoff_ref`；`execution_status` ∈ ready / blocked / done，exclude 轴省略。深度档位**只取三值**：full（逐格全覆盖）/ standard（主干+重点异常）/ light（抽样+冒烟）——"不测"不是深度而是范围决策：功能域写 `include: false`（挂 rationale），类型域写 `decision: exclude` 或 `handoff`，均须挂理由（校验器会拒绝 depth 里出现其他值）。

> **格式硬约束（弱模型格式锤，2026-08-23 R1）**：type_scope **每轴必须写成一行** flow 风格，形如 `performance: { decision: include, depth: standard, signals: ["..."] }`——**禁止**把一个轴拆成 decision / depth / signals 多行块式（校验器按行解析，块式 = 校验失败 = 该轴视同未决策）。写之前先照抄上一行的形状。依据：首轮最弱模型实测 47% 样本块式漂移致解析失败，决策内容本身无恙——纯格式损耗。

## 工作流

### 1. 输入研读

- 读需求模型（无则读原始需求源做轻量研读）；有代码 → 索取仓库（路径/分支/diff），确认实现形态（有无 UI、接口面、数据流）
- 收集历史 Bug（同功能区/同模块），历史缺陷密度是 Likelihood 的估计输入与升降档 R3 的触发输入

### 2. 风险识别与评级（此时加载 `../core/risk-model.md`）

- 按**维度**扫风险：功能域维度（权限 / 数据一致性 / 边界 / 状态流转 / 资损——五维与第 3 步 scope 六轴的对应关系见 `../core/risk-model.md` 的 dimension 注释）+ 类型域轴名（并发 / 可靠 / 安全 / 性能 / 兼容 / 迁移 / 契约——与矩阵轴同源）
- 每条风险（R1、R2…）按模型评级：**Impact × Likelihood（各 1–5）→ Critical/High/Medium/Low**，每条强制带 evidence——**没有证据的风险评级视为无效评级**
- 方法选择参考 `../core/testing-principles.md` 第 2 节（按功能特征选设计方法，决定功能域各轴的深度理由）

### 3. 功能域范围决策

逐轴决定 include / depth / rationale（functional / boundary / permission / state / data_consistency / regression）：

- 风险等级 → 用例优先级映射按 `../core/risk-model.md` 第 3 节执行（Critical 必有 P0 且为回归锚点……），偏离显式说明理由
- **不测的也要写理由**——"为什么不测"与"为什么测"同等重要
- permission 高深度（≥standard）同时是轴 2 业务安全的内部纳入信号（裁决见矩阵第 2 节）

### 4. 类型域全轴扫描（此时**按组加载** `../core/test-type-matrix.md` 对应小节）

**分轴组推进**（A 资金与正确性 → B 依赖与变更 → C 前端体验；每组只加载矩阵中本组轴的小节，不整文件加载）：

1. **G 级扫描**（有代码仓库时，开工跑一次三组共用）：`python3 ../core/scripts/scan_signals.py <仓库路径>` → 每轴 G 级信号 + 预填表
2. **逐轴决策（受限选择，从预填表修订，不空白生成）**：需求信号 → G 级核对 → **S 级照单复核**（矩阵各轴标〔S〕的项逐项读代码确认）→ decision → depth
3. **防橡皮图章**：exclude 永不预填——exclude 必须完成 S 级复核并把 G+S 双清单写进 `scanned`；"脚本无命中"单独不构成 exclude 理由
4. **组内交付核对**：本组全轴有决策再进下一组；十轴完成进入第 5 步

无代码仓库：跳过 G/S 级，仅需求信号决策；exclude 的 rationale 注明"无代码仓库"（校验器按此豁免 S 级要求）。

### 5. 深度校准与预算排序（此时执行矩阵第 13 节 R1–R6）

- 升降档按 R1–R6（风险升档 / 双源信号 / 历史缺陷 / 无信号降档 / 成本门 / 预算约束）
- **R6 > R1**：full（两域合并）> 3 时按风险排序裁剪；被裁剪的 Critical 轴触发 **⏸ 预算裁决检查点**——呈现排序与裁剪影响，用户可扩预算（扩预算时 depth_budget 记 `budget_review: {approved_by: 用户}`）
- **depth 与 execution_status 分离**：环境 / 数据 / 工具缺位 → depth 不降，记 `blocked` + `todo`（向谁索取什么）——"做不了"不得冒充"不用测"

### 6. 自动化计划提案（⏸ 提案，不裁决）

- 按用例特征提案：有 UI 主流程 → Playwright（`automated-e2e-testing`）；接口级校验/幂等/并发 → API 脚本（`api-testing`）；脚本型轴的执行物（性能/视觉、无障碍的 axe 扫描任务）→ 专项脚本 / 扫描任务；探索性/一次性 → 手动
- automation_plan 是**提案**：列出建议清单 + 框架 + 不自动化清单 + 理由，交用户确认（qa 流水线中为执行策略检查点）；确认前不启动执行类 skill

### 7. 回归策略

- 从 Critical/High 风险与 P0 用例中指定**回归锚点**（每次必跑）
- regression_plan：锚点集 + 按变更类型的扩展规则（接口变更 → 接口用例全量；UI 变更 → 主流程 E2E……）

### 8. 落盘与交付

1. 写 `{项目}/测试策略.md`（Schema 结构 + Risk Map 内嵌；type_scope 每轴单行 flow 风格 + 足够性声明：逐轴档位动作清单与完成状态；开头一段**范围假设声明**：本策略限于系统级黑盒，单元/集成测试为开发侧职责，结论以此为前提）
2. handoff 轴 / include+外部执行器 / blocked 轴 → 生成 `{项目}/专项移交_{轴}_{日期}.yaml` 移交包（目标、场景参数、阈值/验收口径）
3. **校验后交付**：`python3 ../core/scripts/validate_schema.py {项目}/测试策略.md`（V1–V5；有代码仓库时叠加 `--repo-root {仓库根}` 抽查各轴 signals 指涉真实性），错误清零再交付。注意：include 且挂 Critical 风险的轴若最终维持 full 以下档位，校验器要求该轴名出现在 budget_review 文本中——降档裁量必须留一行依据，不许无声消失
4. 交付索引给下游（`test-case-writing`）：策略路径 + include 轴清单（用例型轴的 type/标签要求见矩阵第 12 节）+ 优先级映射要求

## Common Mistakes

| 错误 | 后果 | 正确做法 |
|------|------|---------|
| 风险评级无证据（拍脑袋 High） | 评级不可复核，策略失去推导链 | 每条风险挂 evidence（`../core/risk-model.md`） |
| 类型轴静默缺失（漏轴） | 类型盲区被藏成"没想过"，无从挑战 | 十轴必答（V1），exclude 也要留痕 |
| include 无信号 / exclude 无理由 | 过测 / 漏测 | signals 挂证据；rationale + scanned 双清单（V2/V3） |
| 脚本无命中直接 exclude | 脚本盲区被制度化为漏测 | S 级复核后才可 exclude（G+S 双确认） |
| full 满天飞 | 资源稀释在长尾，无重点 | full ≤3 + 挂风险编号（V4）；冲突时 R6>R1 + 预算裁决 |
| 环境缺位记成 exclude | "做不了"冒充"不用测" | depth/execution 分离，blocked + todo（R5/V5） |
| scope 只写布尔开关 | "测多深"丢失，执行时各自理解 | 范围 + 深度 + 理由三件套 |
| 把用例写进策略 | 越界（那是 test-case-writing 的产出） | 策略到"范围/深度/优先级要求"为止 |
| automation_plan 直接执行不等确认 | 剥夺用户执行策略裁决权 | 提案 → ⏸ 用户确认 → 才启动执行 |
| 风险等级沿用 P0/P1 命名 | 与用例优先级同名歧义 | 风险用 Critical/High/Medium/Low（`../core/risk-model.md`） |
