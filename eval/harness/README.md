# Eval Harness 使用说明（v2 科学评估体系）

## 目录

```
eval/
├── EXPECTED.md            # 预期效果门 G1–G7（v1.0 冻结 + 预注册声明 + 观察型指标）
├── golden/                # 黄金集 v0：12 个任务（task.md + annotation.json，标注经独立审计）
├── harness/
│   ├── run_eval.py        # 主脚本：setup-e2e / audit-annotations / generate / score
│   ├── judge_schema.json  # 逐点评审输出约束（covered/detected/quality）
│   ├── pairwise_schema.json  # 成对评审输出约束（winner A/B/tie）
│   ├── audit_schema.json  # 标注审计输出约束（kept/revise/remove + missing）
│   └── fixtures/
│       ├── playwright_scaffold/   # E2E 固定执行环境（含 mock_app 被测应用 + 功能化 helpers）
│       └── mock_api/server.py     # API 固定执行环境（实现任务 OpenAPI 契约与业务规则）
└── results/               # 归档：runs/{时间戳}/outputs|judge|pairwise|exec + metrics.json + report.md
```

## 模型路由

- 生成（主）：`EVAL_GEN_MODEL`（默认 glm-5-2-260617，走 arkcli +chat）
- 逐点评审：`EVAL_JUDGE_MODEL`（默认 oc:deepseek-v4-flash，走 opencode Zen OpenAI 兼容端点）——与生成模型**异构**，消除自评偏差
- 成对评审：`EVAL_PAIR_JUDGE_MODEL`（默认 oc:kimi-k3，强模型用于最需要判断力的对比）
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

## 方法学（v2，对应行业主流实践）

| 环节 | 做法 | 行业对应 |
|------|------|---------|
| 生成 | 每任务×模式 **n=3 独立采样**，任务指标 = 均值±SD | pass@k / τ-bench pass^k 的重复采样思想 |
| 推断 | On/Off 差值在**任务层配对 bootstrap**（10k 次）报 95%CI；成对胜率报 Wilson 95%CI | SWE-bench 式 bootstrap；二项比例 Wilson 区间 |
| 成对评审 | On vs Off 并排 + **位置互换**，不一致记平局 | MT-Bench / AlpacaEval pairwise + position-swap |
| judge | **异构模型** + 3 采样多数表决 + JSON Schema 约束 + 表格行检出规则 | multi-sample majority、judge panel |
| 执行验证 | E2E：mock 被测应用（与任务材料严格一致）+ 真实 chromium 跑生成 spec，双跑测稳定；API：mock 服务实现 OpenAPI 契约与业务规则，跑生成 pytest | SWE-bench execution-based；环境固定 |
| 标注 | GT 由"未参与 skill 编写的独立审计角色"复核范围/歧义/遗漏，一致率落盘 | 标注者间一致性（IAA）思想的可行近似 |
| 门 | 预注册冻结（EXPECTED.md），阈值来自校准轮+边际，验证轮独立采样判定 | pre-registration；evals as CI |
| Executability | 客观正则逐条扫（占位符/模糊判定/正文代码/异步时限/断言超强度/导读四件套），脏率>50% 一票否决 | grounded-fact audit；无 judge 参与的可复核指标 |
| Efficiency | 平均用例数 / 重复用例率 / tokens（On 的 Skill 成本） | correctness-latency-cost 三元组 |

## 固定执行环境说明

- **E2E mock 应用**（`fixtures/playwright_scaffold/mock_app/server.js`）：实现 e2e 任务"材料 3"的全部页面结构（登录 placeholder、新建/搜索/删除、`.project-card`、`GET /api/projects`），内存态、端口锁定（8931）；生成的 spec 若选择器与材料一致即可通过——**执行通过率度量的是"生成代码对真实系统的有效性"**
- **脚手架 helpers** 为真实实现（非编译桩）：`LoginPage.loginAs` 真登录并等待跳转
- **mock API**（`fixtures/mock_api/server.py`）：实现 api 任务 OpenAPI 全部契约（参数校验、错误码、鉴权、限领 409、名称唯一），内存态、端口 8932；兼容常见登录路径
