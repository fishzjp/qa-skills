# 统一风险模型（Risk Model）

> 所有 Skill 统一引用本文件。风险模型与证据体系（`core/evidence.md`）强制挂钩：**没有证据的风险评级视为无效评级**。

## 1. 风险评分

```text
Risk Score = Impact × Likelihood
```

- Impact（影响）、Likelihood（可能性）各取 1–5，乘积 1–25
- **Change Scope（变更范围）与 Complexity（实现复杂度）不是乘子**，它们是估计 Likelihood / Impact 的启发式输入（见下表）

## 2. 两个因子的估计方法

| 因子 | 取值锚点 | 估计输入 |
|------|---------|---------|
| Impact（1–5） | 5 = 数据丢失 / 资损 / 安全；4 = 核心功能不可用；3 = 部分功能降级；2 = 体验问题；1 = 几乎无感知 | 失败后果分级：数据丢失 / 资损 / 安全 > 核心功能不可用 > 部分功能降级 > 体验问题 |
| Likelihood（1–5） | 5 = 几乎必然触发；3 = 常规路径可触发；1 = 极端条件才触发 | 变更范围（diff 大小与涉及面）、实现复杂度、历史缺陷密度、代码证据（如边界未防护、事务不完整） |

## 3. 风险等级（与用例优先级是两套体系）

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

## 4. Risk Map 标注格式

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
  status: needs_verification     # 见 core/evidence.md 第 3 节状态标注
  anchors: [TC-07-02]            # 覆盖此风险的用例编号（派生索引，主从规则见下）
```

**双向引用主从规则**：`case.risk_ref`（Test Case Schema 字段）为权威方向，只在用例侧维护；`risk.anchors` 是由 Schema 抽取派生的反向索引，每次抽取再生、不接受手工编辑——避免两侧漂移。

## 5. 推导链

```text
Evidence（评级依据）
    ↓
Risk Map（每条风险：等级 + 证据 + 置信度）
    ↓
Test Strategy（风险决定测什么、测多深）
    ↓
Test Case（risk_ref 反向追溯到风险锚点）
```

## 6. 与 `test-case-writing` 高风险点 Dn 的关系

`test-case-writing` 代码模式产出的附录高风险点 D1–Dn 是 Risk Map 在用例编写阶段的**局部实例**（聚焦代码审查发现的回归风险）：

- Dn 评级对齐本模型：Impact × Likelihood 评分 → Critical / High / Medium / Low 等级（替代旧的"最高/中高/中/低"表述；旧文件增量更新时顺带换算）
- Dn 每条强制带 evidence（level + `文件:行` source）与通过判据
- 存在 `test-strategy` 产出的 Risk Map 时，Dn 优先映射到已有风险的 `risk_ref`，不另立编号体系

## 7. 引用方式

各 SKILL.md 在需要风险评级 / 风险翻译的步骤标注"此时加载本文件"，相对路径 `../core/risk-model.md`。
