# 示例：同一任务的 Skill On / Off 产出对照

五组真实评测产出的对照——同一任务、同一模型、同一 harness，**唯一差异是是否注入 qa-skills**。
所有文件均为完整真实产物，未做修饰（选样规则：双臂各取**中位样本**——不挑最好的 On，也不丑化 Off）。
产出基于黄金集的虚构业务域（图券商城 / 在线文档协作等），不含真实系统信息。

> **单任务不构成统计结论。** 全套指标、置信区间与门判定见里程碑版 Release 附带的增益矩阵快照（[Releases](https://github.com/fishzjp/qa-skills/releases)）。逐组判读数字为该次运行的实测，跨 run / 跨模型不可直比。

## 五组对照总览

| 组 | 任务（考的 skill） | 有 Skill | 无 Skill | 该组实测（判分覆盖率） |
|----|------|------|------|------|
| 1 | 手动用例编写（test-case-writing） | [test-cases_with-skills.md](./test-cases_with-skills.md) | [test-cases_without-skills.md](./test-cases_without-skills.md) | 规格符合度 0.996 vs 0.971，格式采纳是主要差距 |
| 2 | API 测试脚本（api-testing） | [api-coupon_with-skills.md](./api-coupon_with-skills.md) | [api-coupon_without-skills.md](./api-coupon_without-skills.md) | 覆盖 0.94 vs 0.72；**真实执行通过率 0.97 vs 0.51** |
| 3 | Playwright E2E（automated-e2e-testing） | [e2e-spec_with-skills.md](./e2e-spec_with-skills.md) | [e2e-spec_without-skills.md](./e2e-spec_without-skills.md) | 覆盖 1.00 vs 0.85；执行成功率 0.56 vs 0.39 |
| 4 | 全流程测试方案（qa 编排） | [qa-pipeline_with-skills.md](./qa-pipeline_with-skills.md) | [qa-pipeline_without-skills.md](./qa-pipeline_without-skills.md) | 覆盖 0.70 vs 0.45 |
| 5 | 探索式测试笔记（exploratory-testing） | [exploratory-notes_with-skills.md](./exploratory-notes_with-skills.md) | [exploratory-notes_without-skills.md](./exploratory-notes_without-skills.md) | 覆盖 0.83 vs 0.71 |

---

## 1. 手动用例编写（test-case-writing）

来自黄金集任务 `tcw-coupon-prd`（优惠券创建 PRD：面额边界 / 有效期双模式 / 同商户名称唯一 / 发布状态流转）。

建议先看**[无 Skill 版](./test-cases_without-skills.md)**，注意这些问题：

- `TC-UI-001:访问优惠券创建页面,页面正常加载,无报错`——"正常"如何判定？报错看哪里？
- 环境信息以"待提供"三个字带过——执行者不知道**找谁拿什么**
- 大量用例堆在界面展示层，业务规则（如"已发布状态仅发放总量可调大"）的验证入口和判定深度不足

再看**[有 Skill 版](./test-cases_with-skills.md)**的同一部分：

- 导读四件套齐备：角色表、环境与账号表（未知项写成 `TODO:向谁索取什么`，而不是"待提供"）、术语表、图例
- 状态流转逐边有用例：TC-02-01～06 把"待发布 → 已发布"的编辑权限、拦截条件、发布后表现拆成可判定的一串用例
- 异步行为带判定时限：搜索"判失败"可见"到达结束时间后 1 小时内自动变为已结束，超过 1 小时未变判失败"——多久没变算失败是明确的
- （本示例为 PRD 文档模式，无代码可引故无附录；代码模式产出的附录区结构见 `../skills/core/case-format.md`）

## 2. API 测试脚本（api-testing）

同一份 OpenAPI 文档（优惠券接口），产出可直接运行的 pytest 工程。**这组的最大差距不在覆盖率，在"能不能跑"**：无 Skill 版通过率 0.51，多为环境承接与断言问题；有 Skill 版 0.97。

- **[有 Skill 版](./api-coupon_with-skills.md)**：`common/client.py` 统一封装 + `conftest.py` 环境承接（凭证全部走环境变量）+ 测试文件按"正常创建 / 必填缺失 / 类型错误 / 边界值（name 空白与超长、amount 0 与上限）/ 无效 Token 401"参数化铺开
- **[无 Skill 版](./api-coupon_without-skills.md)**：有脚本形态，但边界与负向打底不足、鉴权与清理链路不完整

## 3. Playwright E2E（automated-e2e-testing）

同一份 markmap 用例转 Playwright 工程。注意一个诚实信号：**这组无 Skill 版的判分覆盖率并不低（0.85）——差距在真实执行**（0.39 vs 0.56；另一次执行专项评测中为 0/9 可运行 vs 7/9）。覆盖数字好看、脚本跑不起来，正是 E2E 最常见的坑。

- **[有 Skill 版](./e2e-spec_with-skills.md)**：Page Object 分层 + 每用例自建数据自清理 + 搜索用例额外造"不匹配数据"防断言恒真 + 删除用例做持久化验证
- **[无 Skill 版](./e2e-spec_without-skills.md)**：结构形似，但等待策略、清理与断言强度的缺口在真实执行中暴露

## 4. 全流程测试方案（qa 编排）

同一份"在线文档协作"需求，要求给出完整测试流水线方案。这是 `qa` 编排 skill 的直接对照。

- **[有 Skill 版](./qa-pipeline_with-skills.md)**：九个阶段齐全——**阶段 0（旁路）探索先行**（需求不完整时先摸系统）、阶段间产物落盘衔接、检查点标明"此处由人拍板"
- **[无 Skill 版](./qa-pipeline_without-skills.md)**：八个阶段的通用流水线框架，阶段平行铺开、无探索旁路、无落盘接力与人检查点设计

## 5. 探索式测试笔记（exploratory-testing）

同一份"文档分享与权限"的探索任务（charter 驱动）。

- **[有 Skill 版](./exploratory-notes_with-skills.md)**：风险清单每条带证据标注与预评级（R1～R5，含"缓存窗口期""评论通知绕过权限"等具体机制假设）、发现的 Bug 标注 Hypothesis 未定性——区分"我观察到了什么"和"我推测什么"
- **[无 Skill 版](./exploratory-notes_without-skills.md)**：章节骨架齐全但内容泛化，风险与发现缺少证据标注和机制深度

---

## 产出溯源（可核查口径）

| 组 | 黄金集任务 | 采样来源 | 模型 | 选样 |
|----|------|------|------|------|
| 1 | tcw-coupon-prd | 验证轮 | glm-5.2（历史版本口径，详见 Release 说明） | 验证轮代表采样 |
| 2 | api-openapi-coupon | 本地评测链路 2026-09 轮次 | deepseek-v4-flash，双臂 n=3 | 双臂中位样本 |
| 3 | e2e-markmap-to-spec | 本地评测链路 2026-09 轮次 | deepseek-v4-flash，双臂 n=3 | 双臂中位样本 |
| 4 | qa-doc-collab-pipeline | 本地评测链路 2026-09 轮次 | deepseek-v4-flash，双臂 n=3 | 双臂中位样本 |
| 5 | exp-docshare-permission | 本地评测链路 2026-09 轮次 | deepseek-v4-flash，双臂 n=3 | 双臂中位样本 |

评测方法学、任务池与原始数据在维护者本地评测链路维护、不随仓库分发；对外数字以 README 实测效果表与 Release 增益矩阵快照为准。
