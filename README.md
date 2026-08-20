# QA Skills

面向软件测试全生命周期的 [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) 框架：一套「Agentic QA 方法论 + Skills + Benchmark」。用户只需说**"帮我测试这个需求"**，Agent 按流水线完成：理解需求 → 分析代码 → 识别风险 → 制定策略 → 生成用例 → 审查覆盖 → 选择执行方式 → 执行 → 发现 Bug → 分析根因 → 生成回归清单 → 输出测试报告。

## 四大支柱

- **Code-aware**：理解真实代码，而不是只读 PRD（代码优先 + 测准声明）
- **Risk-driven**：风险 → 策略 → 用例的推导链（Impact × Likelihood，评级强制挂证据）
- **Evidence-driven**：所有结论标注证据等级（E0–E4）与状态，压幻觉
- **Evaluated**：黄金集 + Benchmark 量化 Skill On / Off 的能力差异

## Skill 体系（10 个 Skill + 共享知识库）

| 你想做的事 | 用哪个 skill |
|------------|--------------|
| "帮我测试这个需求"（端到端流水线） | **qa**（编排入口） |
| 系统性需求建模（目标/范围/规则/异常/不明确项） | requirement-analysis |
| "这个功能应该怎么测"（范围/深度/优先级 + Risk Map） | test-strategy |
| 从需求/代码编写可执行的手动用例（markmap + Schema） | test-case-writing |
| 独立审查已有用例的覆盖与质量 | test-case-review |
| 用例 → Playwright E2E 自动化执行、Bug 证据记录 | automated-e2e-testing |
| 接口级测试（参数/边界/鉴权/幂等/并发） | api-testing |
| 无文档/新系统的探索式测试会话（charter 驱动） | exploratory-testing |
| 已确认 Bug 的根因定位、影响分析、回归建议 | bug-analysis |
| 代码变更后判断回归哪些测试 | regression-testing |

`core/` 为跨 Skill 共享知识库（无 SKILL.md，不会被独立触发）：测试原则、风险模型、证据体系、用例可执行性标准、测试报告模板。

## 安装

把对应目录复制到你的 Agent skills 目录（`core/` 必须一并复制，各 skill 通过相对路径 `../core/*.md` 引用）：

```bash
# 示例：安装到当前项目（保留顶层目录结构）
cp -r qa core requirement-analysis test-strategy test-case-writing test-case-review \
      automated-e2e-testing api-testing exploratory-testing bug-analysis regression-testing \
      <项目>/.claude/skills/
```

安装后直接描述任务（如「帮我测试这个需求」「根据这份 PRD 写测试用例」），对应 skill 自动触发；也可显式调用。

## 目录结构

```
qa-skills/
├── qa/                        # 编排入口（唯一面向"端到端测试"意图，薄编排无领域知识）
├── core/                      # 共享知识库（非 skill）：testing-principles / risk-model /
│                              #   evidence / executability / report-template
├── requirement-analysis/      # 需求建模 → 需求模型.md
├── test-strategy/             # 风险 → 策略 → 测试策略.md（含 Risk Map）
├── test-case-writing/         # 用例编写 → 测试用例_markmap.md + 测试用例.schema.yaml
│   ├── references/            # 方法知识（coverage / boundary / state-machine / permission /
│   │                          #   data-driven / templates，按需加载）
│   └── templates/             # markmap 拼装模板
├── test-case-review/          # 独立用例审查（直接修订 + 审查记录）
├── automated-e2e-testing/     # Playwright E2E（含 references/helpers_reference.md）
├── api-testing/               # 接口级测试（pytest + requests）
├── exploratory-testing/       # charter 驱动探索会话 → 探索笔记_{主题}.md
├── bug-analysis/              # Bug 根因/影响/回归建议 → 追加进测试报告
├── regression-testing/        # diff → 影响面 → 回归清单_{日期}.md
└── eval/                      # 科学评估体系（harness/README.md 详述）
    ├── EXPECTED.md            # 预期效果门 v1.0（预注册冻结）+ 验证轮判定 + v1.1 提案
    ├── golden/                # 黄金集 12 任务（标注经独立审计，annotation.audit 记录修改）
    ├── harness/
    │   ├── run_eval.py        # setup-e2e / audit-annotations / generate / score
    │   ├── *_schema.json      # judge / pairwise / audit 的 JSON Schema 约束
    │   └── fixtures/          # 固定执行环境：playwright_scaffold（含 mock_app 被测应用）
    │                          #   与 mock_api（实现任务 OpenAPI 契约的 mock 服务）
    └── results/               # 运行归档（outputs/judge/pairwise/exec + metrics + report）
```

## 产物流转（文件即流水线状态）

```text
需求模型.md → 测试策略.md（Risk Map）→ 测试用例_markmap.md + 测试用例.schema.yaml
    →（审查修订）→ 执行（playwright/ 或 API 脚本）→ Bug 条目 → 回归清单_{日期}.md
    → 测试报告_{日期}.md（按 core/report-template.md）
```

每个阶段的产出落盘为文件，跨会话可续跑（`qa` 的断点续跑只认文件）；Schema 从 markmap 单向抽取，供审查 / 回归 / 执行层消费。

## Eval 与 Benchmark（科学评估体系 v2）

黄金集 12 任务（GT 标注经独立审计 + 人工复核），On/Off 对比采用多样本与统计推断，执行类指标跑真实环境：

```bash
python3 eval/harness/run_eval.py setup-e2e            # 一次性：依赖 + chromium 浏览器
python3 eval/harness/run_eval.py audit-annotations    # 可选：GT 标注独立审计（改标注后重跑）
python3 eval/harness/run_eval.py generate --samples 3 # 每任务×模式 3 次独立采样
python3 eval/harness/run_eval.py score --samples 3 --run-dir eval/results/runs/<目录>
```

方法学要点：任务层配对 bootstrap 95%CI；成对评审（On vs Off 并排 + 位置互换）；逐采样 judge 多数表决；E2E 产物在 mock 被测应用上以真实浏览器执行、API 产物对 mock 服务跑 pytest——**可执行性、编译、真实执行、植入 bug 检出为无 judge 参与的客观指标**。门 v1.0 预注册冻结（G1–G7），完整定义、验证轮判定（4/7 通过，失败项含诊断）与 v1.1 提案见 [eval/EXPECTED.md](./eval/EXPECTED.md)；最新报告见 [eval/results/LATEST.md](./eval/results/LATEST.md)，方法学详述见 [eval/harness/README.md](./eval/harness/README.md)。

**当前验证结论（2026-08-20 验证轮，如实记录）**：Skill 的可复现效应为——用例可执行性 0.77→0.98、E2E 代码真实执行通过率 0%→78%、植入 bug 检出 100%、质量 +5.7pp（CI 显著）、11/12 任务不劣化；覆盖类增益 +3.8pp（方向显著、幅度小于早期单采样表观值）；成本为 tokens 3.3×。

## 设计理念

- **SKILL.md ≤ 500 行红线**：只装触发边界与工作流；方法/规则/模板下沉 references 与 core/，按需加载（渐进披露）
- **每个 skill 必须有 When NOT to Use**，触发边界由 [能力迁移矩阵](./docs/qa-skills-v2.md) 约束（本地规划文档，未随仓库发布）
- **用例可执行性一票否决**：占位符、虚构入口、无时限异步 = 不可执行，覆盖再全也计零分（core/executability.md）
- **诚实清单**：澄清、执行策略、Bug 定性由用户裁决，Agent 不代答

## 许可证

MIT，详见 [LICENSE](./LICENSE)。
