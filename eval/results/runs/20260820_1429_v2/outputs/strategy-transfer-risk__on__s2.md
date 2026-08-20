# 余额转账 · 测试策略

## 1. 功能概述

| 项 | 内容 |
|---|------|
| 被测功能 | 站内用户间余额转账，实时到账 |
| 角色 | 普通用户（发起/收款）、风控（大额与异常拦截） |
| 核心规则 | 单笔 ≤ 5000 元；日累计 ≤ 20000 元；余额不足拦截；金额保留 2 位小数；大额（≥ 2000 元）触发风控审核，审核中资金冻结；备注 ≤ 50 字 |
| 状态流转 | 发起 → 风控审核（大额）/ 直接成功 → 成功 / 失败 |
| 依赖 | 余额服务、风控服务、消息通知 |
| 实现形态 | 后端 `transfer_service.py` 编排（feature/transfer 分支）；三步操作无分布式事务；金额中间计算用 float；无幂等键；日累计读本地缓存（30s 刷新）；风控异步回调超时 10 分钟自动放行；单号时间戳+随机数生成无唯一约束 |

---

## 2. Risk Map

> 评分规则：Risk Score = Impact × Likelihood（各 1–5）；Critical 20–25 / High 10–19 / Medium 4–9 / Low 1–3。
> 每条风险强制带 evidence（level + source）与 confidence；无证据的评级无效。

### R1 — 数据一致性 / 资损：三步转账无分布式事务，补偿回滚可能不完整

```yaml
risk:
  id: R1
  feature: 余额转账
  dimension: 数据一致性
  description: >
    transfer_service.py 编排三步操作（扣发起方余额 → 调风控 → 加收款方余额），
    三步之间无分布式事务，任一步失败靠补偿逻辑回滚。补偿逻辑是否覆盖所有失败场景未知，
    若回滚不完整将导致资金丢失或双花。
  impact: 5                      # 资金丢失 / 双花 = 资损最高级
  likelihood: 3                  # 中间步骤（风控服务、余额服务）失败是常规可触发场景
  level: High                    # 15 = 5 × 3
  evidence:
    level: E2
    source: transfer_service.py（代码走读：三步编排无分布式事务，靠补偿回滚）
  confidence: medium             # 无事务确定；补偿完整性未验证
  status: needs_verification
  priority_requirement: P0 或 P1
```

### R2 — 并发 / 资损：转账无幂等键，网络重试产生重复转账单

```yaml
risk:
  id: R2
  feature: 余额转账
  dimension: 并发
  description: >
    转账请求无幂等键，客户端/网关层网络重试会产生重复转账单，
    导致发起方被重复扣款、收款方被重复加款。
  impact: 5                      # 重复扣款 = 资损
  likelihood: 4                  # 网络重试是常规场景，移动端弱网下极易触发
  level: Critical                # 20 = 5 × 4
  evidence:
    level: E2
    source: transfer_service.py（代码走读：转账请求无幂等键）
  confidence: high
  status: needs_verification
  priority_requirement: 必须有 P0 用例，且作为回归锚点
```

### R3 — 资损 / 合规：日累计校验读本地缓存（30s 刷新），窗口内可超限

```yaml
risk:
  id: R3
  feature: 余额转账
  dimension: 资损
  description: >
    日累计校验从本地缓存读取当日汇总，缓存 30 秒刷新。
    30 秒窗口内连续发起多笔转账可绕过日累计 ≤ 20000 元限额，
    且多实例部署时各实例缓存独立，偏差更大。
  impact: 5                      # 日累计超限 = 资损 + 合规违规
  likelihood: 4                  # 30s 窗口内连续转账是常规可触发路径
  level: Critical                # 20 = 5 × 4
  evidence:
    level: E2
    source: transfer_service.py（代码走读：日累计从本地缓存读取，30 秒刷新）
  confidence: high
  status: needs_verification
  priority_requirement: 必须有 P0 用例，且作为回归锚点
```

### R4 — 边界 / 资损：金额中间计算用 float，精度误差

```yaml
risk:
  id: R4
  feature: 余额转账
  dimension: 边界
  description: >
    金额在中间计算过程使用 float，仅在入库前转 Decimal。
    float 二进制浮点误差在特定金额组合下（如 0.1 + 0.2）会产生精度偏差，
    可能导致余额计算错误、限额校验偏移。
  impact: 4                      # 金额计算误差，单笔误差小但可累积；核心功能降级
  likelihood: 3                  # float 精度问题在特定金额组合下常规可触发
  level: High                    # 12 = 4 × 3
  evidence:
    level: E2
    source: transfer_service.py（代码走读：金额中间计算用 float，入库前转 Decimal）
  confidence: high
  status: needs_verification
  priority_requirement: P0 或 P1
```

### R5 — 状态流转 / 安全：风控回调超时 10 分钟自动放行

```yaml
risk:
  id: R5
  feature: 余额转账
  dimension: 状态流转
  description: >
    大额转账（≥ 2000 元）触发风控异步审核，回调超时 10 分钟后自动放行。
    若风控服务不可用或回调链路异常，异常/大额转账将绕过风控直接到账。
  impact: 5                      # 异常/大额转账绕过风控 = 资损 + 安全
  likelihood: 3                  # 风控服务不可用或回调超时是常规可触发场景
  level: High                    # 15 = 5 × 3
  evidence:
    level: E2
    source: transfer_service.py（代码走读：回调超时 10 分钟自动放行）
  confidence: high
  status: needs_verification
  priority_requirement: P0 或 P1
```

### R6 — 并发 / 资损：余额扣减并发竞争可能导致超扣

```yaml
risk:
  id: R6
  feature: 余额转账
  dimension: 并发
  description: >
    转账先扣发起方余额。若同一用户并发发起多笔转账，
    余额服务的并发控制机制（乐观锁/悲观锁）未知，
    可能出现余额超扣（余额不足但并发窗口内同时通过校验）。
  impact: 5                      # 余额超扣 = 资损
  likelihood: 3                  # 并发转账常规可触发，取决于余额服务并发控制机制
  level: High                    # 15 = 5 × 3
  evidence:
    level: E2
    source: transfer_service.py（代码走读：先扣发起方余额步骤；并发控制机制未知）
  confidence: medium             # 扣款步骤确定；并发控制机制待确认
  status: needs_verification
  priority_requirement: P0 或 P1
```

### R7 — 边界：单笔限额与日累计限额边界校验

```yaml
risk:
  id: R7
  feature: 余额转账
  dimension: 边界
  description: >
    单笔 ≤ 5000 元、日累计 ≤ 20000 元限额的边界值校验。
    需验证恰好等于限额、超出限额 0.01 元等边界行为。
  impact: 3                      # 限额绕过 = 合规问题，部分功能降级
  likelihood: 3                  # 边界值是常规测试路径
  level: Medium                  # 9 = 3 × 3
  evidence:
    level: E1
    source: 需求模型摘要《余额转账》— 规则：单笔 ≤ 5000 元；日累计 ≤ 20000 元
  confidence: high
  status: fact
  priority_requirement: P1
```

### R8 — 边界：转账金额 2 位小数精度处理

```yaml
risk:
  id: R8
  feature: 余额转账
  dimension: 边界
  description: >
    转账金额保留 2 位小数。需验证 3 位小数输入、非法格式、舍入行为。
    与 R4（float 精度）叠加可能放大误差。
  impact: 3                      # 精度处理不当导致金额异常
  likelihood: 2                  # 需特定输入（如 3 位小数）触发
  level: Medium                  # 6 = 3 × 2
  evidence:
    level: E1
    source: 需求模型摘要《余额转账》— 规则：转账金额保留 2 位小数
  confidence: medium
  status: needs_verification
  priority_requirement: P1
```

### R9 — 边界：转账备注 ≤ 50 字

```yaml
risk:
  id: R9
  feature: 余额转账
  dimension: 边界
  description: 转账备注长度 ≤ 50 字的边界校验。
  impact: 2                      # 体验问题
  likelihood: 2
  level: Medium                  # 4 = 2 × 2
  evidence:
    level: E1
    source: 需求模型摘要《余额转账》— 规则：转账备注 ≤ 50 字
  confidence: high
  status: fact
  priority_requirement: P1
```

### R10 — 权限：账户隔离与越权防护

```yaml
risk:
  id: R10
  feature: 余额转账
  dimension: 权限
  description: >
    用户只能操作本人账户发起转账。需验证伪造发起方 ID、
    篡改收款方 ID 等越权场景。
  impact: 4                      # 越权操作他人资金 = 安全 + 资损
  likelihood: 2                  # 需构造特定请求
  level: Medium                  # 8 = 4 × 2
  evidence:
    level: E1
    source: 需求模型摘要《余额转账》— 角色：普通用户（发起/收款）
  confidence: medium
  status: needs_verification
  priority_requirement: P1
```

### R11 — 数据一致性：转账单号无唯一约束

```yaml
risk:
  id: R11
  feature: 余额转账
  dimension: 数据一致性
  description: >
    转账单号在应用层用"时间戳+随机数"生成，无数据库唯一约束。
    高并发下可能产生重复单号，导致数据混乱或重复处理。
  impact: 4                      # 单号冲突导致数据混乱/重复处理
  likelihood: 2                  # 高并发时时间戳+随机数可能冲突，概率取决于随机数范围
  level: Medium                  # 8 = 4 × 2
  evidence:
    level: E2
    source: transfer_service.py（代码走读：单号用时间戳+随机数生成，无唯一约束）
  confidence: medium             # 生成逻辑确定；冲突概率取决于随机数位数（待澄清）
  status: needs_verification
  priority_requirement: P1
```

### R12 — 状态流转：转账单状态流转完整性

```yaml
risk:
  id: R12
  feature: 余额转账
  dimension: 状态流转
  description: >
    转账单状态：发起 → 风控审核（大额）/ 直接成功 → 成功 / 失败。
    需验证每条合法状态边及非法转换拦截（如审核中直接跳成功、
    失败后再次发起等）。
  impact: 3                      # 非法状态转换导致功能异常
  likelihood: 2                  # 需特定操作序列触发
  level: Medium                  # 6 = 3 × 2
  evidence:
    level: E1
    source: 需求模型摘要《余额转账》— 状态：发起 → 风控审核（大额）/ 直接成功 → 成功 / 失败
  confidence: high
  status: fact
  priority_requirement: P1
```

### Risk Map 汇总

| ID | 维度 | Impact × Likelihood | Score | Level | 置信度 | 证据等级 |
|----|------|:---:|:---:|------|--------|---------|
| R2 | 并发 | 5 × 4 | 20 | **Critical** | high | E2 |
| R3 | 资损 | 5 × 4 | 20 | **Critical** | high | E2 |
| R1 | 数据一致性 | 5 × 3 | 15 | **High** | medium | E2 |
| R5 | 状态流转 | 5 × 3 | 15 | **High** | high | E2 |
| R6 | 并发 | 5 × 3 | 15 | **High** | medium | E2 |
| R4 | 边界 | 4 × 3 | 12 | **High** | high | E2 |
| R7 | 边界 | 3 × 3 | 9 | Medium | high | E1 |
| R10 | 权限 | 4 × 2 | 8 | Medium | medium | E1 |
| R11 | 数据一致性 | 4 × 2 | 8 | Medium | medium | E2 |
| R8 | 边界 | 3 × 2 | 6 | Medium | medium | E1 |
| R12 | 状态流转 | 3 × 2 | 6 | Medium | high | E1 |
| R9 | 边界 | 2 × 2 | 4 | Medium | high | E1 |

---

## 3. 测试范围（Scope）

```yaml
test_strategy:
  feature: 余额转账

  scope:
    functional:
      include: true
      depth: full
      rationale: >
        核心资损路径。R1(High) 补偿回滚、R2(Critical) 幂等性、R5(High) 风控放行、
        R6(High) 并发扣减均指向转账核心链路资金安全，需逐条规则全覆盖。
        设计方法：Workflow（端到端主链 + 每环节失败分支 + 中断恢复）。
      risks: [R1, R2, R5, R6]

    boundary:
      include: true
      depth: full
      rationale: >
        R3(Critical) 日累计缓存延迟本质是限额边界绕过；R4(High) float 精度误差；
        R7(Medium) 单笔/日累计限额边界；R8(Medium) 小数位精度；R9(Medium) 备注长度。
        资损相关边界需逐条全覆盖。设计方法：等价类划分 + 边界值分析。
      risks: [R3, R4, R7, R8, R9]

    concurrency:
      include: true
      depth: full
      rationale: >
        R2(Critical) 无幂等键重复转账、R3(Critical) 缓存窗口并发超限、
        R6(High) 余额并发竞争——并发是本功能资损高发区，需全覆盖。
        包含：同账户并发扣减、重复请求幂等性、多实例缓存一致性。
      risks: [R2, R3, R6]

    state_transition:
      include: true
      depth: full
      rationale: >
        R5(High) 风控超时放行涉及异步状态跳转；R12(Medium) 状态流转完整性。
        大额风控路径状态跳转需逐条边覆盖 + 非法转换拦截。
        设计方法：State Machine（状态 → 事件 → 新状态，每条边一个用例，非法转换配拦截）。
      risks: [R5, R12]

    permission:
      include: true
      depth: standard
      rationale: >
        R10(Medium) 账户隔离与越权风险 Medium 级别。
        主干 + 重点异常：伪造发起方 ID、篡改收款方 ID、跨账户操作。
        设计方法：Role × Action × Resource 矩阵逐格核对。
      risks: [R10]

    regression:
      include: true
      depth: standard
      rationale: >
        无历史 Bug 数据（待澄清），但核心资损路径（R1/R2/R3/R5/R6）需回归保障。
        锚点集 + 按变更类型扩展规则（见回归策略）。
      risks: [R1, R2, R3, R4, R5, R6]

    compatibility:
      include: true
      depth: light
      rationale: >
        需求未提及多端适配要求（待澄清是否有 UI）。轻量冒烟：接口兼容性 + 多实例部署行为。
      risks: []

    performance:
      include: false
      handoff: "专项：k6"
      rationale: >
        性能不在本框架自研范围。但 R3(缓存延迟) 与 R6(并发竞争) 有性能属性，
        需 k6 专项压测验证：高并发下余额竞争行为、多实例缓存一致性、
        风控回调链路在高负载下的超时行为。本策略预留性能测试入口。

    security:
      include: false
      handoff: "专项：安全审计"
      rationale: >
        安全不在本框架自研范围。但 R5(风控绕过) 与 R10(越权) 有安全属性，
        需安全审计专项验证：风控超时放行的攻击面、越权转账的攻击路径、
        金额篡改注入。本策略预留安全测试入口。
```

---

## 4. 设计方法选择

> 依据 `core/testing-principles.md` 第 2 节，按功能特征选设计方法。

| 功能特征 | 设计方法 | 覆盖维度 | 对应风险 |
|---------|---------|---------|---------|
| 复杂业务流程（转账编排） | Workflow | functional | R1, R2, R5, R6 |
| 输入输出型（金额/限额/备注） | 等价类划分 + 边界值分析 | boundary | R3, R4, R7, R8, R9 |
| API（转账接口） | Parameter Matrix | concurrency, functional | R2, R3, R6, R11 |
| 明显状态流转（转账单） | State Machine | state_transition | R5, R12 |
| 权限系统（用户角色） | Role × Action × Resource | permission | R10 |

**二阶交叉覆盖重点**（依据 testing-principles.md 第 3 节）：

1. **写入路径 × 校验规则**：单笔限额、日累计限额、余额校验在「正常转账」「风控审核后到账」「补偿回滚后重新发起」等每条写入路径上是否都生效。
2. **失败 × 重试**：风控服务不可用 → 重试恢复；补偿回滚失败 → 重试恢复；网络超时 → 幂等重试。
3. **标识 × 重复**：转账单号唯一性（R11）；同一发起方对同一收款方的重复转账行为（R2 幂等）。

---

## 5. 自动化计划提案（⏸ 等用户确认）

> 以下为提案，非最终裁决。用户确认前不启动执行类 skill。

```yaml
automation_plan:
  status: proposal  # ⏸ 等用户确认

  recommended_automated:
    - id: AUTO-01
      target: "R2 幂等性验证 — 重复请求不产生重复转账单"
      framework: "API 脚本（pytest + requests）"
      reason: "接口级校验，需精确控制请求重发时序与并发"
    - id: AUTO-02
      target: "R3 日累计缓存窗口 — 30s 内连续转账超限"
      framework: "API 脚本（pytest + 并发库）"
      reason: "需精确控制时间窗口与并发请求顺序"
    - id: AUTO-03
      target: "R6 余额并发竞争 — 同账户并发扣减不超扣"
      framework: "API 脚本（pytest + 并发库 / locust）"
      reason: "需模拟多请求同时扣减同一账户"
    - id: AUTO-04
      target: "R1 补偿回滚完整性 — 各步骤失败后回滚"
      framework: "API 脚本（pytest + mock 故障注入）"
      reason: "需 mock 余额服务/风控服务中间步骤失败"
    - id: AUTO-05
      target: "R5 风控回调超时放行"
      framework: "API 脚本（pytest + mock 延迟）"
      reason: "需模拟回调超时 10 分钟场景"
    - id: AUTO-06
      target: "R4 金额精度 — float→Decimal 转换边界"
      framework: "API 脚本（pytest 参数矩阵）"
      reason: "需精确输入特定金额组合验证精度"
    - id: AUTO-07
      target: "R7 限额边界值 — 单笔/日累计等价类与边界"
      framework: "API 脚本（pytest 参数矩阵）"
      reason: "等价类 + 边界值，数据驱动适合自动化"
    - id: AUTO-08
      target: "主流程 E2E — 发起→直接成功 / 发起→风控→成功"
      framework: "Playwright（如有 UI）或 API 脚本（如无 UI）"
      reason: "有 UI 主流程冒烟；无 UI 则 API 链路冒烟"
      note: "待澄清：是否有 UI"

  not_automated:
    - target: "R9 备注长度边界探索"
      reason: "一次性验证，手动即可"
    - target: "R10 权限矩阵探索性测试"
      reason: "探索性测试，人工判断更灵活"
    - target: "R12 非法状态转换探索"
      reason: "需构造特定操作序列，探索性为主"
    - target: "风控审核人工交互流程"
      reason: "涉及风控人员操作，需手动或独立测试环境"
```

---

## 6. 回归策略

```yaml
regression_plan:
  # 回归锚点 — 每次必跑（来自 Critical/High 风险与 P0 用例）
  anchors:
    - id: ANC-01
      risk: R2
      description: "重复转账防护 — 幂等性验证"
      priority: P0
    - id: ANC-02
      risk: R3
      description: "日累计限额 — 缓存窗口内连续转账不超限"
      priority: P0
    - id: ANC-03
      risk: R1
      description: "补偿回滚 — 扣款后风控失败，余额正确回滚"
      priority: P0
    - id: ANC-04
      risk: R5
      description: "风控超时放行 — 10 分钟超时后自动放行行为"
      priority: P0
    - id: ANC-05
      risk: R4
      description: "金额精度 — float 计算边界值不产生误差"
      priority: P0
    - id: ANC-06
      risk: R6
      description: "并发扣减 — 同账户并发转账不超扣"
      priority: P0

  # 按变更类型的扩展规则
  extension_rules:
    - trigger: "transfer_service.py 接口签名或编排逻辑变更"
      action: "接口用例全量回归 + 补偿回滚用例全量"
    - trigger: "余额服务接口变更"
      action: "补偿回滚 + 并发扣减用例全量"
    - trigger: "风控服务接口 / 回调逻辑变更"
      action: "风控流程用例全量（含超时放行、审核拒绝、审核通过）"
    - trigger: "缓存策略变更（刷新频率 / 缓存层级）"
      action: "日累计 + 并发用例全量"
    - trigger: "金额计算逻辑变更"
      action: "精度 + 边界值用例全量"
    - trigger: "转账单号生成逻辑变更"
      action: "唯一性 + 幂等用例全量"
    - trigger: "UI 变更（如有）"
      action: "主流程 E2E 回归"

  regression_rhythm:
    default: "每次代码合入触发锚点集（6 条 P0）"
    release_gate: "锚点集 + 扩展规则触发的全量用例"
```

---

## 7. 风险等级 → 用例优先级映射要求

> 依据 `core/risk-model.md` 第 3 节。策略阶段可调整，但必须显式说明理由。

| 风险等级 | 用例优先级要求 | 本功能映射 | 说明 |
|---------|---------------|-----------|------|
| Critical | 必须有 P0 用例，且作为回归锚点 | R2 → P0（ANC-01）；R3 → P0（ANC-02） | 无偏离 |
| High | P0 或 P1 | R1 → P0（ANC-03）；R5 → P0（ANC-04）；R4 → P0（ANC-05）；R6 → P0（ANC-06） | R1/R5/R4/R6 提升至 P0：资损路径，补偿/精度/并发任一失效即资金事故，从严要求 |
| Medium | P1 | R7 → P1；R8 → P1；R9 → P1；R10 → P1；R11 → P1；R12 → P1 | 无偏离 |
| Low | P2 或按需 | — | 本功能无 Low 级风险 |

---

## 8. 下游索引

> 交付 `test-case-writing` 的一句话索引：

**策略路径**：`余额转账/测试策略.md`
**必测维度**：functional(full) / boundary(full) / concurrency(full) / state_transition(full) / permission(standard) / regression(standard)
**优先级映射要求**：R2/R3 → P0 锚点；R1/R4/R5/R6 → P0 锚点（资损从严）；R7–R12 → P1。性能/安全移交 k6 / 安全审计，不自行编写。
**设计方法**：Workflow（转账主链）、EP+BVA（金额/限额/备注）、Parameter Matrix（API 参数）、State Machine（转账单状态）、Role×Action×Resource（权限）。
**二阶交叉重点**：写入路径 × 校验规则（限额/余额校验在每条写入路径生效）、失败 × 重试（风控不可用/补偿失败/网络超时）、标识 × 重复（单号唯一性 + 重复转账幂等）。

---

## 9. 待澄清清单

| # | 问题 | 影响范围 | 当前处理 |
|---|------|---------|---------|
| Q1 | 余额服务是否已有并发控制机制（乐观锁/悲观锁/分布式锁）？ | R6 Likelihood 估计 | 保守估计 Likelihood=3，待确认后调整 |
| Q2 | 补偿回滚逻辑的具体实现：哪些步骤有补偿，哪些没有？补偿是同步还是异步？ | R1 评级与用例设计 | 保守假设补偿可能不完整，待读代码确认 |
| Q3 | 风控回调超时 10 分钟自动放行是产品设计意图还是临时实现？是否有降级开关？ | R5 Impact 与 Likelihood | 按当前代码行为评级，待确认设计意图后可能调整 |
| Q4 | 转账功能是否有 UI？前端形态是什么（Web/App/小程序）？ | automation_plan 中 Playwright 适用性、compatibility 维度深度 | AUTO-08 预留两条路径，待确认后裁剪 |
| Q5 | 转账单号随机数的位数/范围？ | R11 Likelihood 估计 | 保守估计 Likelihood=2，待确认后调整 |
| Q6 | 余额服务、风控服务的 SLA（可用性、平均延迟）？ | R1/R5 补偿与超时触发频率估计 | 按常规场景估计，待确认后调整 |
| Q7 | 是否有历史 Bug 数据（同功能区/同模块）？ | 各风险 Likelihood 估计 | 缺失，按代码证据估计，待补充后校准 |
| Q8 | "实时到账"的实时性 SLA（秒级？分钟级？）？ | performance handoff 的压测指标定义 | 预留性能入口，待确认后细化 k6 指标 |
| Q9 | 风控审核的正常 SLA（平均审核时长）？10 分钟超时阈值是否合理？ | R5 测试设计与超时阈值合理性判断 | 按代码 10 分钟评级，待确认设计意图 |
| Q10 | 日累计的"日"是自然日（0 点重置）还是滚动 24 小时？ | R3/R7 测试设计（跨日边界用例） | 按自然日假设，待确认后调整 |
| Q11 | 部署形态是单实例还是多实例？本地缓存是否共享？ | R3 多实例缓存一致性严重程度 | 保守假设多实例独立缓存，待确认后调整 |
| Q12 | 转账是否支持撤销/退款？逆向操作如何处理？ | 测试原则第 8 条「逆向操作成对验证」 | 需求未提及，待确认是否纳入范围 |