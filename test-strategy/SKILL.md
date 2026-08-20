---
name: test-strategy
description: 回答"这个功能应该怎么测"时使用——基于需求模型与代码识别风险（Risk Map：Impact × Likelihood，评级强制挂证据），把风险翻译成测试范围、类型、深度与优先级的策略，含自动化计划提案与回归策略。不用于：已有策略直接写用例（test-case-writing）、需求建模（requirement-analysis）、端到端流水线（qa）。
---

# 测试策略（test-strategy）

回答"**这个功能应该怎么测**"——把风险翻译成测试范围与深度。策略位于"需求 → 风险分析 → **策略** → 测试设计 → 用例"链路中，跳过策略直接写用例是本框架明确反对的。

- **输入**：需求模型（`需求模型.md`；没有则内联轻量研读需求源）、代码仓库、系统架构、历史 Bug
- **输出（落盘）**：`{项目}/测试策略.md`——按下方 Schema 组织，含 Risk Map
- **边界**：不写具体用例（→ `test-case-writing`）；不代替用户做执行策略最终裁决（提案 + 等确认）

## When NOT to Use

- 端到端测试整个需求 → `qa` 编排
- 需要系统性需求建模 → `requirement-analysis`
- 已有策略、直接写用例 → `test-case-writing`
- 代码变更后判断回归范围 → `regression-testing`（本 skill 的 regression_plan 是长期回归策略，不是某次 diff 的范围选择）

## 测试策略 Schema（产出结构）

```yaml
test_strategy:
  feature:                    # 被测功能
  scope:
    functional:    { include: true,  depth: full,     rationale: "核心资损路径" }
    boundary:      { include: true,  depth: standard }
    permission:    { include: true,  depth: full,     rationale: "R2 权限风险 High" }
    regression:    { include: true,  depth: standard }
    compatibility: { include: true,  depth: light }
    performance:   { include: false, handoff: "专项：k6" }
    security:      { include: false, handoff: "专项：安全审计" }
  automation_plan:            # 哪些用例自动化、用什么框架（提案，⏸ 等用户确认）
  regression_plan:            # 回归策略（锚点用例、回归节奏）
  risk_map_ref:               # 指向 Risk Map（本文档内嵌，每条风险含证据）
```

> 策略粒度是**范围 + 深度 + 理由**（为什么测 / 测多深 / 为什么不测），不是布尔开关；每项纳入理由应能追溯到 Risk Map 中的风险编号。性能 / 安全**不在本框架自研范围**，用 `handoff` 标注移交专业工具（k6 / locust、安全审计），报告预留入口。

## 工作流

### 1. 输入研读

- 读需求模型（无则读原始需求源做轻量研读）；有代码 → 索取仓库（路径/分支/diff），确认实现形态（有无 UI、接口面、数据流）
- 收集历史 Bug（同功能区/同模块），历史缺陷密度是 Likelihood 的估计输入

### 2. 风险识别与评级（此时加载 `../core/risk-model.md`）

- 按**维度**扫风险：权限 / 数据一致性 / 边界 / 状态流转 / 并发 / 兼容性 / 资损 / 安全 / 性能
- 每条风险（R1、R2…）按模型评级：**Impact × Likelihood（各 1–5）→ Critical/High/Medium/Low**，每条强制带 evidence（level + source）与 confidence——**没有证据的风险评级视为无效评级**
- 方法选择参考 `../core/testing-principles.md` 第 2 节（按功能特征选设计方法，决定 scope 各维度的深度理由）

### 3. 范围决策（风险 → 策略翻译）

逐维度决定 include / depth / rationale：

- **深度档位**：full（逐条规则/逐条边全覆盖）/ standard（主干 + 重点异常）/ light（抽样 + 冒烟）/ exclude（handoff 或显式不测 + 理由）
- 风险等级 → 用例优先级映射按 `../core/risk-model.md` 第 3 节执行（Critical 必有 P0 且为回归锚点……），偏离显式说明理由
- **不测的也要写理由**——"为什么不测"与"为什么测"同等重要

### 4. 自动化计划提案（⏸ 提案，不裁决）

- 按用例特征提案：有 UI 主流程 → Playwright（`automated-e2e-testing`）；接口级校验/幂等/并发 → API 脚本（`api-testing`）；探索性/一次性 → 手动；无 UI 后端 → 协作执行
- automation_plan 是**提案**：列出"建议自动化清单 + 框架 + 不自动化清单 + 理由"，交用户确认（qa 流水线中为执行策略检查点）
- 提案确认前不启动执行类 skill

### 5. 回归策略

- 从 Critical/High 风险与 P0 用例中指定**回归锚点**（每次必跑）
- regression_plan：锚点集 + 按变更类型的扩展规则（接口变更 → 接口用例全量；UI 变更 → 主流程 E2E……）

### 6. 落盘与交付

写 `{项目}/测试策略.md`（Schema 结构 + Risk Map 内嵌）；交付时给下游（`test-case-writing`）一句话索引：策略路径 + 必测维度 + 优先级映射要求。

## Common Mistakes

| 错误 | 后果 | 正确做法 |
|------|------|---------|
| 风险评级无证据（拍脑袋 High） | 评级不可复核，策略失去推导链 | 每条风险挂 evidence（`../core/risk-model.md`） |
| scope 只写布尔开关 | "测多深"丢失，执行时各自理解 | 范围 + 深度 + 理由三件套 |
| 性能/安全维度静默缺失 | 范围不可见，被误以为已覆盖 | include: false + handoff 显式标注 |
| 把用例写进策略 | 越界（那是 test-case-writing 的产出） | 策略到"范围/深度/优先级要求"为止 |
| automation_plan 直接执行不等确认 | 剥夺用户执行策略裁决权 | 提案 → ⏸ 用户确认 → 才启动执行 |
| 风险等级沿用 P0/P1 命名 | 与用例优先级同名歧义 | 风险用 Critical/High/Medium/Low（`../core/risk-model.md`） |
