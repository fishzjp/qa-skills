# Test Case Schema 抽取规则（唯一来源）

> markmap → `测试用例.schema.yaml` 的抽取规则全框架唯一定义处。`test-case-writing` 编写/增量更新后抽取，`test-case-review` 修订后重新抽取，`regression-testing` / 执行层（`automated-e2e-testing` / `api-testing`）消费其结构化字段。规则变更只改本文件，不改各 SKILL.md。

## 双轨原则

markmap 是给人的交付物与**唯一人工维护源**；Schema 是机器可读元数据层，由 skill 在加工时**从 markmap 单向抽取**，作为 Skill 间流转接口。**不要求人维护两份**，Schema 永远可由 markmap 再生。markmap 任何修改后必须重新抽取，两轨不一致以 markmap 为准。

## 文件整体形态（三层）

```yaml
meta:
  source_markmap: 测试用例_markmap.md   # ← 抽取来源文件名
  extracted_at: 2026-08-27             # ← 抽取日期（YYYY-MM-DD）
  strategy_ref: 测试策略.md             # ← 上游策略文件名；无策略时省略此键
modules:          # ← 一级模块表：module 字段的裁定依据 + 共享前置的唯一承载处
  - module: "2. 营销活动"
    shared_preconditions: []   # ← 该一级模块正文标题下的 `> 前置：` 引用块逐行摘录（见 case-format.md §5）
cases: []
```

- **cases 平铺**为列表（不是按模块嵌套树）——消费方全靠字段过滤，嵌套树徒增解析成本；模块归属由用例的 `module` 字段表达
- **`module` 字段裁定**：取用例所挂**一级模块标题原文**（`## 2. 营销活动` → `"2. 营销活动"`，含编号与名称）；子模块/细分类别不入该字段。TC 编号首段必须与一级模块编号一致（`TC-02-xx` 属于 module `"2. ..."`），校验器据此交叉核对
- **共享前置去重**：`modules[].shared_preconditions` 记各模块级共享前置一次；用例级 `preconditions` 只写该条额外需要的条件，与共享前置重复即违反去冗余规则（校验时若二者重复仅告警）

## 抽取规则（cases[] 逐字段）

```yaml
  id: TC-02-03                  # ← 用例编号
  title:                        # ← 名称行去编号与优先级
  module: "2. 营销活动"         # ← 所属一级模块标题原文（裁定规则见上节）
  priority: P0 | P1 | P2        # ← 名称行 [Px] 标注，缺省 P1
  type: functional | boundary | exception | permission | regression | state | data | reliability | concurrency | security | compatibility
                                # ← 按模块/子模块类别与用例内容判定；类型域四值（reliability/concurrency/security/compatibility）仅用于测试策略 type_scope 用例型轴产出的用例（映射见 test-type-matrix.md 第 12 节）
  execution_model: ui | dev-collab  # ← 执行模型判定结果（协作五段式 → dev-collab）
  smoke: SMOKE-1                # ← 名称后（SMOKE-n），非冒烟省略
  preconditions: []             # ← 该条特有的前置条件（共享前置在 modules 表，不在本字段重复）
  steps: []                     # ← 操作步骤；dev-collab 保留「请开发执行」标注
  expected: []                  # ← 预期结果（含判定时限原文）
  test_data: {}                 # ← 步骤中嵌入的具体测试数据，按步骤号组织 {step: 数据描述}（如 {2: "券码 NEW50-100"}）；expected 中的期望值不算 test_data。只用具体值（占位符是可执行性红线），多步骤共用一组入参时也拆到触发它的步骤号下
  risk_ref:                     # ← 关联风险编号：Risk Map 的 R1…（无策略时 Dn 的 D1…）
  code_refs: []                 # ← 附录「代码证据清单」中该 TC 的 文件:行 列表。**模式相关必填**：代码模式（markmap 有测准声明）应有非空列表——没有代码位置就没有被审查资格，确无一比一对应的实现可注明实现形态；纯文档模式一律空列表（编造指涉属幻觉证据）
  evidence:                     # ← 该用例依据的证据（level E0–E4 / source / confidence，见 core/evidence.md）。代码模式必填三件套；纯文档模式下 evidence 允许省略或值为 null（此时 level 上限 E1，准确性受限提示已由流程给出）
  tags: []                      # ← 两类合法值：可测试性标注 [需真机]/[需Mock]/[需专业环境]，以及类型域轴标签 [并发]/[可靠]/[安全]/[兼容]/[迁移]/[集成]/[国际化]（两组含义均见 case-format.md §6）；其余自由文本标签会在校验时收到告警
  automation:
    supported: yes | no | partial   # ← 按 execution_model + tags 推断（ui 无特殊标签→playwright；dev-collab→api 或 manual；[需Mock]/[需真机]/[需专业环境] 至多 partial）
    framework:                  # playwright / api / manual
  status: active | changed | deprecated  # ← 增量更新标记（[已变更]/[已废弃]）
```

## YAML 转义纪律（防空解析）

title / steps / expected 等字段值含引号或冒号时必须转义——双引号值内的 `"` 写成 `\"`，或整体改用单引号包裹（内部单引号双写 `''`）；禁止在双引号值内裸放引号（如 `"满100减20"券"` 是非法 YAML，一条解析失败会中断下游全部消费）。长文本建议用 `>-` 块标量。

## 抽取后校验（强烈建议）

抽取/修订重抽后运行 `../core/scripts/validate_schema.py`（无第三方依赖，路径相对消费本文件的 SKILL.md 所在目录）：

```bash
# 基础校验：YAML 可解析（转义纪律）+ TC 编号一致性 + 占位符检查
python3 ../core/scripts/validate_schema.py 测试用例_markmap.md 测试用例.schema.yaml

# 推荐：上游存在测试策略时叠加风险覆盖门禁——策略 Risk Map 中全部 Critical/High 风险
# 必须被至少一条用例的 risk_ref 反向覆盖（零覆盖 = 报错，证据链最后一环）；
# 有代码仓库时可叠加 --repo-root 抽查 code_refs 中 "文件.ext:行号" 指涉的真实性（缺失告警）
python3 ../core/scripts/validate_schema.py 测试用例_markmap.md 测试用例.schema.yaml \
  --strategy {项目}/测试策略.md --repo-root {被测仓库根}
```

校验说明：零依赖环境下 YAML 解析降级为基础 lint（引号配对 / 裸引号）。`--strategy` 同时核对 risk_ref 是否指涉 Risk Map 中存在的编号（未知名 → 告警提示疑似笔误）。

## 存量迁移

已有 markmap 用例文件按同规则抽取（TC 编号、优先级、模块结构都是现成锚点），不需要人工重写。历史上以 `test_case:` 为根的单对象 / 嵌套形态仍可被校验器解析（按 id 递归收集用例），但重新抽取时一律换成上文三层形态。

## 引用方式

各 SKILL.md 在抽取 / 重新抽取步骤标注"此时加载本文件"，相对路径 `../core/schema-extraction.md`。
