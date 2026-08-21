# Test Case Schema 抽取规则（唯一来源）

> markmap → `测试用例.schema.yaml` 的抽取规则全框架唯一定义处。`test-case-writing` 编写/增量更新后抽取，`test-case-review` 修订后重新抽取，`regression-testing` / 执行层（`automated-e2e-testing` / `api-testing`）消费其结构化字段。规则变更只改本文件，不改各 SKILL.md。

## 双轨原则

markmap 是给人的交付物与**唯一人工维护源**；Schema 是机器可读元数据层，由 skill 在加工时**从 markmap 单向抽取**，作为 Skill 间流转接口。**不要求人维护两份**，Schema 永远可由 markmap 再生。markmap 任何修改后必须重新抽取，两轨不一致以 markmap 为准。

## 抽取规则（逐字段）

```yaml
test_case:
  id: TC-02-03                  # ← 用例编号
  title:                        # ← 名称行去编号与优先级
  module:                       # ← 所属一级模块标题（状态机节点/子模块）
  priority: P0 | P1 | P2        # ← 名称行 [Px] 标注，缺省 P1
  type: functional | boundary | exception | permission | regression | state | data
                                # ← 按模块/子模块类别与用例内容判定
  execution_model: ui | dev-collab  # ← 执行模型判定结果（协作五段式 → dev-collab）
  smoke: SMOKE-1                # ← 名称后（SMOKE-n），非冒烟省略
  preconditions: []             # ← 该条「前置条件」行（共享前置在模块级，不重复）
  steps: []                     # ← 操作步骤；dev-collab 保留「请开发执行」标注
  expected: []                  # ← 预期结果（含判定时限原文）
  test_data: {}                 # ← 步骤中嵌入的具体数据
  risk_ref:                     # ← 关联风险编号：Risk Map 的 R1…（无策略时 Dn 的 D1…）
  code_refs: []                 # ← 附录「代码证据清单」中该 TC 的 文件:行 列表
  evidence:                     # ← 该用例依据的证据（level E0–E4 / source / confidence，见 core/evidence.md）
  tags: []                      # ← [需真机] / [需Mock] / [需专业环境]
  automation:
    supported: yes | no | partial   # ← 按 execution_model + tags 推断（ui 无特殊标签→playwright；dev-collab→api 或 manual）
    framework:                  # playwright / api / manual
  status: active | changed | deprecated  # ← 增量更新标记（[已变更]/[已废弃]）
```

## YAML 转义纪律（防空解析）

title / steps / expected 等字段值含引号或冒号时必须转义——双引号值内的 `"` 写成 `\"`，或整体改用单引号包裹（内部单引号双写 `''`）；禁止在双引号值内裸放引号（如 `"满100减20"券"` 是非法 YAML，一条解析失败会中断下游全部消费）。长文本建议用 `>-` 块标量。

## 抽取后校验（强烈建议）

抽取/修订重抽后运行 `core/scripts/validate_schema.py`（无第三方依赖）：

```bash
python3 <skills目录>/core/scripts/validate_schema.py 测试用例_markmap.md 测试用例.schema.yaml
```

校验：YAML 可解析（转义纪律）、Schema 的 TC 编号与 markmap 一致（无孤儿/遗漏）、字段值无 `{xxx}` 占位符。零依赖环境下 YAML 解析降级为基础 lint（引号配对 / 缩进 / 裸冒号）。

## 存量迁移

已有 markmap 用例文件按同规则抽取（TC 编号、优先级、模块结构都是现成锚点），不需要人工重写。

## 引用方式

各 SKILL.md 在抽取 / 重新抽取步骤标注"此时加载本文件"，相对路径 `../core/schema-extraction.md`。
