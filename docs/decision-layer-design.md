# 精准测试决策层设计稿：测试类型决策矩阵 + 深度校准

> **文档状态**：v1（2026-08-23）。文中 `eval/` 引用（运行归档、标注工具等）属**本地维护的评测链路**，不随公开仓库分发。**Phase A 已实施**（矩阵 `core/test-type-matrix.md`、扫描器 `core/scripts/scan_signals.py`、校验器 V1–V5、test-strategy 重写及 §6 全部同步改写，validate_skills 全绿，dogfood 链路验证通过）。**Phase B 前两轮完成**：GT 双人复核（GLM-5.2 独立标注，决策一致 40/45）→ 最弱模型首轮（Off 臂宽容口径亦为**零显式决策**——盲区在决策纪律不在类型知识；On 严格 0.533）→ **R1 格式锤复验**（格式失败归零，查全 0.880，纯代码信号轴 8/9）；glm-5.2 梯度轮见 `eval/results/runs/`。开放问题状态见 §10。
>
> **与既有文档的关系**：
> - 实现方向来自框架愿景——「知识 × 工具 × 决策」三层，**决策层是一等公民**（知识与工具是供给，决策是把供给变成专家性的调度器）
> - **取代** `qa-skills-v2.md` §6.3（性能/安全不自研、仅作集成点）：升级为「方法论与决策自研，执行层对接专业工具」
> - **扩展** v2 §7.3 Test Strategy Schema（scope 从 5+2 固定轴 → 功能域 + 类型域全轴必答）
> - 依赖并复用现有资产：`core/risk-model.md`（评级挂证据）、`core/evidence.md`（E0–E4）、`core/testing-principles.md`（方法选择）、`core/scripts/validate_schema.py`（校验器）

---

## 0. 摘要

给 AI 装上测试专家的**类型决策力**：面对任何需求 + 代码，产出一份**全类型可审计的测试范围决策**——每个测试类型要么纳入（挂证据、定深度），要么排除（挂理由、留痕），要么移交（挂接收方、带输入包）。不漏测靠「全轴必答」，不浪费靠「include 必须挂信号 + full 有预算上限」。决策质量本身可评测（客观判指标，无需 LLM judge）。

**头条价值主张：弱模型增益**——把类型视野从模型能力变成框架能力。弱模型 Off 侧的系统性缺陷是类型盲区（只测 PRD 写到的，看不见代码里有信号、需求里没文案的轴），这正是类别性质变（0.2→0.98 型）发生的位置；机制见 §5.4，验证假设见 §7.2。

一句话：**专家性不是"什么测试都会做"，而是"每个类型都进过决策、每个决策都有证据、不做的留痕、做的交给最合适的执行者"。**

---

## 1. 动机与原则

### 1.1 为什么决策层是一等公民

已有实验证据（eval 单文件消融）：只提供核心标准文档（纯知识）**不改变模型行为**；0.26→0.98 的用例规格增益来自「工作流 + 决策纪律」。结论：知识不装进决策流程就是噪音——本设计就是把"测试类型的取舍"从模型自由发挥，变成显式的、可校验的决策流程。

### 1.2 现状的两个机制性缺陷（本设计要消灭的）

| # | 缺陷 | 机制性来源 | 本设计的解法 |
|---|------|-----------|-------------|
| 1 | **漏测**：可靠性、a11y、i18n、迁移、契约等类型不在决策空间里——不是被排除，而是从未被考虑，策略文档无痕迹、无从挑战 | scope schema 只有 5 个实质轴 + 2 个 handoff 轴（compatibility 在 5 轴之中，本设计迁入矩阵） | 全轴必答（§5.2 V1），排除必须留痕 |
| 2 | **浪费**：include 不需要证据支撑，模型可以生成样样 full 的"安全策略" | rationale 是建议句式，无校验 | include 挂信号 / full 挂风险等级 / full 有预算上限（§5.2 V2–V4） |

### 1.3 设计原则（六条硬规则）

1. **全轴必答**：类型域每个轴必须在策略中出现且带决策（include / exclude / handoff 三选一），缺轴不过校验
2. **include 挂信号**：纳入必须有需求级或代码级信号（或风险编号）支撑；无信号的纳入 = 过测
3. **exclude 挂理由**：排除必须引用扫描结果（哪些信号查过、均未命中）；无理由的排除 = 漏测
4. **depth 与 execution 分离**：深度档位表达"应该测多深"（应然），执行状态表达"现在能做多少"（实然）——环境缺位记 TODO 索取，**不得**把"做不了"悄悄记成"不用测"
5. **单一真相**：类型决策的唯一来源是 `core/test-type-matrix.md`；coverage.md 中的类型性维度、risk-model 的维度枚举一律改为引用矩阵，消灭多头真相
6. **弱模型优先**：默认形态按最弱模型设计（脚本外包、预填修订、分轴组推进、受限选择，§5.4）；强模型不损失正确性、只多花 token——宁可放弃为强模型优化的优雅，不赌弱模型的遵循

---

## 2. 决策矩阵总览

### 2.1 两域结构与显式变更（delta）

```text
测试策略 scope
├── 功能域（显式变更：+2 轴、迁出 1 轴）
│   现有 4 轴保留：functional / boundary / permission / regression
│   新增 2 轴：state / data_consistency（自 coverage.md 维度升格，与风险维度对齐）
│   迁出 1 轴：compatibility → 矩阵轴 5
│   —— 功能域几乎总是 include，差异在深度；沿用「范围 + 深度 + 理由」机制
└── 类型域（本设计新增，矩阵管辖，10 轴全轴必答）
    性能效率 / 业务安全 / 可靠性 / 并发一致性 / 兼容性 /
    无障碍 / 视觉一致性 / 国际化 / 迁移与升级 / 契约与集成
```

performance / security 从 handoff 占位升级为矩阵正式轴。功能域的 schema 变更同入 §6 同步改写清单——**"现状保留"不是事实，显式 delta 才是**。

**域间裁决规则**（重叠必裁决；先例：轴 4 与轴 1 的并发 / 性能裁决）：

| 重叠 | 裁决 |
|---|---|
| permission（功能域）× 业务安全（轴 2） | **permission 管授权功能的正确性**——有权限的人行为对不对，越权用例由它产出；**业务安全管未授权视角的防御**——不该拿的人拿不拿得到、敏感数据漏不漏、注入面、认证会话。permission 轴 depth ≥ standard 是业务安全轴的内部纳入信号；同一批越权用例不得两轴双计数 |

### 2.2 ISO/IEC 25010:2023 映射（对外合法性）

| 矩阵轴 | ISO 25010 特性 |
|---|---|
| 性能效率 | Performance Efficiency |
| 业务安全 | Security（业务子集；渗透/SAST 显式出界） |
| 可靠性 | Reliability |
| 并发一致性 | Reliability × Functional 交叉（正确性归并发轴，容量/延迟归性能轴） |
| 兼容性 | Compatibility（co-existence / interoperability） |
| 无障碍 / 视觉一致性 | Interaction Capability |
| 国际化 | Interaction Capability × Flexibility |
| 迁移与升级 | Flexibility（adaptability / replaceability） |
| 契约与集成 | Compatibility（interoperability） |

Functional Suitability 由功能域覆盖；Maintainability / Safety 不设轴（理由见 2.3）。

### 2.3 考虑过但不设轴的类型（排除也要留痕——矩阵自身遵守自己的原则）

| 类型 | 不设轴理由 | 出路 |
|---|---|---|
| 可用性 / UX 主观体验 | 主观判定，LLM judge 与自动指标均不可靠 | 右移（A/B、用户反馈）或人工评审 |
| 渗透测试 | 需授权与专业工具链，且属攻防而非 QA 职责 | 业务安全轴 handoff 出口之一 |
| SAST / 依赖扫描 | 开发侧工具（CI 集成），非测试决策 | 契约与集成轴的信号来源之一，不做执行 |
| 维护性 / 安全性(产品内嵌) | 开发工程属性，QA 不可执行验证 | 不覆盖 |
| 单元 / 组件级测试 | 这是**级别**决策不是**类型**决策 | 级别路由另案（§10 开放问题 5） |

---

## 3. 十轴详设

> 每轴统一六字段：需求信号 / 代码信号 / 默认档 / 档位语义（full·standard·light 各自的具体动作，即该轴的停止准则）/ 执行归属 / 成本因子。
> **代码信号分两级**（方案 B 已裁决，2026-08-23）：**G 级**（greppable）由 `core/scripts/scan_signals.py` 按每轴模式清单机械扫描，产出文件:行 级信号 + 默认档预填表——同代码必得同 G 级信号；**S 级**（semantic，信号清单中以〔S〕标注）是脚本抓不住的语义模式，由 agent 按固定清单复核。**R4 的"扫描全灭"必须 G + S 双确认**——S 级未复核不得作为 exclude 依据，否则脚本盲区会被制度化为漏测。这是"通过代码分析决定测什么"的落地形态，也是弱模型增益的第一机制（§5.4）。
>
> **默认档分软硬**：软默认轴可经 R4 降档至 exclude；硬默认轴（仅轴 2 业务安全）无 R4 出口。**矩阵文件按轴独立成节**，文首设组索引（§5.4 三轴组 → 小节锚点）——分轴组推进时只加载本组小节，300 行矩阵不整文件进上下文。

### 轴 1 性能效率（performance）

- **需求信号**：SLA / P95 响应时间承诺；大促、秒杀、抢购场景；预计并发用户数；性能验收指标
- **代码信号**：无分页全量查询；循环内远程调用（N+1）〔S〕；缓存依赖（Redis 命中率假设）；锁竞争热点〔S〕；消息积压消费逻辑
- **默认档**：无信号 exclude（记录扫描结果）；有 SLA 或容量信号 → include
- **档位语义**：full = 压测模型设计（用户旅程 × 到达率阶梯）+ 执行 + 瓶颈归因报告；standard = 核心接口基准（单接口阶梯加压）+ 阈值判定；light = 代码级性能审查（分页 / 缓存 / N+1 / 锁，逐项出 E2 证据清单）
- **执行归属**：模型设计与脚本生成 = agent；压测执行 = k6（handoff 协议，§5.3）；light 全 agent
- **成本因子**：独立压测环境、可重置数据、基准噪音控制

### 轴 2 业务安全（security-business）

- **需求信号**：多角色 / 权限层级；隐私数据（手机号 / 身份证 / 地址）；资金操作；合规要求（个保法 / GDPR）；**内部信号**：功能域 permission 轴 depth ≥ standard
- **代码信号**：鉴权中间件覆盖面缺口〔S〕；对象级授权缺失模式〔S〕（user_id 来自请求参数而非会话）；可枚举 ID 直接引用；敏感字段明文返回或落日志；SQL 拼接
- **默认档**：Web / API 系统**一律 standard**——**硬默认，无 R4 exclude 出口**（成本极低 × 价值极高，这是专家的默认直觉；除本轴外其余九轴均为软默认）
- **档位语义**：full = 未授权视角全矩阵（匿名 + 低权角色对全部高危资源的可达性探测）+ 敏感数据流追踪 + 注入面；standard = 高危资源越权抽样 + 注入面 / 敏感暴露扫描；light = 设计层审查（Cx 记录）。**越权功能正确性用例归功能域 permission 轴产出**（裁决见 §2.1），本轴不重复产
- **执行归属**：agent（复用 API 测试基建与测试账号矩阵）
- **成本因子**：低——测试账号矩阵是唯一前置

### 轴 3 可靠性（reliability）

- **需求信号**：可用性承诺（9x%）；降级预案；容灾要求；"不能丢消息"类硬约束
- **代码信号**：重试逻辑与重试上限；超时配置；消息队列消费与 ack；断路器；事务边界〔S〕；补偿 / 回滚逻辑
- **默认档**：有异步 / 第三方依赖信号 → standard；无 → light
- **档位语义**：full = 故障注入矩阵（依赖宕机 / 超时 / 拒绝 / 脏数据）+ 恢复验证；standard = 超时 / 重试 / 幂等 / 降级专项用例（现有"失败 → 重试 → 恢复"原则的类型化落地）；light = 清单审查（超时有无 / 重试上限 / 幂等键 / 消息 ack 语义）
- **执行归属**：standard 及以下 = agent；故障注入 = agent 设计 + 可控环境执行
- **成本因子**：故障注入需可控环境；standard 无特殊成本

### 轴 4 并发一致性（concurrency）

- **需求信号**：库存 / 名额 / 配额；抢购；"全局唯一"类约束；多人同时编辑
- **代码信号**：check-then-write 模式（先查后写无锁）〔S〕；共享可变状态〔S〕；扣减逻辑；依赖唯一约束兜底的写入路径
- **默认档**：有共享可变资源信号 → standard；无 → light
- **档位语义**：full = 竞争窗口分析 + 并发用例矩阵（同一资源 × 全部竞争写入路径）+ 真实并发执行；standard = 关键竞争点并发用例（衔接 api-testing 并发能力）；light = 竞态模式代码审查
- **执行归属**：agent
- **成本因子**：可重置数据
- **与性能轴的裁决**：正确性 bug（超卖 / 重复）归本轴，容量 / 延迟归性能轴；同一次并发执行可同时给两轴供 E3 证据（执行复用，决策分离）

### 轴 5 兼容性（compatibility）

- **需求信号**：明确支持的浏览器 / 设备清单；企业客户旧环境（旧内核）；跨端一致性要求
- **代码信号**：浏览器特性 API 使用（IntersectionObserver 等）；UA 判断分支；响应式断点；CSS 特性依赖
- **默认档**：有前端 → light；有明确支持清单 → standard
- **档位语义**：full = 支持矩阵逐格（浏览器 × 设备 × 分辨率 × P0 路径）；standard = 支持清单矩阵 × P0 路径；light = 最新 Chrome / Safari / Edge / Firefox 冒烟
- **执行归属**：agent + Playwright 项目矩阵
- **成本因子**：多浏览器 CI runner；真机（移动端超出 v1 范围）

### 轴 6 无障碍（accessibility）

- **需求信号**：政企 / 教育政务客户；无障碍合规要求；投标条款
- **代码信号**：有前端即最低信号（语义化标签缺失、img 无 alt、键盘不可达、表单无 label）
- **默认档**：有前端 → light
- **档位语义**：full = WCAG 2.2 AA 逐页审计 + 键盘全路径 + 读屏抽样（读屏归人工）；standard = axe 全页扫描 + 违规分级 + 关键流键盘走查；light = axe 扫描 P0 页面
- **执行归属**：agent + axe-core（Playwright 集成，一条命令接入）
- **成本因子**：极低
- **边界**：主观判定类（对比度阈值争议、读屏体验）标记人工复核，agent 只出客观违规清单

### 轴 7 视觉一致性（visual）

- **需求信号**：品牌规范验收；设计稿交付（Figma）；视觉回归要求
- **代码信号**：有前端即信号
- **默认档**：有前端 → light
- **档位语义**：full = 全页面截图基线 + 逐变更 diff；standard = 关键页基线 + diff；light = P0 页面截图存档供人比对（不自动判）
- **执行归属**：agent + Playwright screenshot
- **成本因子**：低；基线维护与动态内容遮罩规则（时间 / 头像 / 随机推荐位）是主要复杂度
- **防 flaky 硬约束**：自动 diff 必须先声明遮罩规则，未声明遮罩的 diff 失败不判 Bug

### 轴 8 国际化（i18n）

- **需求信号**：海外 / 多语言市场；RTL 语言；跨时区用户群；本地化交付
- **代码信号**：i18n bundle / locale 目录；日期货币格式化库；硬编码文案（扫描前端源码字符串）；时区处理逻辑
- **默认档**：无信号 exclude（记录扫描结果）；有信号 → standard
- **档位语义**：full = 伪本地化全量 + RTL 布局走查 + 格式矩阵（日期 / 货币 / 电话 / 时区 / 复数规则）；standard = 目标语言集核心流 + 格式抽样；light = 硬编码文案扫描 + 代表性页面伪本地化
- **执行归属**：agent
- **成本因子**：翻译数据依赖（伪本地化不依赖）

### 轴 9 迁移与升级（migration）

- **需求信号**：存量系统迭代；数据结构变更公告；灰度共存 / 版本升级
- **代码信号**：DB migration 文件；数据回填脚本；双写逻辑〔S〕；API 多版本共存
- **默认档**：有 migration 文件 → standard；无 → light（存量系统）/ exclude（绿地项目，记录判断依据）
- **档位语义**：full = 升级路径矩阵（版本 × 数据形态）+ 回滚验证 + 新旧数据共存探测；standard = 代表性升级用例 + 回滚一例；light = migration 脚本审查（可回滚性 / 兼容性 / 回填幂等）
- **执行归属**：agent
- **成本因子**：可重置的存量数据快照

### 轴 10 契约与集成（contract-integration）

- **需求信号**：第三方依赖清单；对外 API 的消费方；微服务边界；webhook
- **代码信号**：外部 HTTP / gRPC 调用；消息契约；OpenAPI 定义变更；回调处理
- **默认档**：有外部依赖 → standard；无 → exclude（记录扫描结果）
- **档位语义**：full = 消费者驱动契约（Pact 式）+ 依赖故障矩阵（超时 / 错误码 / 格式变化 / 限流）；standard = 关键依赖 mock 与真实双跑 + 异常分支用例；light = 调用面清单 + 错误处理审查
- **执行归属**：agent；契约测试框架执行为 handoff 候选
- **成本因子**：mock / 沙箱可用性

---

## 4. 深度校准与停止准则

### 4.1 升降档规则（跨轴通用；唯一声明的冲突裁决：R6 > R1，被裁 Critical 轴走预算裁决检查点）

| 规则 | 触发条件 | 动作 |
|---|---|---|
| R1 风险升档 | 该轴覆盖的场景上挂 Critical 风险 → full；High → 至少 standard | 升档，rationale 挂风险编号 |
| R2 双源信号 | 同轴命中 ≥2 类独立信号（需求级 + 代码级） | 升一档 |
| R3 历史缺陷 | 该轴维度历史 Bug ≥3 或出过线上事故 | 升一档（与 Regression-focused 方法同构） |
| R4 无信号降档 | 需求 + 代码信号扫描全灭（**G 级脚本输出 + S 级 agent 复核双确认**；硬默认轴无此出口） | 可降至 exclude；**G + S 双清单必须落盘**（这就是 exclude 的理由） |
| R5 成本门 | 执行前提（环境 / 数据 / 工具）不可得 | **执行降级不决策降级**：档位保持，execution_status 记 blocked + TODO 向谁索取（原则 4） |
| R6 预算约束 | full 轴数 > 3（**两域合并计**） | 强制按风险排序裁剪至 ≤3，被裁轴降 standard 并记录排序依据——**样样 full = 无重点 = 浪费**。**与 R1 冲突时 R6 优先**；被裁剪的 Critical 轴触发**预算裁决检查点**（qa 第四类人工检查点，用户可扩预算） |

R6 是"不浪费人力物力"的机制化：资源永远有限，专家的判断力体现在被迫取舍时的排序，排序过程留痕、可被挑战。

### 4.2 depth 与 execution_status 分离（schema 层落地）

```yaml
performance:
  decision: include
  depth: full                  # 应然：应该测多深（R1：R3 风险 Critical）
  execution_status: blocked    # 实然：独立压测环境缺位
  blocked_reason: "压测环境未提供"
  todo: "向运维索取独立压测环境与可重置数据集"
```

**execution_status 枚举**：`ready`（前提齐备）/ `blocked`（缺前提，必带 todo）/ `done`（档位动作已执行完）；exclude 轴省略此字段。

策略评审时两列分开审：depth 审"判断对不对"，execution_status 审"前提拿到了没有"。环境到位后 depth 不变、status 转 ready——不需要重新决策。

### 4.3 停止准则

每个轴的**档位语义本身就是停止准则**：full / standard / light 各自的动作清单（§3 每轴已写死）勾完即停。策略落盘时生成「足够性声明」：逐轴列出档位动作清单与完成状态。禁止"再测测看"式的开放式深挖——想加深必须升档并说明触发了哪条 R 规则。

---

## 5. Schema 与校验

### 5.1 新 scope 结构（v2 §7.3 的扩展）

```yaml
test_strategy:
  functional_scope:            # 功能域：沿用现有轴与「范围+深度+理由」机制
    functional:  { include: true, depth: full,  rationale: "..." }
    boundary:    { include: true, depth: standard }
    permission:  { include: true, depth: full,  rationale: "R2 High" }
    state:       { include: true, depth: standard }
    data_consistency: { include: true, depth: standard }
    regression:  { include: true, depth: standard }
  type_scope:                  # 类型域：十轴全轴必答
    performance:    { decision: include,  depth: full,     signals: [PRD-4.2, order_service.go:88], risk_refs: [R3], executor: k6,      execution_status: blocked, ... }
    security_business: { decision: include, depth: standard, signals: [多角色], executor: agent,   execution_status: ready }
    reliability:    { decision: include,  depth: standard, signals: [queue/retry], executor: agent, execution_status: ready }
    concurrency:    { decision: include,  depth: standard, signals: [库存扣减, check-then-write:cart_service.go:41], executor: agent, execution_status: ready }
    compatibility:  { decision: include,  depth: light,    signals: [有前端], executor: agent,     execution_status: ready }
    accessibility:  { decision: include,  depth: light,    signals: [有前端], executor: agent,     execution_status: ready }
    visual:         { decision: include,  depth: light,    signals: [有前端], executor: agent,     execution_status: ready }
    i18n:           { decision: exclude,  rationale: "需求级信号（海外/多语言/RTL）未命中；代码扫描无 i18n bundle、无硬编码外文文案", scanned: [需求信号(G), i18n目录(G), 格式化库(G), 硬编码文案复核(S)] }
    migration:      { decision: include,  depth: standard, signals: [migrations/2026-08-x*.sql], executor: agent, execution_status: ready }
    contract_integration: { decision: include, depth: standard, signals: [外部支付依赖], executor: agent, execution_status: ready }
  depth_budget:                # R6 落地：full 轴清单 ≤3，按风险排序
    full_axes: [functional, permission, performance]
    ranking_rationale: "R3(资损 Critical) > R2(越权 High) > ..."
```

**执行归属三态**（decision × executor 的语义边界）：`include + executor=agent` = 框架内闭环；`include + executor=外部工具`（如 k6）= 框架产出设计与脚本、工具执行、结果经回收格式回流报告（同受 V5 移交包约束）；`handoff` = 整轴出框架——不产用例 / 脚本，只产移交包与回收格式。**depth_budget 与 V4 横跨两域**：功能域 full 轴计入预算并同样强制挂风险编号——这是现有 rationale 纪律的升格，不是新增负担。

### 5.2 校验规则（validate_schema.py 扩展，全部机械可判）

| # | 规则 | 消灭什么 |
|---|---|---|
| V1 | 类型域十轴全部存在，每轴 decision ∈ {include, exclude, handoff} | 漏测（静默缺失） |
| V2 | include 轴必须有非空 signals（引用 PRD 章节 / 文件:行）或 risk_refs | 浪费（无证据纳入） |
| V3 | exclude 轴必须有 rationale，scanned 清单含 **G 级脚本输出 + S 级复核结论**双记录 | 漏测（无理由排除 / 脚本盲区制度化） |
| V4 | **两域**全部 depth=full 轴必须有 ≥High 风险编号引用；full 总数（两域合并）≤3 且与 depth_budget 一致；被 R6 裁剪的 Critical 轴必须有预算裁决记录 | 浪费（无重点） |
| V5 | execution_status=blocked 必须带 todo（向谁索取什么）；handoff 必须带 executor 与移交包引用 | 断链（移交即消失） |

### 5.3 handoff 协议（做实"移交"）

**移交包**：test-strategy 对 handoff / blocked 轴生成 `{项目}/专项移交_{轴}_{日期}.yaml`，内容按接收方定制（k6：用户旅程、到达率阶梯、时长、阈值；渗透：目标面、角色矩阵、授权范围）。**回收格式**：`core/report-template.md` 增设「专项结果」表——外部工具的结果由 agent 归一化填入（发现 × 证据等级 E3 × 阈值判定），消灭"策略里写了移交、报告里永远空白"的现状断链。

### 5.4 弱模型增益设计（默认形态，非降级预案）

北极星是最弱模型增益下限，因此弱模型支持不是"过载后的兜底"，是决策层的**默认设计形态**。头条价值主张：**把类型视野从模型能力变成框架能力**——弱模型 Off 侧的系统性缺陷是类型盲区（只会测 PRD 提到的，看不见代码里只有信号、没有需求文案的可靠性 / 契约 / 迁移轴），这正是类别性质变发生的位置。四个机制：

1. **机械活全部脚本外包**（方案 B 已裁决）：G 级信号查找、预填、校验全进脚本；S 级语义复核是 agent 的固定动作（每轴清单固定、照单执行）；弱模型只做"证据 → 决策"与"照单复核"两类受限判断——这是它够得着的认知负荷
2. **脚本预填 + agent 修订**：scan_signals.py 按矩阵默认档产出预填决策表（include 轴 + 信号 + 默认深度），agent 的工作从"空白生成"变成"核对调整"——编辑比生成更适配弱模型。**防橡皮图章**：exclude 决策不允许预填，且预填仅基于 G 级——exclude 必须由 agent 完成 S 级语义复核并记录 G + S 双清单（V3 兜底）
3. **分轴组推进 + 交付核对**：十轴不要求单次全扫，按 3–4 组顺序推进（如：资金与正确性组〔性能 / 并发 / 业务安全〕→ 依赖与变更组〔可靠 / 契约 / 迁移〕→ 前端体验组〔兼容 / a11y / 视觉 / i18n〕），每组完成即核对"组内全轴有决策"再进下一组，**且只加载矩阵中本组轴的小节**（矩阵按轴成节，见 §3 结构约定）——复用 tcw 弱模型修复的「逐模块推进与交付核对」硬约束。强模型同样走此形态（不损失正确性，只多花少量 token）——单一代码路径，不做"强模型快路径"的分支赌博
4. **受限选择模板**：decision / depth / execution_status 全部是枚举值，signals 引用脚本产出的信号 ID，rationale 给句子框架——弱模型对"从清单里选"的遵循度远高于自由生成（用例规格 0.26→0.98 的增益来源正是格式约束）

---

## 6. 与既有内容的关系（同步改写清单）

| 文件 | 改动 | 目的 |
|---|---|---|
| `core/test-type-matrix.md`（新增） | §2–§4 全部内容，约 250–300 行，**按轴独立成节 + 文首组索引**，L3 按组加载（实际落地 165 行） | 单一真相 |
| `core/scripts/scan_signals.py`（新增） | 每轴 grep 模式清单 → 结构化信号（文件:行）+ 默认档预填决策表；零第三方依赖 | 弱模型外包 + 确定性（§5.4） |
| `test-strategy/SKILL.md` | 工作流插入「全轴扫描」步骤（按组加载矩阵小节 → G 级扫描 + S 级复核 → 逐轴决策 → 深度校准 → 预算排序）；scope schema 换 §5.1 结构，**功能域 +state / +data_consistency / 迁出 compatibility** | 决策流程入口 |
| `core/coverage.md` | 类型性维度（11/13/14/15/16/18/19）改为「类型提示：决策以 test-type-matrix 为准」 | 消灭多头真相 |
| `core/risk-model.md` | dimension 枚举与矩阵轴对齐 | 同上 |
| `core/scripts/validate_schema.py` | V1–V5 | 机制兜底 |
| `core/schema-extraction.md` + `core/case-format.md` | Test Case Schema type 枚举扩值：+ `reliability / concurrency / security / compatibility` | 类型域用例进双轨 Schema（映射见下行） |
| `core/report-template.md` | 专项结果回收表 | handoff 闭环 |
| `test-case-writing/SKILL.md` | 消费 type_scope，按**轴 → 消费方式**映射：**用例型**（可靠 / 并发 / 业务安全 / 兼容，standard 及以上）→ 产手动用例，type 用新增枚举值；**脚本型**（性能 / 视觉，standard 及以上）→ 不产手动用例，产执行物进执行策略裁决；**审查型**（light 档）→ 产扫描 / 审查清单条目（Cx/Dn 通道） | 决策传导到设计 |
| `qa/SKILL.md` | 流水线表更新（策略产物含 type_scope 与专项移交包）；**新增预算裁决检查点**（R6 裁剪 Critical 轴时触发，第四类人工检查点） | 编排同步 |
| `docs/qa-skills-v2.md` | §6.3 加取代注记（指向本文档）、§7.3 标注 schema 扩展 | 消灭双头真相 |

**行数预算**：test-strategy SKILL.md 当前约 100 行，改造后预计 150 行内（远低于 500 红线；落地时点实测 131 行，2026-08-26 为 134 行）；矩阵本体约 300 行（落地时点实测 165 行，2026-08-27 为 169 行），仅策略阶段加载。

---

## 7. 决策类黄金任务与指标

### 7.1 任务形态（客观判，无需 LLM judge）

输入：需求文档 + 代码仓库；GT：**专家的全轴决策**（每轴 decision / depth + 关键信号集）。GT 是人工标注的有限集合，指标全部机械计算——符合"客观指标自动判"的既有方法学，也绕开成对评审平局率超限的老问题。

### 7.2 指标

```text
类型查全率   = |GT_include ∩ AI_include| / |GT_include|        ← 主指标，Critical 轴双倍权重的加权版并列报告
类型查准率   = 有信号支撑的 AI_include / |AI_include|
深度校准率   = include 交集中 depth 精确一致数 / |GT_include ∩ AI_include|
排除正当率   = AI_exclude 中 rationale 引用了真实扫描结果的比例
```

四个指标分别对应：漏测、浪费、判断精度、排除纪律。

**口径精确定义**：「有信号支撑」= 该轴决策所引信号与 GT 信号集可匹配（按轴比对，G / S 级分别核对）；「真实扫描结果」= scanned 清单与 scan_signals.py 实际输出一致、且 S 级复核结论在案。

**头条价值假设（Phase B 首轮在最弱模型上验证）**：Off 侧类型查全率显著低——尤其**仅代码信号的轴**（可靠性 / 契约 / 迁移：PRD 没写、只有代码里有痕迹）构成系统性盲区；On 侧接近 GT。跨模型预期梯度：弱模型增益 > 中档 > 强模型（强模型自带部分类型视野，其增益来自纪律与防漏）——增益矩阵若呈现此梯度，就是"类型视野从模型能力变成框架能力"的直接证据。

### 7.3 五个原型任务（覆盖信号分布的关键切片）

1. **电商券系统**（需求显性：秒杀 + 库存 + 资损 + 外部风控依赖）→ GT：并发 / 性能 / 迁移 / 契约 include——考"显性信号的档位校准"
2. **内部多角色管理后台**（需求显性多角色 + 隐私数据，无容量诉求）→ GT：业务安全 full（R1），性能 exclude（正当排除）——考"该排除时排除"
3. **对外营销官网**（纯前端 + 品牌规范 + 海外多语言市场）→ GT：a11y / visual / 兼容 / i18n include，功能域 light——考"非后端类型的可见性"
4. **微服务支付链路**（代码里有 retry / queue / 外部支付调用，**PRD 只字未提**）→ GT：可靠性 / 契约 include——考"代码信号优先于需求文本"（code-aware 支柱的类型域验证）
5. **存量系统加字段**（migration 文件 + 双写）→ GT：迁移 standard——考"变更驱动的轴唤醒"

**任务 × 轴 GT 覆盖矩阵**（I-full / I-std / I-light / E = 该任务此轴的 GT 判例；设计目标：每轴 ≥1 个 include 判例 + ≥1 个 exclude 判例）：

| 轴 | ①券系统 | ②管理后台 | ③营销官网 | ④支付链路 | ⑤加字段 |
|---|---|---|---|---|---|
| 性能 | I-full | E | E | I-std | E |
| 业务安全 | I-std | I-full | I-light | I-std | I-std |
| 可靠性 | I-std | E | E | I-full | E |
| 并发 | I-full | E | E | I-std | E |
| 兼容 | I-light | I-light | I-std | E | E |
| 无障碍 | E | I-light | I-std | E | E |
| 视觉 | E | E | I-std | E | E |
| i18n | E | E | I-std | E | E |
| 迁移 | I-std | E | E | E | I-std |
| 契约 | I-light | E | E | I-full | E |

具体档位以 GT 双人复核定稿为准，本表为覆盖度设计基线——某轴若无 include 判例，查全率对该轴无意义（评测空转），这是本表存在的理由。

标注成本预估：每任务专家决策 GT 约 2–4 小时（低于可测点清单标注——决策空间只有 10 轴 × 3 档）。

---

## 8. 实施切分

```text
Phase A（本设计落地）     core/test-type-matrix.md + core/scripts/scan_signals.py（信号扫描 + 预填）+ test-strategy 改造（分轴组推进 + 受限选择）+ V1–V5 校验 + report-template 扩展 + §6 同步改写
Phase B（决策评测）       5 个黄金任务 + GT 标注 + harness 指标；模型矩阵轨道首轮跑最弱模型，验证头条假设（§7.2）
Phase C（选择性深化）     仅当某轴在真实使用中高频 include 且 agent 执行有类别优势 → 升级为专项 skill（首候选：性能/k6、业务安全、a11y+视觉）
                          工具接口清单（哪些决策规则缺证据供给，倒推接什么工具）
```

**合入质量门**（AGENTS.md 纪律）：Phase B 在最弱模型上，类型查全率 / 查准率出现类别性增益（预期形态：Off 侧查全率低——类型盲区是自由发挥模型的系统性缺陷；On 侧接近 GT）。+2pp 级差异视为噪声，不作为变更依据。

**成本披露**（README 3.3× 口径的延续）：决策层必然抬高策略阶段 token 成本；缓解已内建（按组加载矩阵小节、脚本预填替代自由生成、修订式决策）。Phase B 实测后，在增益矩阵旁如实披露决策层成本增量——"更好但更贵"的披露传统照旧。

**防过拟合**：黄金任务不进 skill 正文；矩阵信号规则不得引用黄金任务特征。

---

## 9. 反模式表

| 反模式 | 后果 | 约束 |
|---|---|---|
| 轴静默缺失 | 漏测被藏成"没想过" | V1 |
| include 无信号 | 样样都测 = 无重点 | V2 |
| exclude 只写"不适用" | 无从挑战，等于没答 | V3 禁套话，必须列 scanned 清单 |
| full 满天飞 | 资源稀释在长尾 | V4 + R6 |
| 环境缺位 → exclude | "做不了"冒充"不用测" | R5 / 原则 4 |
| 移交即消失 | 策略写了 k6，报告永远空 | V5 + §5.3 |
| 决策与执行耦合 | 环境恢复后重新决策，判断漂移 | §4.2 两列分离 |
| 矩阵复制进多个 skill | 多头真相漂移 | 原则 5，矩阵只在 core/ |
| 为强模型优化单次全扫 / 自由生成 | 弱模型遵循崩塌，头条亮点变风险项 | §5.4：分轴组 + 预填修订 + 受限选择为唯一形态 |
| 语义信号被脚本盲区冒充"扫描全灭" | 脚本抓不到 ≠ 不存在，exclude 穿上合规外衣 | G/S 双确认（§3、R4、V3） |

---

## 10. 开放问题

> 每条标注**所属环节**（skills = 产品实施侧 / eval = 评测侧）与**裁决时点**。

### 10.1 skills 侧

1. **代码信号的落地形态**——**已裁决（2026-08-23）：方案 B**。`core/scripts/scan_signals.py` 机械扫描（每轴 grep 模式清单 → 文件:行 信号 + 默认档预填表），agent 只做语义确认与补充；预填决策表与防橡皮图章约束（exclude 不可预填）见 §5.4。脚本随 Phase A 交付（§8）；边界：仅服务类型域信号扫描，不取代功能域的代码优先阅读。

### 10.2 eval 侧（Phase B 首轮验证）

2. **弱模型全轴扫描的遵循度**——**设计侧已裁决（2026-08-23）：升格为默认设计原则**（原则 6 + §5.4 四机制），不再是"过载后兜底"，弱模型增益即本设计的头条价值主张。剩余验证点：头条假设（§7.2）在最弱模型上是否成立；若分轴组推进后仍出现漏轴 / 敷衍决策，做数据驱动的进一步分片（逐轴）微调——是调参，不是形态返工。

### 10.3 eval 侧（评测方法学与规划）

3. **GT 双人复核口径**——**已执行（2026-08-23）**：第二标注者 = GLM-5.2（仅材料、不知矩阵与草稿，独立通道 opencode Zen；工具 `eval/harness/annotate_type_scope_gt.py`）。结果：决策一致 40/45（88.9%）、深度一致 37/45；分歧轴剔除分母（5 决策分歧 + 8 深度分歧标 depth_contested）。结构性发现：③⑤ 业务安全被不知矩阵的标注者独立 include——**硬默认获得规则体系外支持，GT 非循环自证**。剩余开放点：若引入人类第三标注者仲裁分歧轴，可将 5 个剔除轴回收进分母（当前按协议剔除，偏保守）。
4. **n=5 的统计功效**（Phase B 末评估）：5 个任务只够类别性判读（与「+2pp 视为噪声」纪律匹配）；扩容到 12（对齐现有任务池规模）的时点按首轮采样方差评估——不是要不要扩的问题，是何时扩的问题。

### 10.4 产品路线（Phase B 之后）

5. **级别路由（单元 / 集成 / 验收）**：本设计显式不含。若 Phase B 验证「全轴必答 + 信号挂证据」机制成立，级别路由作为决策层第二块**复用同一机制**，不另起炉灶。这是路线图决策，不涉评测。

### 10.5 长期（两侧共同）

6. **矩阵轴稳定性**：轴集合变动破坏 GT 可比性。skills 侧：轴增删走矩阵版本号；eval 侧：黄金集标注记录所用矩阵版本。
