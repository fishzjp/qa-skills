# 余额转账功能测试策略

> **策略定位**：需求 → 风险分析 → **策略（本文档）** → 测试设计 → 用例
> 跳过策略直接写用例是本框架明确反对的。本文档定义"测什么、测多深、为什么不测"，不包含具体用例。

---

## 1. 功能概述

| 项 | 内容 |
|---|------|
| **被测功能** | 站内用户间余额转账，实时到账 |
| **角色** | 普通用户（发起/收款）、风控（大额与异常拦截） |
| **核心规则** | 单笔 ≤ 5000 元；日累计 ≤ 20000 元；余额不足拦截；金额保留 2 位小数；大额（≥ 2000）触发风控审核，审核通过才到账，审核中资金冻结；备注 ≤ 50 字 |
| **状态流转** | 发起 → 风控审核（大额）/ 直接成功 → 成功 / 失败 |
| **依赖服务** | 余额服务、风控服务、消息通知 |
| **实现形态** | 后端 `transfer_service.py` 编排三步流程（扣发起方 → 调风控 → 加收款方），API 驱动，无 UI 层信息 |

---

## 2. Risk Map

### 2.1 风险总览

| ID | 维度 | 风险描述 | I×L | 等级 | 优先级要求 | 证据 |
|----|------|---------|-----|------|-----------|------|
| R1 | 数据一致性 | 三步编排无分布式事务，补偿回滚失败致资金不一致 | 5×3=15 | **High** | P0 或 P1 | E2 `transfer_service.py` |
| R2 | 数据一致性 | 金额中间计算用 float，精度丢失致金额偏差 | 4×4=16 | **High** | P0 或 P1 | E2 `transfer_service.py` |
| R3 | 并发 | 日累计校验读本地缓存（30s 刷新），并发绕过限额 | 4×5=20 | **Critical** | P0 + 回归锚点 | E2 `transfer_service.py` |
| R4 | 并发/资损 | 无幂等键，网络重试致重复转账单 | 5×4=20 | **Critical** | P0 + 回归锚点 | E2 `transfer_service.py` |
| R5 | 安全/资损 | 风控回调超时 10 分钟自动放行，异常大额被放行 | 5×3=15 | **High** | P0 或 P1 | E2 `transfer_service.py` |
| R6 | 数据一致性 | 单号无唯一约束，高并发下可能冲突 | 3×2=6 | **Medium** | P1 | E2 `transfer_service.py` |
| R7 | 边界 | 单笔/日累计限额边界校验 off-by-one | 3×3=9 | **Medium** | P1 | E1 需求模型-规则 |
| R8 | 权限 | 鉴权机制未明确，跨用户操作风险 | 5×2=10 | **High** | P0 或 P1 | E1 需求模型 + 代码走读 |

### 2.2 风险详情

#### R1：三步编排无分布式事务，补偿回滚失败

```yaml
risk:
  id: R1
  feature: 余额转账
  dimension: 数据一致性
  impact: 5            # 扣款成功但加款失败=直接资损
  likelihood: 3        # 补偿逻辑在服务故障/网络异常时可能失败
  level: High          # 15 = 5 × 3
  evidence:
    level: E2
    source: "transfer_service.py：三步编排（扣发起方→调用风控→加收款方）无分布式事务，靠补偿回滚"
  confidence: medium
  status: needs_verification
  anchors: []          # 待 test-case-writing 回填
```

#### R2：金额中间计算用 float 致精度丢失

```yaml
risk:
  id: R2
  feature: 余额转账
  dimension: 数据一致性
  impact: 4            # 金额计算偏差=资损/对账不一致
  likelihood: 4        # float 计算金额是经典精度 bug，中间计算用 float 几乎必然引入误差
  level: High          # 16 = 4 × 4
  evidence:
    level: E2
    source: "transfer_service.py：金额中间计算用 float，仅入库前转 Decimal"
  confidence: high
  status: inference
  anchors: []
```

#### R3：日累计校验读本地缓存，并发绕过限额

```yaml
risk:
  id: R3
  feature: 余额转账
  dimension: 并发
  impact: 4            # 日累计限额失效=超额转账=资损
  likelihood: 5        # 缓存 30 秒窗口内并发请求几乎必然绕过
  level: Critical      # 20 = 4 × 5
  evidence:
    level: E2
    source: "transfer_service.py：日累计校验从本地缓存读取，缓存 30 秒刷新"
  confidence: high
  status: risk
  anchors: []
```

#### R4：无幂等键，网络重试致重复转账

```yaml
risk:
  id: R4
  feature: 余额转账
  dimension: 并发/资损
  impact: 5            # 重复转账=直接资损
  likelihood: 4        # 网络重试是常见场景，无幂等键则必然产生重复单
  level: Critical      # 20 = 5 × 4
  evidence:
    level: E2
    source: "transfer_service.py：转账请求无幂等键"
  confidence: high
  status: risk
  anchors: []
```

#### R5：风控回调超时自动放行

```yaml
risk:
  id: R5
  feature: 余额转账
  dimension: 安全/资损
  impact: 5            # 异常大额/风控目标转账被放行=资损
  likelihood: 3        # 回调超时在网络/服务异常时可触发
  level: High          # 15 = 5 × 3
  evidence:
    level: E2
    source: "transfer_service.py：风控回调超时 10 分钟自动放行"
  confidence: medium
  status: needs_verification
  anchors: []
```

#### R6：单号无唯一约束，高并发冲突

```yaml
risk:
  id: R6
  feature: 余额转账
  dimension: 数据一致性
  impact: 3            # 单号冲突致数据写入异常或关联混乱
  likelihood: 2        # 时间戳+随机数冲突概率低，但高并发下存在
  level: Medium        # 6 = 3 × 2
  evidence:
    level: E2
    source: "transfer_service.py：转账单号用时间戳+随机数生成，无唯一约束"
  confidence: medium
  status: risk
  anchors: []
```

#### R7：限额边界校验 off-by-one

```yaml
risk:
  id: R7
  feature: 额转账
  dimension: 边界
  impact: 3            # 边界校验错误致可超额转账
  likelihood: 3        # 需确认代码实现（≤ 还是 <）
  level: Medium        # 9 = 3 × 3
  evidence:
    level: E1
    source: "需求模型-规则：单笔 ≤ 5000，日累计 ≤ 20000"
  confidence: low
  status: needs_verification
  anchors: []
```

#### R8：鉴权机制未明确

```yaml
risk:
  id: R8
  feature: 余额转账
  dimension: 权限
  impact: 5            # 跨用户操作余额=资损/安全
  likelihood: 2        # 标准实现通常有鉴权，但代码走读未确认
  level: High          # 10 = 5 × 2
  evidence:
    level: E1
    source: "需求模型-角色：定义角色但未明确鉴权规则；代码走读要点未提及鉴权实现"
  confidence: low
  status: needs_verification
  anchors: []
```

---

## 3. 测试范围决策

### 3.1 范围矩阵

```yaml
test_strategy:
  feature: 余额转账
  scope:
    functional:
      include: true
      depth: full
      rationale: "核心资损路径。R1/R4/R5 为 Critical/High 风险，状态流转每条边 + 补偿回滚每条路径需全覆盖"
      design_method: "State Machine（状态流转）+ Workflow（端到端主链 + 失败分支 + 中断恢复）"
      risk_ref: [R1, R3, R4, R5]
    boundary:
      include: true
      depth: full
      rationale: "单笔 5000/日累计 20000/备注 50 字/金额 2 位小数均有明确边界；R7 Medium，边界 off-by-one 高发"
      design_method: "Equivalence Partitioning + Boundary Value Analysis"
      risk_ref: [R7]
    permission:
      include: true
      depth: full
      rationale: "R8 权限风险 High；资金功能权限失效=直接资损，需逐格核对角色 × 操作 × 资源"
      design_method: "Role × Action × Resource 矩阵 + 资源级隔离（A 的余额 B 不可操作）"
      risk_ref: [R8]
    regression:
      include: true
      depth: standard
      rationale: "无历史 Bug 数据；R3/R4 Critical 风险用例必须作为回归锚点"
      risk_ref: [R3, R4]
    compatibility:
      include: true
      depth: light
      rationale: "站内转账无明确多端差异需求；Web/App 一致性抽样冒烟即可"
      risk_ref: []
    performance:
      include: false
      handoff: "专项：k6"
      rationale: "并发是风险维度（R3/R4），但并发正确性验证归入 functional（API 并发脚本）；压测/容量不在本框架自研范围，移交 k6 专项"
    security:
      include: false
      handoff: "专项：安全审计"
      rationale: "R5 风控绕过/R8 鉴权涉及安全，但深度安全审计不在本框架自研范围；权限维度的功能级验证仍在本策略覆盖（permission scope）"
```

### 3.2 各维度详细说明

#### functional（full）

**覆盖范围**：

| 子项 | 设计方法 | 覆盖要点 | 风险追溯 |
|------|---------|---------|---------|
| 状态流转 | State Machine | 转账单状态：发起 → 风控审核 / 直接成功 → 成功 / 失败；每条边一个用例；非法转换配拦截用例 | R1, R5 |
| 端到端主链 | Workflow | 发起 → 扣余额 → 风控（大额）/ 直通 → 加收款方余额 → 通知 | R1 |
| 失败分支 | Workflow | 三步任一失败的补偿回滚路径（扣款后风控失败、加款失败） | R1 |
| 中断恢复 | Workflow | 风控审核中状态 → 回调成功 / 回调失败 / 回调超时 | R5 |
| 并发正确性 | 并发测试 | 并发多笔转账验证日累计限额、重复请求验证幂等性 | R3, R4 |
| 金额计算 | Input→Transform→Output | 典型金额 / 精度敏感组合（0.1+0.2 等）/ 畸形输入 → 逐类核对入库金额 | R2 |

**二阶交叉覆盖要求**（参照 `core/testing-principles.md` 第 3 节）：

1. **写入路径 × 校验规则**：限额校验（单笔/日累计）是否在发起、网络重试、补偿回滚后重发**每条写入路径**上都生效——校验常只挂在首次发起，重试/补偿路径绕过校验的 bug 高发。
2. **失败 × 重试**：三步编排中任一步失败后，重试能否恢复至一致的终态（发起方余额、收款方余额、转账单状态三者对齐）。
3. **标识 × 重复**：转账单号（时间戳+随机数）重复提交时的唯一性行为——无唯一约束下数据库是否允许重复写入、业务层是否有兜底。

#### boundary（full）

| 边界对象 | 等价类 | 边界取值 | 风险追溯 |
|---------|--------|---------|---------|
| 单笔金额 | 有效：0.01–5000；无效：<0、>5000、0、负数 | 0 / 0.01 / 4999.99 / 5000 / 5000.01 / 超大值 | R7 |
| 日累计金额 | 有效：≤20000；无效：>20000 | 19999.99 / 20000 / 20000.01（多笔累积逼近） | R3, R7 |
| 大额阈值 | 大额：≥2000；非大额：<2000 | 1999.99 / 2000 / 2000.01 | R5 |
| 转账备注 | 有效：0–50 字；无效：>50 字 | 空 / 50 字 / 51 字 / 超长 | — |
| 金额精度 | 有效：2 位小数；无效：3+ 位小数 | 0.01 / 0.001 / 0.005（舍入行为） | R2 |

#### permission（full）

| 角色维度 | 覆盖要点 | 风险追溯 |
|---------|---------|---------|
| Role × Action × Resource | 普通用户：发起转账（操作自己的余额）；普通用户：收款（被动）；风控：审核（仅大额/异常） | R8 |
| 资源级隔离 | 用户 A 不能从用户 B 的账户转出；用户 A 不能查看/操作他人余额 | R8 |
| 越权尝试 | 伪造收款方 ID、篡改发起方身份、未登录访问转账接口 | R8 |
| 权限即时性 | 角色变更（如冻结账户后）能否即时阻止转账 | R8 |

#### compatibility（light）

| 子项 | 覆盖要点 |
|------|---------|
| Web/App 一致性 | 转账主流程在 Web 与 App 端行为一致（抽样冒烟） |
| — | 本功能为 API 驱动，无多端特殊逻辑，light 抽样即可 |

#### 不测维度与理由

| 维度 | 决策 | 理由 | 移交 |
|------|------|------|------|
| performance | exclude | 并发正确性验证归入 functional（API 并发脚本）；压测/容量/响应时间不在本框架自研范围 | k6 专项 |
| security | exclude | R5 风控绕过/R8 鉴权涉及深度安全测试；权限功能级验证已在 permission scope 覆盖 | 安全审计专项 |

---

## 4. 风险等级 → 用例优先级映射

| 风险等级 | 对应风险 | 用例优先级要求 | 说明 |
|---------|---------|---------------|------|
| **Critical** | R3, R4 | 必须有 P0 用例，且作为回归锚点 | 并发绕过限额、重复转账为资损直触路径 |
| **High** | R1, R2, R5, R8 | P0 或 P1 | R1 补偿回滚、R5 风控超时放行建议 P0；R2 精度、R8 鉴权可 P1（待澄清后升 P0） |
| **Medium** | R6, R7 | P1 | R6 单号冲突、R7 边界 off-by-one |

> 偏离说明：R8（鉴权）当前 confidence 为 low、status 为 needs_verification，若澄清确认鉴权实现完备，可降为 P1；若确认缺失，必须升 P0。

---

## 5. 自动化计划提案（⏸ 等用户确认）

### 5.1 建议自动化清单

| 序号 | 覆盖风险 | 用例特征 | 框架/工具 | 理由 |
|------|---------|---------|----------|------|
| A1 | R3 | 日累计并发绕过 | API 脚本（`api-testing`） | 需多线程并发发请求，验证缓存窗口内限额是否被绕过 |
| A2 | R4 | 幂等性/重复转账 | API 脚本（`api-testing`） | 需重复发送相同请求，验证是否产生重复单 |
| A3 | R1 | 补偿回滚验证 | API 脚本（`api-testing`） | 需 mock 余额服务/风控服务各步骤失败，验证回滚逻辑 |
| A4 | R5 | 风控回调超时 | API 脚本（`api-testing`） | 需 mock 回调延迟 >10min，验证自动放行行为 |
| A5 | R7 | 限额边界值 | API 脚本（`api-testing`） | 批量参数矩阵，逐边界值发送 |
| A6 | R2 | 金额精度 | API 脚本（`api-testing`） | 构造 float 精度敏感金额组合，验证入库金额 |
| A7 | R6 | 单号唯一性 | API 脚本（`api-testing`） | 高并发发送，检查单号是否冲突 |
| A8 | — | 主流程 E2E | Playwright（`automated-e2e-testing`） | 发起 → 审核 → 到账 → 通知，端到端冒烟回归 |

### 5.2 不自动化清单

| 序号 | 覆盖风险 | 用例特征 | 执行方式 | 理由 |
|------|---------|---------|---------|------|
| M1 | R1 | 补偿回滚失败的组合场景 | 手动探索性 | 需人工观察系统状态和数据一致性，自动化难以断言 |
| M2 | R5 | 风控审核业务规则验证 | 手动 | 需人工判断"异常"标准，非确定性规则 |
| M3 | R8 | 鉴权验证 | 待定 | 待确认鉴权实现后决定（token/session 可自动化；复杂认证流程手动） |

### 5.3 框架选择理由

- **API 脚本（`api-testing`）**：本功能为 API 驱动，并发/幂等/mock 场景用 API 脚本最直接、最可控。A1–A7 均为接口级验证。
- **Playwright（`automated-e2e-testing`）**：主流程 E2E 冒烟回归，覆盖用户视角端到端路径。仅 A8 一条，轻量。
- **手动**：探索性场景和业务规则判断，自动化成本高于收益。

> ⏸ 以上为提案。**确认前不启动执行类 skill。** 请用户确认：自动化清单是否照此执行、框架选择是否接受、不自动化清单是否同意。

---

## 6. 回归策略

### 6.1 回归锚点集（每次必跑）

| 锚点 | 覆盖风险 | 风险等级 | 用例优先级 | 验证目标 |
|------|---------|---------|-----------|---------|
| RA-1 | R3 | Critical | P0 | 日累计限额在并发下不被绕过 |
| RA-2 | R4 | Critical | P0 | 重复请求不产生重复转账单 |
| RA-3 | R1 | High | P0 | 三步编排中任一步失败后补偿回滚成功，资金一致 |

### 6.2 按变更类型的扩展规则

| 变更类型 | 扩展范围 | 理由 |
|---------|---------|------|
| `transfer_service.py` 编排逻辑变更 | 接口用例全量 | 核心编排逻辑影响所有转账路径 |
| 余额服务接口变更 | 集成用例全量 + RA-1/RA-2/RA-3 | 余额读写是资金一致性的核心 |
| 风控服务接口变更 | 风控相关用例全量 + RA-3 | 风控回调逻辑影响审核状态流转 |
| 金额计算逻辑变更 | R2 精度用例全量 + RA-1 | 精度问题影响所有金额路径 |
| 限额校验逻辑变更 | 边界用例全量 + RA-1 | 限额校验影响风控边界 |
| 转账 UI 变更 | 主流程 E2E（A8） | UI 变更影响用户操作路径 |
| 幂等/单号机制变更 | RA-2 全量 + R6 用例 | 幂等机制变更是重复转账的直接防线 |

### 6.3 回归节奏

- **每次发布**：锚点集 RA-1/RA-2/RA-3 必跑。
- **接口变更发布**：按 6.2 扩展规则追加全量。
- **无变更例行回归**：锚点集 + 主流程 E2E（A8）。

---

## 7. 下游索引

> **给 `test-case-writing` 的一句话索引**：
> 策略路径：`{项目}/测试策略.md`；必测维度：functional（full）/ boundary（full）/ permission（full）/ regression（standard）；优先级映射：R3/R4 → P0+回归锚点，R1/R2/R5/R8 → P0 或 P1，R6/R7 → P1；每条用例 `risk_ref` 必须追溯到 Risk Map 中的 R 编号。

---

## 8. 待澄清清单

| 序号 | 关联风险 | 问题 | 影响范围 |
|------|---------|------|---------|
| Q1 | R1 | 补偿回滚逻辑的具体实现是什么？哪些场景触发回滚？回滚失败是否有告警/重试/人工介入？ | 决定 functional 失败分支用例的深度与数量 |
| Q2 | R1 | 风控审核失败后，冻结资金的退回路径是同步还是异步？退回失败如何处理？ | 决定状态流转"审核中→失败"边的用例设计 |
| Q3 | R5 | 风控回调超时自动放行是否有告警机制？是否有人工介入流程？超时阈值是否可配置？ | 决定安全/资损维度是否升 Critical |
| Q4 | R7 | 限额边界代码实现是 `amount <= 5000` 还是 `amount < 5000`？需求写 ≤ 但实现可能不同 | 决定边界用例的预期值（5000 是通过还是拦截） |
| Q5 | R8 | 转账操作是否有鉴权校验（token/session/接口权限）？具体实现方式是什么？ | 决定权限维度用例优先级（P0 或 P1）及自动化可行性 |
| Q6 | R3 | 日累计校验是否有兜底机制（如定时全量校验、缓存失效后强制读库）？ | 决定并发用例的断言策略（是否一定绕过） |
| Q7 | R4 | 是否计划增加幂等键？如已有幂等补偿（如基于单号的去重），去重逻辑在哪层？ | 决定幂等用例的预期（确认产生重复单 vs 拦截重复） |
| Q8 | R2 | float 计算→Decimal 转换的具体位置在哪？是否所有金额路径都经过转换？ | 决定精度用例的覆盖面 |