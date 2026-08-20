# 余额转账 - 测试策略

```yaml
test_strategy:
  feature: 余额转账（站内用户间实时转账）
```

---

## 一、Risk Map

> 每条风险按 Impact × Likelihood（各 1–5）评级，强制挂证据（level + source）。没有证据的评级视为无效。

| ID | 维度 | 风险描述 | Impact | Likelihood | Score | Level | Evidence | Confidence | Status |
|----|------|---------|--------|------------|-------|-------|----------|------------|--------|
| R1 | 并发 / 幂等 | 转账请求无幂等键，网络重试产生重复转账单，导致重复扣款或重复到账 | 5（资损） | 4（网络重试为常规路径，移动端弱网/用户连续点击均会触发） | 20 | **Critical** | E2 — `transfer_service.py`：请求入口无幂等键校验 | high | needs_verification |
| R2 | 数据一致性 | 日累计校验从本地缓存读取，30 秒刷新窗口内可并发超额转账，突破 20000 元日限 | 5（资损） | 4（30 秒窗口宽，高并发或用户快速连发即可命中） | 20 | **Critical** | E2 — `transfer_service.py`：日累计从本地缓存读取，TTL=30s | high | needs_verification |
| R3 | 数据一致性 | 三步编排（扣发起方 → 调风控 → 加收款方）无分布式事务，任一步失败靠补偿回滚；补偿失败或部分失败时资金状态不一致 | 5（资损） | 3（需中间步骤失败才触发，但风控服务/消息服务不可用时为常规故障路径） | 15 | **High** | E2 — `transfer_service.py`：三步编排无分布式事务，依赖补偿逻辑 | medium | needs_verification |
| R4 | 安全 / 资损 | 风控异步回调超时 10 分钟自动放行，大额异常转账可能在风控未决策时被放行 | 5（资损） | 3（需风控服务异常/回调链路超时，但生产环境第三方服务波动常见） | 15 | **High** | E2 — `transfer_service.py`：回调超时 10min 自动放行逻辑 | medium | needs_verification |
| R5 | 数据一致性 | 金额中间计算用 `float`，仅入库前转 `Decimal`；浮点精度可能导致金额计算偏差 | 4（功能不可用/金额错误） | 3（特定金额组合触发精度问题，如 0.1+0.2 类场景） | 12 | **High** | E2 — `transfer_service.py`：中间计算 float，入库前转 Decimal | medium | needs_verification |
| R6 | 数据一致性 | 转账单号用"时间戳+随机数"生成，无唯一约束；高并发下单号碰撞可能导致数据混乱或重复 | 4（功能不可用/数据混乱） | 3（高并发碰撞概率低但存在，无 DB 唯一约束兜底） | 12 | **High** | E2 — `transfer_service.py`：单号生成无唯一约束 | medium | needs_verification |
| R7 | 边界 | 单笔限额（≤5000）、日累计（≤20000）、备注（≤50 字）、金额精度（2 位小数）边界校验可能遗漏或不一致 | 3（部分功能降级） | 3（边界条件常规可触发） | 9 | **Medium** | E1 — 需求模型：规则条目 | high | inference |
| R8 | 状态流转 | 转账单状态流转：发起 → 风控审核/直接成功 → 成功/失败；审核中资金冻结，非法转换或中间态操作未拦截 | 4（资金状态不一致） | 2（状态机较明确，但异步回调和超时放行增加复杂度） | 8 | **Medium** | E1 — 需求模型：状态定义 + E2 风控异步回调逻辑 | medium | needs_verification |
| R9 | 权限 | 角色边界：普通用户只能发起/收款，风控角色审核；需验证普通用户不能触发风控放行或越权操作 | 3（部分功能降级） | 2（需构造特定条件） | 6 | **Medium** | E1 — 需求模型：角色定义 | high | inference |
| R10 | 兼容性 | 依赖余额服务、风控服务、消息通知；下游服务波动时转账主流程降级或通知丢失 | 2（体验问题） | 3（依赖服务波动常见） | 6 | **Medium** | E1 — 需求模型：依赖声明 | medium | inference |
| R11 | 并发 | 同一用户同时发起多笔转账，余额扣减无行级锁/版本控制可能导致超额扣减（余额变负） | 5（资损） | 3（用户多端同时操作即可触发） | 15 | **High** | E2 — `transfer_service.py`：先扣余额，未确认是否有行级锁/乐观锁（待核实） | low | needs_verification |

### 风险等级 → 用例优先级映射

| 风险等级 | 涉及风险 | 用例优先级要求 |
|---------|---------|---------------|
| Critical | R1, R2 | 必须有 P0 用例，且作为回归锚点 |
| High | R3, R4, R5, R6, R11 | P0 或 P1 |
| Medium | R7, R8, R9, R10 | P1 |

---

## 二、测试范围与深度

```yaml
scope:
  functional:
    include: true
    depth: full
    rationale: >
      核心资损路径，Risk Map 中 R1–R6、R11 均指向功能正确性。
      逐条规则全覆盖：单笔限额、日累计限额、余额不足拦截、大额风控冻结/审核/放行、
      备注长度、金额精度。设计方法按 testing-principles §2：
      主体为 Workflow（端到端主链 + 每环节失败分支 + 中断恢复），
      辅以 State Machine（转账单状态流转，每条边一个用例 + 非法转换拦截）。

  boundary:
    include: true
    depth: full
    rationale: >
      R7 为 Medium，但金额边界直接关联资损路径（R5 float 精度）。
      全覆盖：单笔金额 0 / 0.01 / 4999.99 / 5000 / 5000.01 / 负数 / 超大数；
      日累计 19999.99 / 20000 / 20000.01；备注 0 / 50 / 51 字。
      Equivalence Partitioning + Boundary Value Analysis。

  permission:
    include: true
    depth: standard
    rationale: >
      R9 为 Medium。主干 + 重点异常：普通用户发起/收款正常路径 +
      普通用户尝试触发风控放行/越权查看他人转账单拦截。
      Role × Action × Resource 矩阵逐格核对关键行为。

  concurrency:
    include: true
    depth: full
    rationale: >
      R1（无幂等，重复转账）、R2（缓存窗口超额）、R11（余额超额扣减）均为 Critical/High。
      逐场景全覆盖：网络重试重复提交、30 秒窗口内并发多笔突破日累计、
      同用户多端同时发起扣减、转账单号高并发碰撞。
      这是本功能最高优先级测试维度。

  state_transition:
    include: true
    depth: full
    rationale: >
      R8 为 Medium，但状态流转涉及资金冻结/释放，错误转换直接导致资损。
      逐条边覆盖：发起→直接成功、发起→风控审核、风控审核→成功、风控审核→失败、
      风控审核→超时放行；非法转换（成功→发起、失败→成功）配拦截用例。

  error_recovery:
    include: true
    depth: full
    rationale: >
      R3 为 High（三步无分布式事务，靠补偿回滚）。
      逐环节失败 + 恢复：扣款成功后风控调用失败 → 补偿回滚扣款；
      风控通过后加款失败 → 补偿处理；补偿本身失败 → 资金状态与告警。
      按 testing-principles §1 原则 7（失败→重试→恢复）+ 原则 8（逆向操作成对验证）。

  data_consistency:
    include: true
    depth: full
    rationale: >
      R3/R5/R6 均为 High。逐条覆盖：三步中间态余额一致性、
      float→Decimal 精度偏差、转账单号唯一性（无约束下的碰撞行为）。

  regression:
    include: true
    depth: standard
    rationale: >
      P0 回归锚点 + 接口变更扩展规则。见下方 regression_plan。

  compatibility:
    include: true
    depth: light
    rationale: >
      R10 为 Medium，依赖服务波动为体验问题。抽样冒烟：
      余额服务/风控服务/消息通知不可用时主流程降级行为 + 恢复后自愈。

  performance:
    include: false
    handoff: "专项：k6 / locust — 并发扣减、缓存窗口突破、单号碰撞需压测验证，本框架不自研，移交性能专项"
    rationale: >
      R1/R2/R11 的并发风险在功能层面以构造性测试覆盖（显式并发请求），
      但高负载下的竞态窗口与吞吐瓶颈需压测工具量化，移交 k6 专项。

  security:
    include: false
    handoff: "专项：安全审计 — 风控回调超时放行（R4）、幂等缺失（R1）涉及安全攻击面，移交安全审计"
    rationale: >
      R4 回调超时自动放行可被攻击者利用（故意延迟回调绕过风控），
      属安全攻防范畴，移交安全审计专项。本策略仅覆盖功能层面的超时放行行为验证。
```

---

## 三、Risk → 测试类型 → 设计方法 推导

| 风险 ID | 测试类型 | 设计方法（testing-principles §2） | 核心测试动作 |
|---------|---------|------|------------|
| R1 | 并发 / 幂等 | API Parameter Matrix + 逆向操作 | 相同请求重放 N 次，验证只产生 1 笔转账单；构造网络超时后重试，验证无重复扣款 |
| R2 | 并发 / 边界 | Concurrency + Boundary | 30 秒缓存窗口内并发发起多笔，验证日累计不超额；验证缓存刷新后的累计准确性 |
| R3 | 错误恢复 | Workflow（失败分支 + 中断恢复） | 逐环节注入失败（扣款后风控失败、风控后加款失败），验证补偿回滚正确性；补偿失败后资金状态 |
| R4 | 状态流转 / 安全 | State Machine + 时间边界 | 大额转账进入风控审核 → 回调超时 10min → 验证自动放行行为；验证超时放行后资金解冻 |
| R5 | 数据一致性 | Input→Transform→Output | 典型金额（0.1+0.2、大额带小数）、畸形输入 → 验证计算保真（读回一致） |
| R6 | 数据一致性 / 唯一性 | 标识×重复（§3 交叉覆盖） | 高并发生成单号 → 验证无碰撞；单号重复时 DB 行为（无约束下的容错/报错） |
| R7 | 边界 | Equivalence Partitioning + BVA | 单笔/日累计/备注/精度的等价类划分与边界取值 |
| R8 | 状态流转 | State Machine | 每条状态边一个用例 + 非法转换拦截 |
| R9 | 权限 | Role × Action × Resource | 角色行为矩阵逐格 + 资源级隔离（A 的转账单 B 不可见） |
| R10 | 兼容性 | 降级冒烟 | 逐个依赖不可用 → 主流程降级行为 + 恢复后自愈 |
| R11 | 并发 | Concurrency | 同用户多端同时发起多笔，验证余额不超额扣减（不变负） |

### 二阶交叉覆盖（testing-principles §3）

| 交叉类型 | 覆盖点 |
|---------|--------|
| 写入路径 × 校验规则 | 单笔限额/日累计/余额不足校验在"首次发起"、"重试发起"、"风控驳回后重新发起"每条写入路径上是否都生效 |
| 失败 × 重试 | 扣款失败/风控失败/加款失败 → 重试发起 → 恢复正常（与 R3 补偿回滚联合验证） |
| 标识 × 重复 | 转账单号时间戳+随机数碰撞时唯一性行为（与 R6 联合验证） |

---

## 四、自动化计划提案

> ⏸ **以下为提案，不裁决。需用户确认后启动执行类 Skill。**

```yaml
automation_plan:
  status: proposal
  pending: user_confirmation

  recommended_automated:
    - target: "并发/幂等重复转账（R1）"
      framework: "API 脚本（api-testing）— Python + httpx + asyncio 并发"
      reason: "需精确控制并发请求时序与重放，API 层最有效"
      priority: P0

    - target: "缓存窗口突破日累计（R2）"
      framework: "API 脚本（api-testing）— 并发请求 + 时间窗口控制"
      reason: "需在 30 秒窗口内精确并发，UI 无法控制时序"
      priority: P0

    - target: "同用户多端并发扣减（R11）"
      framework: "API 脚本（api-testing）— 并发请求 + 余额断言"
      reason: "并发竞态验证，需 API 层精确控制"
      priority: P0

    - target: "补偿回滚正确性（R3）"
      framework: "API 脚本（api-testing）+ mock 故障注入"
      reason: "需 mock 风控/加款失败，验证补偿逻辑，API 层可注入故障"
      priority: P0

    - target: "转账单状态流转全路径（R8）"
      framework: "API 脚本（api-testing）"
      reason: "状态机验证，API 层可覆盖所有状态边"
      priority: P1

    - target: "金额边界与精度（R5/R7）"
      framework: "API 脚本（api-testing）— 参数化批量"
      reason: "等价类+边界值用例量大但模式统一，参数化适合自动化"
      priority: P1

    - target: "转账主流程 E2E（冒烟）"
      framework: "Playwright（automated-e2e-testing）"
      reason: "有 UI 主流程冒烟，验证端到端可走通"
      priority: P1

  recommended_manual:
    - target: "风控回调超时自动放行（R4）"
      reason: "需等待 10 分钟超时 + 验证资金解冻时序，自动化 ROI 低；手动构造 + 观察"
      priority: P0

    - target: "依赖服务降级行为（R10）"
      reason: "需模拟下游服务不可用，探索性观察降级表现，手动更灵活"
      priority: P1

    - target: "权限矩阵边界（R9）"
      reason: "角色行为矩阵格数有限，手动执行即可；自动化 ROI 低"
      priority: P1

  not_automated:
    - target: "转账单号高并发碰撞（R6）"
      reason: "需极高并发量级才能触发碰撞，属性能测试范畴，移交 k6 专项"
      handoff: "k6 压测"

    - target: "安全攻防（R4 超时放行攻击面）"
      reason: "安全审计范畴，移交安全专项"
      handoff: "安全审计"
```

---

## 五、回归策略

```yaml
regression_plan:
  anchors:
    - id: REG-01
      name: "幂等性 — 重复请求不产生重复转账单"
      risk_ref: [R1]
      priority: P0
      trigger: "每次必跑"

    - id: REG-02
      name: "日累计限额 — 缓存窗口内并发不超额"
      risk_ref: [R2]
      priority: P0
      trigger: "每次必跑"

    - id: REG-03
      name: "补偿回滚 — 风控失败后扣款正确回滚"
      risk_ref: [R3]
      priority: P0
      trigger: "每次必跑"

    - id: REG-04
      name: "转账主流程 — 正常小额转账端到端成功"
      risk_ref: [R7, R8]
      priority: P0
      trigger: "每次必跑"

    - id: REG-05
      name: "余额不足拦截"
      risk_ref: [R7]
      priority: P0
      trigger: "每次必跑"

  expansion_rules:
    - change_type: "transfer_service.py 编排逻辑变更"
      expansion: "R1–R6、R11 全量用例回归 + 补偿回滚全路径"

    - change_type: "风控回调/超时逻辑变更"
      expansion: "R4 全量用例 + 状态流转全路径（R8）"

    - change_type: "金额计算/精度逻辑变更"
      expansion: "R5 全量边界用例 + 数据一致性读回验证"

    - change_type: "日累计/缓存逻辑变更"
      expansion: "R2 全量并发用例 + 边界值全量"

    - change_type: "接口签名/参数变更"
      expansion: "接口用例全量回归"

    - change_type: "UI 变更"
      expansion: "转账主流程 E2E（Playwright）"

  regression_cadence:
    pre_merge: "REG-01 ~ REG-05 全跑"
    nightly: "REG-01 ~ REG-05 + R5/R7 边界用例"
    weekly: "全量 P0 + P1"
```

---

## 六、下游索引（交付 test-case-writing）

> **策略路径**：`{项目}/测试策略.md`
> **必测维度**：functional（full）、boundary（full）、concurrency（full）、error_recovery（full）、state_transition（full）、data_consistency（full）、permission（standard）、regression（standard）、compatibility（light）
> **优先级映射**：Critical（R1/R2）→ P0 且为回归锚点；High（R3/R4/R5/R6/R11）→ P0 或 P1；Medium（R7/R8/R9/R10）→ P1
> **设计方法**：主体 Workflow + State Machine；边界 BVA；并发 API 脚本；权限 Role×Action×Resource 矩阵
> **风险锚点**：每条用例 `risk_ref` 必须追溯到 Risk Map 中的 R1–R11

---

## 七、待澄清清单

| # | 问题 | 影响风险 | 当前假设 |
|---|------|---------|---------|
| Q1 | `transfer_service.py` 扣减余额时是否有行级锁或乐观锁？ | R11 | 假设无锁（代码走读未提及），按 High 评级；若有锁则 Likelihood 降至 2，Level 降为 Medium |
| Q2 | 补偿回滚失败后是否有告警/人工介入机制？资金如何对账？ | R3 | 假设无自动对账，补偿失败后资金不一致需人工处理；若有对账 Job 则增加恢复路径测试 |
| Q3 | 风控回调超时 10 分钟自动放行——这是产品需求还是技术兜底？是否有产品确认？ | R4 | 假设为技术兜底（代码实现），若为产品需求则需补充"超时放行后风控仍可追溯拦截"的测试 |
| Q4 | 转账单号无唯一约束——是否计划加 DB 唯一索引？还是接受碰撞概率？ | R6 | 假设当前接受碰撞（无约束），按 High 评级；若计划加索引则测试碰撞时的 DB 报错处理 |
| Q5 | 日累计缓存 30 秒刷新——是否有最终一致性校验（如定时对账修正）？ | R2 | 假设无对账修正，缓存窗口内超额不可逆；若有对账则增加"对账修正后超额转账处理"测试 |
| Q6 | float→Decimal 转换——具体在哪些计算环节用 float？是否有已知的精度问题案例？ | R5 | 假设全程中间计算用 float，按 High 评级；若仅展示层用 float 则 Level 降为 Medium |
| Q7 | 转账是否有收款方确认环节？还是发起即到账？ | R8 | 根据需求模型"实时到账"假设发起即到账，无收款方确认；若有确认环节则状态流转需增加"待确认"状态 |
| Q8 | 是否有历史 Bug 数据可供 Likelihood 校准？ | 全部 | 当前 Likelihood 基于代码证据估计，无历史缺陷密度输入 |