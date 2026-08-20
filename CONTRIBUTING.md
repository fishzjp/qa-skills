# 贡献指南

欢迎提交 Issue 和 Pull Request。

## 如何贡献

- **报告问题**：在 Issue 中描述复现场景与预期行为。
- **改进方法论**：各 skill 的工作流、检查表、模板都欢迎补充。改动请保持核心原则：一条用例只测一个点、代码优先（测准声明）、先澄清再动手、用例必须可执行（`core/executability.md`）、证据标注（`core/evidence.md`）。
- **补充代码模板**：新增的 Page Object / Helper 模板请保持通用、不绑定具体业务，且不包含任何真实账号、URL 或内部信息。
- **扩充黄金集**：`eval/golden/` 下新增任务（task.md + annotation.json，可测点/检出项须材料可推导、不依赖 skill 知识）。**新增或修改标注后必须跑独立审计**：`python3 eval/harness/run_eval.py audit-annotations`，flagged 项人工逐条复核后将修改与理由记入 annotation 的 `audit` 字段——标注者不得既写标注又独立复核同一批内容。

## 架构红线（改 skill 前必读）

1. **SKILL.md ≤ 500 行**：只装触发边界（L1）与工作流（L2）；方法 / 规则 / Checklist / 模板一律下沉本 skill 的 `references/` 或 `core/`，工作流步骤中显式引用执行（"此步执行 references/xxx.md 全部检查项"），不得降级为可选参考
2. **每个 skill 必须有 When NOT to Use**，且指明"交给谁"；触发措辞保持现状约定——`qa` 独占"端到端 / 帮我测试"意图词，其余 skill 的 description 均含正向触发词与反触发（"不用于…→ 对应 skill"），新增/修改 skill 时对照既有 description 的写法
3. **`core/` 不含 SKILL.md**：纯共享引用目录，加入新文件需确认至少两个 skill 消费
4. **风险等级（Critical/High/Medium/Low）与用例优先级（P0/P1/P2）是两套体系**，不得混用命名
5. **产出落盘**：skill 的阶段产物必须落盘为文件（落盘清单见各 SKILL.md 的「落盘产物」行与 `qa/SKILL.md` 的流水线表），Skill 间只通过文件衔接

## 提交前自检

- [ ] 未引入任何真实环境地址、账号、密钥、内部系统名
- [ ] `python3 scripts/validate_skills.py` 通过（与 CI 同一校验：frontmatter / SKILL.md ≤500 行 / When NOT to Use / core 纯引用 / 引用完整 / JSON 合法）
- [ ] 改动后的 skill 仍符合 [Agent Skill 规范](https://docs.claude.com/en/docs/claude-code/skills)：每个 skill 有 `SKILL.md`，frontmatter 含 `name` 与 `description`
- [ ] 改动影响用例产出的，跑一遍 Benchmark（多样本，断点续跑可重试失败项）：
      `python3 eval/harness/run_eval.py generate --samples 3 --tasks <相关任务>` + `score --samples 3`；
      判定标准以 [eval/EXPECTED.md](./eval/EXPECTED.md) 当前生效版本为准（v1.0 已冻结并完成验证轮判定，v1.1 提案见该文件）；**改过标注或 judge 配置的，先删除对应 judge/pairwise 缓存再评分**（缓存不感知上游变更）
- [ ] 客观指标（可执行性 / 编译 / 真实执行 / 植入 bug 检出）不依赖 LLM judge，回退即拦截；judge 类指标回退需先排除同源宽容偏差（成对评审大量平局是信号）
- [ ] 代码示例可独立运行，或已用占位符（如 `<你的测试环境地址>`）标注需替换处

## 许可证

提交的内容将按 [MIT](./LICENSE) 许可证发布。
