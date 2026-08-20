# 余额转账测试策略

> 本策略回答"余额转账功能应该怎么测"。基于需求模型摘要（E1）与代码走读要点（E2）识别风险，按 `core/risk-model.md` 评级，翻译为范围/深度/优先级要求。不含具体用例（→ `test-case-writing`）。

---

## Risk Map

> 评级规则：Risk Score = Impact × Likelihood（各 1–5）；Critical 20–25 / High 10–19 / Medium 4–9 / Low 1–3。每条风险强制带 evidence（level + source）与 confidence，无证据评级无效。

```yaml
risks:

  - id: R1
    feature: 余额转账
    dimension: 数据一致性
    title: 三步转账无分布式事务，任一步失败靠补偿回滚
    impact: 5                      # 中间步骤失败导致发起方已扣款但收款方未到账 = 资损
    likelihood: 3                  # 风控服务/加余额调用常规路径可能失败；补偿逻辑是否覆盖全部分支未验证
    level: High                    # 15 = 5 × 3
    evidence:
      level: E2
      source: transfer_service.py（编排：扣余额 -> 调风控 -> 加余额，无分布式事务，靠补偿回滚）
    confidence: high
    status: needs_verification     # 补偿逻辑实际分支覆盖待实测确认
    anchors: []                    # 派生索引，由 test-case-writing 的 case.risk_ref 抽取再生

  - id: R2
    feature: 余额转账
    dimension: 边界
    title: 金额中间计算用 float，仅入库前转 Decimal，存在精度漂移
    impact: 4                      # 精度误差累积导致账实不符
    likelihood: 4                  # 金额计算为常规路径，每次转账都经过
    level: High                    # 16 = 4 × 4
    evidence:
      level: E2
      source: transfer_service.py（金额 float 中间计算，入库前转 Decimal）
    confidence: high
    status: needs_verification

  - id: R3
    feature: 余额转账
    dimension: 并发
    title: 转账请求无幂等键，网络重试产生重复转账单
    impact: 5                      # 重复扣款/重复到账 = 直接资损
    likelihood: 4                  # 移动端弱网重试为常规场景
    level: Critical                # 20 = 5 × 4
    evidence:
      level: E2
      source: 转账请求层（无幂等键设计）
    confidence: high
    status: needs_verification

  - id: R4
    feature: 余额转账
    dimension: 数据一致性
    title: 转账单号时间戳+随机数生成，无唯一约束，高并发下可能碰撞
    impact: 4                      # 单号碰撞导致单据混淆/对账错乱
    likelihood: 2                  # 需高并发+同毫秒随机碰撞，极端条件
    level: Medium                  # 8 = 4 × 2
    evidence:
      level: E2
      source: 应用层转账单号生成逻辑（时间戳+随机数，无唯一约束）
    confidence: medium
    status: needs_verification

  - id: R5
    feature: 余额转账
    dimension: 边界
    title: 日累计校验读本地缓存（30 秒刷新），短窗口内可绕过日累计限额
    impact: 5                      # 绕过日累计限额 = 资损+合规风险
    likelihood: 4                  # 30 秒窗口常规可利用，无需极端条件
    level: Critical                # 20 = 5 × 4
    evidence:
      level: E2
      source: 日累计校验逻辑（本地缓存 30 秒刷新）
    confidence: high
    status: needs_verification

  - id: R6
    feature: 余额转账
    dimension: 状态流转
    title: 风控回调超时 10 分钟自动放行，大额本应审核却放行
    impact: 5                      # 大额未审核到账 = 风控失效+资损
    likelihood: 3                  # 回调超时为可发生场景（风控服务延迟/网络抖动）
    level: High                    # 15 = 5 × 3
    evidence:
      level: E2
      source: 风控异步回调逻辑（超时 10 分钟自动放行）
    confidence: high
    status: needs_verification

  - id: R7
    feature: 余额转账
    dimension: 边界
    title: 限额与字段长度边界（单笔≤5000、日累计≤20000、2 位小数、备注≤50 字）
    impact: 3                      # 边界绕过导致小额资损或体验问题
    likelihood: 3                  # 边界值为常规测试触发点
    level: Medium                  # 9 = 3 × 3
    evidence:
      level: E1
      source: 需求模型摘要（规则章节）
    confidence: high
    status: fact

  - id: R8
    feature: 余额转账
    dimension: 状态流转
    title: 转账单状态机非法转换（如审核中直接置成功、失败后再次发起）
    impact: 3                      # 状态错乱导致资金状态不可追溯
    likelihood: 2                  # 需构造非法请求或并发操作
    level: Medium                  # 6 = 3 × 2
    evidence:
      level: E1
      source: 需求模型摘要（状态章节：发起 -> 风控审核/直接成功 -> 成功/失败）
    confidence: medium
    status: needs_verification

  - id: R9
    feature: 余额转账
    dimension: 并发
    title: 余额扣减无锁描述，并发转账可能绕过余额不足拦截
    impact: 5                      # 余额透支 = 资损
    likelihood: 3                  # 同账户并发转账可触发
    level: High                    # 15 = 5 × 3
    evidence:
      level: E2
      source: transfer_service.py（先扣发起方余额，无显式锁/版本号描述）
    confidence: medium             # 代码走读要点未明确锁机制，需进一步确认
    status: needs_verification

  - id: R10
    feature: 余额转账
    dimension: 权限
    title: 普通用户越权操作他人账户转账
    impact: 4                      # 越权转账 = 资损+安全
    likelihood: 2                  # 需构造越权请求
    level: Medium                  # 8 = 4 × 2
    evidence:
      level: E1
      source: 需求模型摘要（角色章节：普通用户/风控）
    confidence: low                # 代码走读未涉及鉴权层，需确认
    status: needs_verification
```

**Risk Map 汇总**

| ID | 维度 | 等级 | Score | 关键证据 |
|----|------|------|-------|---------|
| R3 | 并发 | Critical | 20 | 无幂等键，重试重复转账（E2） |
| R5 | 边界 | Critical | 20 | 日累计缓存 30s 刷新可绕过（E2） |
| R1 | 数据一致性 | High | 15 | 三步无分布式事务靠补偿（E2） |
| R2 | 边界 | High | 16 | float 中间计算精度漂移（E2） |
| R6 | 状态流转 | High | 15 | 风控回调超时自动放行（E2） |
| R9 | 并发 | High | 15 | 余额扣减无锁描述（E2） |
| R7 | 边界 | Medium | 9 | 限额/字段长度边界（E1） |
| R4 | 数据一致性 | Medium | 8 | 单号无唯一约束（E2） |
| R10 | 权限 | Medium | 8 | 越权操作（E1） |
| R8 | 状态流转 | Medium | 6 | 状态机非法转换（E1） |

---

## 测试策略

```yaml
test_strategy:
  feature: 余额转账（站内用户间实时转账，含大额风控审核）

  scope:

    functional:
      include: true
      depth: full
      rationale: >
        核心资损路径。R1（三步无事务）、R6（风控超时放行）、R8（状态机）均落在主功能链路上，
        按 testing-principles.md「复杂业务流程 -> Workflow」方法覆盖：端到端主链 + 每环节失败分支 +
        中断恢复 + 多轮累积。主链每一步必须有用例，失败分支按补偿回滚逐路径覆盖。

    boundary:
      include: true
      depth: full
      rationale: >
        R5（日累计缓存绕过，Critical）、R2（float 精度，High）、R7（限额与字段长度，Medium）均在此维度。
        按「输入输出型 -> 等价类 + 边界值」方法逐条规则全覆盖：单笔限额（4999.99/5000/5000.01）、
        日累计（19999.99/20000/20000.01）、金额精度（2 位小数边界 + float 漂移构造）、
        备注（0/50/51 字）。日累计缓存窗口须专项构造 30 秒内连续转账验证绕过。

    permission:
      include: true
      depth: standard
      rationale: >
        R10（越权，Medium）。按「权限系统 -> Role × Action × Resource」方法做主干 + 资源级隔离：
        A 用户不可对 B 用户账户发起转账、不可查询/操作他人转账单。深度 standard 因需求未展开
        细粒度角色体系，且代码走读未涉及鉴权层（confidence: low，已列入待澄清）。

    regression:
      include: true
      depth: standard
      rationale: >
        本功能为新增，历史 Bug 暂缺。回归深度 standard：以 Critical/High 风险锚点用例为核心，
        接口变更时扩展到接口用例全量。待上线后按历史缺陷密度动态调整（risk-model.md 第 2 节）。

    compatibility:
      include: true
      depth: light
      rationale: >
        后端编排型功能，兼容性主要在消息通知触达端（不同客户端推送兼容）。light 抽样冒烟即可。

    performance:
      include: false
      handoff: "专项：k6 -- 并发扣减压测（R9 余额透支）、风控回调延迟场景、30 秒缓存窗口并发吞吐"
      rationale: >
        R9（并发余额扣减）与 R5（缓存窗口）的性能边界需压测定量，不在本框架自研范围。
        性能维度移交 k6 专项，本策略在 Risk Map 中保留入口，测试报告预留压测结果挂载位。

    security:
      include: false
      handoff: "专项：安全审计 -- 越权（R10）、重放攻击（R3 幂等缺失）、风控绕过（R6 超时放行）"
      rationale: >
        R3/R6/R10 含安全属性，但深度安全审计（重放、越权自动化扫描、风控规则逆向）移交安全专项。
        本策略在 functional/boundary/permission 维度覆盖功能层面表现，安全维度不静默缺失，显式 handoff。

  risk_map_ref: "本文档 Risk Map 章节（R1–R10）"

  risk_to_priority_mapping:
    rule: "按 risk-model.md 第 3 节默认映射"
    Critical:
      - R3 -> 必须有 P0 用例，且作为回归锚点
      - R5 -> 必须有 P0 用例，且作为回归锚点
    High:
      - R1 -> P0 或 P1
      - R2 -> P0 或 P1
      - R6 -> P0 或 P1
      - R9 -> P0 或 P1
    Medium:
      - R4 -> P1
      - R7 -> P1
      - R8 -> P1
      - R10 -> P1
    Low: []
    deviation_notes: "无偏离。R9 confidence 为 medium，若澄清确认存在乐观锁则降级为 Medium/P1，届时更新本映射。"

  automation_plan:
    status: proposal
    await_confirmation: true
    proposed_automated:
      - item: "幂等性验证（R3）-- 重复请求/网络重试场景"
        framework: "api-testing（API 脚本）"
        reason: "接口级校验，需精确控制请求时序与重放，无 UI 依赖"
      - item: "日累计缓存绕过（R5）-- 30 秒窗口内连续转账"
        framework: "api-testing（API 脚本）"
        reason: "需精确时序控制与并发请求编排"
      - item: "并发余额扣减（R9）-- 同账户并发转账"
        framework: "api-testing（API 脚本） + k6（压测定量）"
        reason: "接口级并发，API 脚本验证透支逻辑，k6 量化吞吐边界"
      - item: "限额与精度边界（R2/R7）-- 参数化边界值"
        framework: "api-testing（API 脚本，参数化）"
        reason: "等价类+边界值用例量大但结构化，适合参数化自动化"
      - item: "状态机非法转换（R8）-- 非法状态请求"
        framework: "api-testing（API 脚本）"
        reason: "接口级状态校验，可枚举自动化"
    proposed_manual:
      - item: "补偿回滚全路径验证（R1）-- 三步各点注入失败"
        framework: "手动 + 故障注入"
        reason: "需在特定步骤注入失败（mock 风控超时/加余额异常）并观察补偿，探索性强，一次性验证为主"
      - item: "风控回调超时放行（R6）-- 10 分钟超时路径"
        framework: "手动（可辅助 API 脚本触发）"
        reason: "等待时间长，适合一次性回归验证；每次回归手动执行"
      - item: "大额风控审核全流程（功能主链）"
        framework: "手动"
        reason: "涉及风控异步回调与人工审核环节，端到端链路长，探索性空间大"
    not_automated:
      - item: "消息通知触达（兼容性 light）"
        reason: "依赖客户端环境，自动化 ROI 低，手动冒烟"
    note: >
      本计划为提案，⏸ 等用户确认。确认前不启动执行类 skill。
      转账为后端编排型功能，无独立 UI，建议以 API 脚本为主、E2E 为辅（若有前端转账页面再评估 Playwright）。

  regression_plan:
    anchors:
      - risk_ref: R3
        description: "重复转账拦截（幂等性）-- 每次必跑"
        priority: P0
      - risk_ref: R5
        description: "日累计限额绕过（30 秒缓存窗口）-- 每次必跑"
        priority: P0
      - risk_ref: R1
        description: "三步转账补偿回滚（中间步骤失败）-- 每次必跑"
        priority: P0
      - risk_ref: R9
        description: "并发转账余额透支拦截 -- 每次必跑"
        priority: P0
    expansion_rules:
      - trigger: "transfer_service.py 编排逻辑变更（扣款/风控/加余额任一步）"
        action: "R1 补偿回滚全路径用例全量回归"
      - trigger: "接口签名/参数变更"
        action: "接口用例全量回归（api-testing 脚本）"
      - trigger: "限额规则或日累计逻辑变更"
        action: "boundary 维度全量回归（R5/R7）"
      - trigger: "风控回调机制变更"
        action: "R6 超时放行 + 正常审核全流程回归"
      - trigger: "余额服务/风控服务依赖升级"
        action: "锚点用例 + 失败分支用例回归"
    cadence: "每次提测必跑锚点集；版本回归按 expansion_rules 扩展；上线后首个版本全量回归一次建立基线"
```

---

## 二阶交叉覆盖要求（交付给 test-case-writing 的重点提示）

依据 `testing-principles.md` 第 3 节，以下交叉点为本功能高发薄弱区，用例设计阶段必须覆盖：

1. **写入路径 × 校验规则**：单笔限额、日累计限额、余额不足拦截、备注长度校验--在「正常发起」「网络重试重新发起」「风控驳回后重新提交」**每条写入路径**上是否都生效（校验常只挂首发起路径）。
2. **失败 × 重试**：三步转账任一步失败（扣款失败/风控调用失败/加余额失败）-> 补偿回滚 -> 重新发起能否恢复正常；风控回调超时 -> 放行后状态是否正确。
3. **标识 × 重复**：转账单号（时间戳+随机数）重复提交时的唯一性行为；同一发起方对同一收款方短时间多次转账的去重/拦截行为（与 R3 幂等关联）。

---

## 待澄清清单

> 以下问题影响风险评级与策略深度，未阻塞策略产出，但需在用例设计前澄清。证据等级为 E0（用户陈述）或待补 E2。

| # | 问题 | 影响范围 | 当前假设 |
|---|------|---------|---------|
| Q1 | 余额扣减是否有乐观锁/悲观锁/版本号机制？ | R9 评级（High -> 可能 Medium） | 代码走读未提及，暂按无锁假设评级 High |
| Q2 | 补偿回滚逻辑具体覆盖哪些失败分支？是否有最大重试次数/兜底告警？ | R1 用例深度 | 暂按"每个中间步骤失败均需验证补偿"设计 |
| Q3 | 风控回调超时自动放行是否为产品确认的预期行为（而非缺陷）？ | R6 评级与处置 | 暂按风险处理，待产品确认是否为有意的容错策略 |
| Q4 | 转账请求是否计划增加幂等键（如客户端生成的 request_id）？ | R3 根因修复方向 | 当前无，策略按"无幂等键"设计用例 |
| Q5 | 日累计缓存是否有兜底的权威数据源校验（如缓存失效后回查 DB）？ | R5 绕过严重程度 | 暂按纯缓存校验假设，30 秒窗口可绕过 |
| Q6 | 转账单号是否计划加数据库唯一约束？ | R4 评级（Medium -> 可能 Low） | 当前无唯一约束 |
| Q7 | 鉴权层如何校验"只能操作自己账户"？是否有资源级隔离？ | R10 深度 | confidence: low，待确认鉴权实现 |
| Q8 | 是否有前端转账 UI 页面（决定是否需 Playwright E2E）？ | automation_plan 框架选择 | 暂按后端编排型功能处理，以 API 脚本为主 |

---

## 下游索引（交付 test-case-writing）

> **策略路径**：`{项目}/测试策略.md`
> **必测维度**：functional（full）、boundary（full）、permission（standard）、regression（standard）、compatibility（light）
> **优先级映射要求**：R3/R5 → P0 锚点；R1/R2/R6/R9 → P0 或 P1；R4/R7/R8/R10 → P1。每条用例 `risk_ref` 必须回指 R1–R10 中至少一条。
> **二阶交叉**：写入路径×校验、失败×重试、标识×重复三组必须有用例覆盖。