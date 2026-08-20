# Eval Harness 使用说明（v2 科学评估体系）

> **当前状态（2026-08-20）**：主通道（arkcli / glm-5-2）正常；opencode 通道（异构 judge / 成对评审 / 泛化模型）因月度额度耗尽暂不可用，验证轮的 judge 已降级为同源模型并在结果中如实标注——恢复后按文末"待补项"各一条命令补齐。

## 目录

```
eval/
├── EXPECTED.md            # 预期效果门 G1–G7（v1.0 冻结 + 验证轮判定 + v1.1 提案）
├── golden/                # 黄金集 v0：12 个任务（task.md + annotation.json）
│                          #   annotation 的 audit 字段记录独立审计与人工复核的修改及理由
├── harness/
│   ├── run_eval.py        # 主脚本：setup-e2e / audit-annotations / generate / score
│   ├── judge_schema.json  # 逐点评审输出约束（covered/detected/quality）
│   ├── pairwise_schema.json  # 成对评审输出约束（winner A/B/tie）
│   ├── audit_schema.json  # 标注审计输出约束（kept/revise/remove + missing）
│   └── fixtures/
│       ├── playwright_scaffold/   # E2E 固定执行环境（mock_app 被测应用 + 功能化 helpers + chromium）
│       └── mock_api/server.py     # API 固定执行环境（实现任务 OpenAPI 契约与业务规则）
└── results/               # 归档：runs/{时间戳}/outputs|judge|pairwise|exec + metrics.json + report.md
```

## 模型路由

- 生成（主）：`EVAL_GEN_MODEL`（默认 glm-5-2-260617，走 arkcli +chat）
- 逐点评审：`EVAL_JUDGE_MODEL`（默认 oc:deepseek-v4-flash，走 opencode Zen OpenAI 兼容端点）——设计目标与生成模型**异构**消除自评偏差（当前因额度降级为同源，见顶部状态）
- 成对评审：`EVAL_PAIR_JUDGE_MODEL`（默认 oc:kimi-k3，强模型用于最需要判断力的对比；实际所用模型落盘于 metrics.json）
- 标注审计：`EVAL_AUDIT_MODEL`（默认 oc:kimi-k3）
- 泛化生成：`--model oc:deepseek-v4-pro`（产物文件带模型标签，score 自动分组出 G7）
- `oc:` 前缀走 opencode（`OPENCODE_GO_KEY` 放在仓库根 `.env`，**不入 git**）；其余走 arkcli

## 运行

```bash
# 0) 一次性：安装依赖与浏览器（chromium）
python3 eval/harness/run_eval.py setup-e2e

# 1) 标注独立审计（GT 可测点的范围/歧义/遗漏；一致性落盘 annotation_audit_summary.json）
python3 eval/harness/run_eval.py audit-annotations

# 2) 生成：每任务×模式 n=3 采样（断点续跑：重跑同命令跳过已成功文件）
python3 eval/harness/run_eval.py generate --samples 3

# 2b) 泛化：第二模型 n=2（写入同 run 目录，文件带模型标签）
python3 eval/harness/run_eval.py generate --samples 2 --model oc:deepseek-v4-pro --run-dir <同上>

# 3) 评分：逐采样 judge（3 表决）+ 成对评审（位置互换）+ 真实执行 + 统计推断 + 冻结门判定
python3 eval/harness/run_eval.py score --samples 3 --run-dir <同上>
```

环境变量：`EVAL_WORKERS`（并发，默认 4）、`EVAL_JUDGE_SAMPLES`（judge 表决数，默认 3）、
`EVAL_PAIR_SAMPLES`（成对评审采样对数，默认 2）、`EVAL_GEN/E2E/API_TIMEOUT`、`EVAL_E2E_PORT/EVAL_API_PORT`。

## 缓存与断点续跑规则（重要）

- `generate` / `judge` / `pairwise` 按文件缓存，成功即跳过；重跑同一命令只补失败项
- `exec` 仅缓存 `exec_ok=true` 的结果——环境错误（mock 起不来/端口被占/超时）会重试，不把 pass_rate=0 的环境失败固化成数据
- **缓存不感知上游变更**：改了 annotation.json、judge prompt、judge 模型或 mock 应用/服务，必须先删除对应缓存（judge/、pairwise/、exec/ 下相关 json）再评分，否则结果是旧的
- 失败的 judge/pairwise 文件会自动重试（ok=false 不算缓存命中）

## 标注审计工作流（改 golden 集必走）

1. 修改/新增 annotation 后：`python3 eval/harness/run_eval.py audit-annotations`（独立审计角色逐条给 kept/revise/remove + 遗漏项）
2. 人工逐条复核 flagged 项：接受/拒绝都要有理由，连同修改写入 annotation 的 `audit` 字段（changes 列表）；可参考 tcw-export-noui 等任务的既有写法
3. 删除该 run 目录 judge/ 下对应任务的缓存后重新 score

## 方法学（v2，对应行业主流实践）

| 环节 | 做法 | 行业对应 |
|------|------|---------|
| 生成 | 每任务×模式 **n=3 独立采样**，任务指标 = 均值±SD | pass@k / τ-bench pass^k 的重复采样思想 |
| 推断 | On/Off 差值在**任务层配对 bootstrap**（10k 次）报 95%CI；成对胜率先按任务聚合再报 Wilson 95%CI（避免同任务多对伪重复） | SWE-bench 式 bootstrap；二项比例 Wilson 区间 |
| 成对评审 | On vs Off 并排 + **位置互换**，不一致记平局 | MT-Bench / AlpacaEval pairwise + position-swap |
| judge | **异构模型**（设计目标）+ 3 采样多数表决 + JSON Schema 引导 + 本地校验（GT-id 集合、分值域 0-5）+ 表格行检出规则 | multi-sample majority、judge panel |
| 执行验证 | E2E：mock 被测应用（与任务材料严格一致）+ 真实 chromium 跑生成 spec，双跑测稳定；API：mock 服务实现 OpenAPI 契约与业务规则，跑生成 pytest | SWE-bench execution-based；环境固定 |
| 标注 | GT 由"未参与 skill 编写的独立审计角色"复核范围/歧义/遗漏，一致率落盘 | 标注者间一致性（IAA）思想的可行近似 |
| 门 | 预注册冻结（EXPECTED.md），阈值来自校准轮+边际，验证轮独立采样判定 | pre-registration；evals as CI |
| Executability | 客观正则逐条扫（占位符/模糊判定/正文代码/异步时限/断言超强度/导读四件套），脏率>50% 一票否决。**口径注意**：TC 编号与导读四件套为 skill 教的模板格式，该指标同时度量模板遵从度（对 Off 有构造偏差）；无格式采样计 0 不剔除分母，另报无格式依赖的 content_violations 密度 | grounded-fact audit；无 judge 参与的可复核指标 |
| Efficiency | 平均用例数 / 重复用例率 / tokens（On 的 Skill 成本） | correctness-latency-cost 三元组 |

## 固定执行环境说明

- **E2E mock 应用**（`fixtures/playwright_scaffold/mock_app/server.js`）：实现 e2e 任务"材料 3"的全部页面结构（登录 placeholder、新建/搜索/删除、`.project-card`、`GET /api/projects`），内存态、端口锁定（8931）；生成的 spec 若选择器与材料一致即可通过——**执行通过率度量的是"生成代码对真实系统的有效性"**
- **脚手架 helpers** 为真实实现（非编译桩）：`LoginPage.loginAs` 真登录并等待跳转
- **mock API**（`fixtures/mock_api/server.py`）：实现 api 任务 OpenAPI 全部契约（参数校验、错误码、鉴权、限领 409、名称唯一），内存态、端口 8932；兼容常见登录路径

## 待补项（opencode 额度恢复后，各一条命令）

```bash
# 1) 异构 judge 复评（当前验证轮 judge 与生成同源，覆盖/质量/成对为保守估计）
rm -rf eval/results/runs/<run>/judge eval/results/runs/<run>/pairwise
EVAL_JUDGE_MODEL=oc:deepseek-v4-flash EVAL_PAIR_JUDGE_MODEL=oc:kimi-k3 \
  python3 eval/harness/run_eval.py score --samples 3 --run-dir <run>

# 2) G7 泛化：第二生成模型（产物文件自动带模型标签，score 自动分组出 G7）
python3 eval/harness/run_eval.py generate --samples 2 --model oc:deepseek-v4-pro --run-dir <run>
python3 eval/harness/run_eval.py score --samples 3 --run-dir <run>
```
