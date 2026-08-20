# Eval Harness 使用说明

## 目录

```
eval/
├── EXPECTED.md            # 预期效果门（G1–G6，score 阶段自动判定）
├── golden/                # 黄金集 v0：12 个任务（task.md + annotation.json）
│   ├── tcw-*              # test-case-writing × 5（PRD / 代码 / 无UI / 状态机 / 增量）
│   ├── rev-*              # test-case-review × 1（植入 13 处问题的用例文件）
│   ├── req-*              # requirement-analysis × 1（8 处矛盾/模糊）
│   ├── strategy-*         # test-strategy × 1（6 个植入风险）
│   ├── api-*              # api-testing × 1（OpenAPI → pytest）
│   ├── e2e-*              # automated-e2e-testing × 1（markmap → Playwright）
│   ├── bug-*              # bug-analysis × 1（off-by-one 根因）
│   └── reg-*              # regression-testing × 1（diff + Schema → 回归清单）
├── harness/
│   ├── run_eval.py        # 主脚本：generate / score / setup-e2e
│   ├── judge_schema.json  # LLM judge 的 JSON Schema 输出约束
│   └── fixtures/playwright_scaffold/   # E2E 编译检查脚手架（npm 依赖不进 git）
└── results/               # 评测结果归档（runs/{时间戳}/outputs|judge|metrics.json|report.md + LATEST.md）
```

## 运行

```bash
# 0) 一次性：安装 E2E 编译检查依赖
python3 eval/harness/run_eval.py setup-e2e

# 1) 生成（Skill On / Off 双模式，失败重跑同一命令即可续跑，成功会缓存）
python3 eval/harness/run_eval.py generate

# 2) 评分（客观检查 + LLM judge + 聚合 + 预期效果门）
python3 eval/harness/run_eval.py score --run-dir eval/results/runs/<目录>

# 只跑部分任务（子串匹配）
python3 eval/harness/run_eval.py generate --tasks tcw- api-
```

环境变量：`EVAL_MODEL`（默认 glm-5-2-260617，两模式必须同模型）、`EVAL_WORKERS`（并发，默认 3）、`EVAL_GEN_TIMEOUT` / `EVAL_JUDGE_TIMEOUT`。

## 方法学

- **On / Off 唯一差异**：是否把 `annotation.json → skill_files_on` 列出的 skill 指令文件注入 instructions；任务输入两模式完全一致
- **Coverage 分母**：`annotation.json → testable_points`（Agent 标注 v0，人工复核待扩容，见 EXPECTED.md 已知限制）
- **Executability（一票否决）**：`run_eval.py` 客观检查逐条扫用例（占位符 / 模糊判定 / 正文代码泄漏 / 异步无时限 / 断言超强度），导读四件套单独计分；脏用例 > 50% → 该任务 Coverage 计 0，否则有效覆盖 = 覆盖 × 可执行性分
- **编译类客观指标**：api 任务 py_compile；e2e 任务写入脚手架后 `tsc --noEmit` + spec 静态检查（TC 命名 / 无固定等待 / PO 封装 / 持久化断言）
- **LLM-as-judge**：固定 rubric（correctness / specificity / actionability 各 0–5）+ JSON Schema 强约束输出；judge prompt 在 `run_eval.py → JUDGE_PROMPT`，纳入版本管理
