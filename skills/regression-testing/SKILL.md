---
name: regression-testing
description: 代码变更（diff/Bug 修复/需求变更）后自动判断应该回归哪些测试时使用——沿"改动文件 → 改动函数 → 受影响功能 → 受影响用例 → 回归范围"分析链，基于用例 Schema 的追溯映射产出分级回归清单。不用于：用例文件本身的增量修改（test-case-writing）、回归策略的长期制定（test-strategy）。
---

# 回归测试（regression-testing）

代码变更 → 自动判断应该回归哪些测试。

- **输入**：Code Diff（`git diff <base>...<head>`）、Bug 修复说明、需求变更说明、已有用例（markmap + `测试用例.schema.yaml`）、（可选）需求模型
- **输出（落盘）**：`{项目}/回归清单_{日期}.md`——必须回归（P0）/ 建议回归（P1）/ 可选回归（P2）三级，逐条给依据
- **前置依赖**：持久的"用例 ↔ 代码 ↔ 功能"追溯映射，v0 三层全部来自落盘产物，不依赖会话记忆：
  1. **代码级锚点**：用例附录「代码证据清单（TC ↔ 文件:行）」，由 Schema 的 `code_refs` 结构化
  2. **功能层**：需求模型 + Schema 的 `module` / `risk_ref`
  3. **per-run 增量**：改动文件映射附录（针对本次 diff 生成）

> 没有这个数据结构，影响面分析就只是"让模型读一遍 diff 猜"——Schema 缺失时先提示：可由 `test-case-writing` 对存量 markmap 抽取（不需要人工重写）。

## When NOT to Use

- 用例文件的增量修改本身（标记/新增/废弃用例）→ `test-case-writing` 增量更新流程
- 长期回归策略（锚点用例、回归节奏）→ `test-strategy` 的 regression_plan
- 判断某次失败是不是 Bug → `bug-analysis` / `automated-e2e-testing` 工作流二
- 端到端流水线 → `qa` 编排

## 分析链

```text
Changed Files（git diff）
    ↓
Changed Functions（diff 中被修改的函数/类/组件）
    ↓
Affected Features（函数 → 所属功能：经 Schema code_refs / module / 需求模型映射）
    ↓
Affected Test Cases（功能 → 用例：risk_ref / module / 附录改动文件映射）
    ↓
Regression Scope（三级回归清单 + 依据）
```

## 工作流

### 1. 盘点变更

```bash
git diff <base>...<head> --stat          # 改动文件清单
git diff <base>...<head> -U3             # 逐文件读改动内容，定位改动函数
```

变更类型分类（基础四类，与 `test-case-writing` 阶段一「改动盘点」的枚举一致）：🆕 新建 / ✏️ 修改（可按需细分标注：行为修改、🐛 Bug 修复（关联 Bug 单）、🔧 重构（行为应不变））/ 🗑️ 删除 / 💀 死代码。类型不同，回归侧重不同（重构 → 全量行为锚点；Bug 修复 → 修复验证 + 该 Bug 历史关联用例；死代码 → 不产生回归用例）。

### 2. 影响面分析（沿分析链逐层映射）

- **代码层**：Schema 中 `code_refs` 命中改动文件（或同文件邻近行）的用例 → 直接受影响
- **功能层**：改动函数所属功能（module / 需求模型）下的全部用例 → 间接受影响；共享工具/公共组件改动 → **消费方全查**（grep 引用方，逐个判断）
- **风险层**：Risk Map 中挂在受影响功能上的风险（`risk_ref` 反查）→ 其锚点用例（Critical 风险必进"必须回归"）
- **历史层**（有 Bug 单时）：该 Bug 涉及功能的历史回归用例

> 分析过程对每个映射给依据（"TC-03-02 code_refs 命中 `coupon_service.py:124`"），**映射不上的不硬编**——列入"影响不明，建议人工判断"。

### 3. 生成分级回归清单

```markdown
# 回归清单 — {日期}

- 变更基线：{base}...{head}（{commit 数} commits，{文件数} 文件）
- 变更类型：{新增/修改/修复/重构/删除}

## 必须回归（P0）
| 用例 | 依据 |
|------|------|
| TC-01-01（SMOKE-1） | 改动文件 code_refs 直连 + Critical 风险 R1 锚点 |

## 建议回归（P1）
| 用例 | 依据 |
|------|------|
| TC-02-03 | 同功能模块间接受影响（module=发放流程） |

## 可选回归（P2）
| 用例 | 依据 |
|------|------|
| TC-06-02 | 公共组件改动，消费关系间接 |

## 影响不明（建议人工判断）
- {文件/功能}：{为什么映射不上}

## 无影响确认（显式排除）
- {模块}：{排除依据，如"改动仅涉日志文案，无行为变更"}
```

> 与 `test-strategy` 的 regression_plan 对齐：锚点用例（Critical 风险 P0）默认进"必须回归"；执行方式按 automation_plan（e2e / api / 手动）标注。

### 4. 交付与执行衔接

- 清单落盘后交执行：自动化部分 → `automated-e2e-testing` / `api-testing`；手动部分 → 测试工程师
- 回归结果汇总进测试报告（`../core/report-template.md` §5 回归摘要）

## Common Mistakes

| 错误 | 后果 | 正确做法 |
|------|------|---------|
| 只按改动文件名匹配用例 | 同名不同层、公共组件消费方漏检 | 沿分析链走到底，公共组件 grep 引用方 |
| 无 Schema 时靠"读 diff 猜" | 影响面分析退化为猜 | 先对存量 markmap 抽取 Schema（`test-case-writing`） |
| 清单不给依据 | 不可复核，无法裁剪 | 每条用例给映射依据 |
| 全量回归一刀切 | 回归成本爆炸、关键用例被稀释 | 三级分级 + 显式排除清单 |
| 映射不上的硬编进清单 | 虚假置信 | "影响不明"单独列出，人工判断 |
| 用例文件修改与回归范围混为一谈 | 职责越界 | 用例修改归 `test-case-writing`，本 skill 只选回归范围 |
