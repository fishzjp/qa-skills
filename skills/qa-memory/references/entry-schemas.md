# .qa/ 条目 Schema（entry-schemas）

本文件是 `.qa/` 知识库条目格式的**唯一权威定义**：`scripts/memory_validate.py` 的校验规则与本文件同源——**改本文件必须同步改校验器与 `tests/test_memory_validator.py`**（CONTRIBUTING 架构红线 9）。

## 1. 条目物理形态

一个条目 = 一个 H2 小节，位于六个主题文件之一：

```markdown
## <ISO日期> <短语标题>

```yaml
<元数据块，见 §2>
```

**段落标记**：正文…
```

- **标题即标识，创建后不可变**：INDEX 与 `related` 都引用标题；确需改名 → 旧条目走 superseded + 新条目 `related` 指回（见 SKILL.md 工作流 G3）。标题内禁止竖线 `|`（INDEX 表格列分隔符）。
- 条目边界 = 标题行到下一个 `## ` 标题 / `## 归档` / 文件末尾（去尾部空行）。主题文件中除条目标题外只允许一个 `## 归档` 段（retired 条目的单行归档，每条一行：`日期 标题 — 一句话失效原因`）。
- 单条目 ≤40 行且 ≤2KB；主题文件 ≤300 行且 ≤50KB。

## 2. 元数据块（yaml 受限子集）

只支持**四种形态**，校验器自带解析器（不依赖 pyyaml）：

| 形态 | 示例 | 规则 |
|---|---|---|
| 裸标量 | `type: flaky` | 值内禁 `#`（注释歧义）与引号字符 |
| 带引号串（可空） | `evidence: ""` | 双引号成对包裹 |
| 单行列表 | `keywords: [checkout, websocket, 超时]` | 元素禁逗号、禁引号 |
| 空列表 | `related: []` | — |

解析细则：每行以首个 `: `（冒号+空格）切分 key/value；key 不重复；枚举值精确匹配（大小写敏感）；**裸标量与列表元素禁 `#`**（注释歧义；含 `#` 的值如 `条目.md#锚点` 用带引号串包裹）。

### 字段表

| 字段 | 必填 | 约束 |
|---|---|---|
| `type` | ✓ | 枚举 6 值，**与所在文件一一对应**：`env`→env-notes.md、`flaky`→flaky-tests.md、`defect`→defect-patterns.md、`contract`→api-contracts.md、`domain`→app-domain.md、`workflow`→workflows.md |
| `status` | ✓ | `active` \| `superseded` \| `retired`（失效不删除正文，见 SKILL.md G2） |
| `created` | ✓ | ISO 日期；**必须等于标题中的日期**；创建后不变 |
| `updated` | ✓ | ISO 日期；必须 ≥ created；每次实质修改更新 |
| `source` | ✓ | 非空。溯源：产生该知识的 skill/会话 + 日期或 commit（如 `bug-analysis@2026-09-05`） |
| `confidence` | ✓ | `tentative` \| `confirmed`；**首写一律 tentative**，升级判据见 §5 |
| `summary` | ✓ | 非空，≤60 字，一句话结论；禁止竖线 `|` |
| `keywords` | ✓ | 3–8 个非空元素，优先专有名词 |
| `related` |  | 列表；每个元素必须是 `.qa/` 内真实存在的条目标题（精确匹配） |
| `verified` |  | 最后一次现场核验的 ISO 日期或 commit 哈希（7–40 位十六进制）；staleness 锚点，读取时落后当前 HEAD 过多按 tentative 对待 |
| `evidence` |  | **defect 与 contract 类必填非空**：PR 链接 / commit / 落盘产物路径（证据可回查） |
| `gt-failure-mode` |  | `""` \| `澄清缺失` \| `边界遗漏` \| `状态遗漏` \| `断言强度不足`（评测飞轮对齐字段） |

未知 key 一律 FAIL（封闭 schema，防漂移）。

## 3. 正文段落标记（按 type，字面校验）

| type | 必需段落标记（字面） |
|---|---|
| `env` | `**现象**`、`**处置**` |
| `flaky` | `**症状**`、`**根因**`、`**处置**`（处置段必须含噪声/真实失败判定方法与重试策略） |
| `defect` | `**症状**`、`**根因**`、`**处置**`（处置段=修法+回归要点） |
| `contract` | `**契约**`、`**变更**` |
| `domain` | `**规则**`、`**依据**`（无依据不得 confirmed） |
| `workflow` | `**场景**`、`**步骤**`、`**注意**` |

**defect vs workflow 归属判据**（防跨文件重复）：以"症状→根因"为核心 → `defect`；以"操作序列"为核心 → `workflow`。查重范围为全 `.qa/`（不止目标文件）。

## 4. 完整正例（flaky）

```markdown
## 2026-09-05 checkout websocket 超时假失败

```yaml
type: flaky
status: active
created: 2026-09-05
updated: 2026-09-05
source: automated-e2e-testing@2026-09-05
confidence: tentative
summary: 支付 WS 网关超时致用例假失败，重试需带幂等头
keywords: [checkout, websocket, 超时]
related: []
verified: 2026-09-05
evidence: ""
gt-failure-mode: ""
```

**症状**：checkout_e2e.spec.ts:42 随机超时，重跑通过率高，CI 夜间更频。
**根因**：支付网关 WS 握手 P99 达 8s，默认 5s 超时不足；非被测系统缺陷。
**处置**：噪声判定=本地重跑 3 次通过且网关监控无告警。用例超时设 15s；重试必须带 `Idempotency-Key` 头防重复下单。
```

## 5. confidence 升降规则

- **首写默认 `tentative`**；升级 `confirmed` 判据（满足其一）：第二个独立会话现场复现 / 用户人工确认 / defect 类 evidence 中的 diff 已人审。
- 现场复核成功 → 升 confirmed 并刷新 `verified`；现场复核失败 → 走 superseded 失效记录；`confirmed` 不直接降级为 `tentative`（要么成立要么失效，防摇摆）。

## 6. 校验器负例清单（单测对照，改 schema 时同步补测）

以下形态必须 FAIL：value 含 `#`；列表元素含引号；未知 key；key 重复；缺 `: ` 分隔；keywords <3 或 >8；summary >60 字或含 `|`；标题含 `|`；type/status/confidence/gt-failure-mode 枚举外值；`updated < created`；标题日期 ≠ created；type 与所在文件不符；defect/contract 缺 evidence；related 指向不存在的标题；跨文件重复标题；缺正文段落标记；条目 >40 行或 >2KB；主题文件 >300 行或 >50KB；INDEX >150 行或 >20KB；归档区 >50 行；秘密扫描命中（`sk-`/AKIA/JWT/明文凭据赋值/Bearer 实值/URL 内嵌凭据）。

以下形态必须 WARN（不挡落盘，须人工确认）：代码块内的示例凭据、占位符形态（`<token>`/`xxx`）不命中、高熵长串、指令模式命中（"忽略校验/跳过审查/不要告知用户"类祈使句）。
