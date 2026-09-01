# 贡献指南

感谢你关注 qa-skills。本文说明各类贡献的方式、架构约束与提交前自检；参与前请先阅读 [行为准则](./.github/CODE_OF_CONDUCT.md)。

## 目录

- [如何贡献](#如何贡献)
- [开发环境](#开发环境)
- [架构红线（改 skill 前必读）](#架构红线改-skill-前必读)
- [提交前自检](#提交前自检)
- [Pull Request 流程](#pull-request-流程)
- [许可证](#许可证)

## 如何贡献

- **报告问题**：先在 [Discussions](https://github.com/fishzjp/qa-skills/discussions) 确认非已知问题，再在 Issue 中描述复现场景与预期行为。
- **改进方法论**：各 skill 的工作流、检查表、模板均欢迎补充（skill 目录统一在 `skills/` 下）。改动请保持核心原则：一条用例只测一个点、代码优先（测准声明）、先澄清再动手、用例必须可执行（`skills/core/executability.md`）、证据标注（`skills/core/evidence.md`）。
- **补充代码模板**：新增的 Page Object / Helper 模板请保持通用、不绑定具体业务，且不包含任何真实账号、URL 或内部信息。
- **评测任务建议**：黄金集与评测 harness 在维护者本地链路中维护（不随公开仓库分发）；对评测任务、指标口径有想法欢迎在 [Discussions](https://github.com/fishzjp/qa-skills/discussions) 讨论。

## 开发环境

- Python 3.9+（运行校验脚本与产品脚本单测；`validate_skills.py` 等脚本显式兼容 3.9 的 `relative_to` 写法）
- 本地校验与 CI 使用同一入口：`python3 scripts/validate_skills.py`（skills 内容红线）+ `python3 scripts/validate_repo.py`（仓库面守门：py 语法 / yml 合法性 / json / 门面文档链接 / 落地页资产）；单测 `python3 -m unittest discover -s tests -p "test_*.py"`；安装器行为冒烟 `bash tests/install_smoke.sh`（eval 评测 harness 与其单测在维护者本地环境，不在公开仓库）

## 架构红线（改 skill 前必读）

1. **SKILL.md ≤ 500 行**：只装触发边界（L1）与工作流（L2）；方法 / 规则 / Checklist / 模板一律下沉本 skill 的 `references/` 或 `core/`，工作流步骤中显式引用执行（"此步执行 references/xxx.md 全部检查项"），不得降级为可选参考
2. **每个 skill 必须有 When NOT to Use**，且指明"交给谁"；触发措辞保持现状约定——`qa` 独占"端到端 / 帮我测试"意图词，其余 skill 的 description 均含正向触发词与反触发（"不用于…→ 对应 skill"），新增 / 修改 skill 时对照既有 description 的写法
3. **core/ 是共享依赖单元**：`skills/core/SKILL.md` 仅为安装依赖单元而存在（frontmatter 显式声明"不可独立触发"，不参与任务触发竞争）；其余核心文件为纯共享引用内容，加入新内容需确认至少两个 skill 消费
4. **skill 自包含，禁止跨 skill 引用**：任何 skill 的文件不得引用兄弟 skill 目录内的文件（含另一 skill 的 SKILL.md / references / scripts）；被多 skill 消费的方法 / 格式 / 规则一律下沉 `core/`（设计方法细则放 `core/methods/`，工具脚本放 `core/scripts/`）
5. **description ≤ 300 字符**：description 常驻宿主每个会话的上下文，只装正触发话术 + 一句产出 + 反触发指向；机制细节写进 SKILL.md 正文（When to Use 等）
6. **风险等级（Critical / High / Medium / Low）与用例优先级（P0 / P1 / P2）是两套体系**，不得混用命名；Bug 严重程度用 **S0/S1/S2**（缺陷影响等级，口径说明见 `skills/core/report-template.md` §3），与用例优先级的 P 系词汇分离
7. **产出落盘**：skill 的阶段产物必须落盘为文件（落盘清单见各 SKILL.md 的「落盘产物」行与 `skills/qa/SKILL.md` 的流水线表），Skill 间只通过文件衔接
8. **跟踪面白名单，与 skills 无关的内容禁止入库**：临时文件、测试数据、实验报告、开发报告、开发计划等一律不得提交（此类内容属维护者本地评测链路，`.gitignore` 已隔离 `eval/`、`tests/test_harness.py`、`.in-situ-lab/`、`docs/` 等）；仓库跟踪面为白名单制——git 跟踪的每个文件必须落在白名单内（根目录既有文件 + `skills/`、`scripts/`、`.github/`、`.dsh/`、`assets/`、`examples/`、`tests/` 前缀；`tests/` 仅放随产品脚本与守门脚本的回归测试及安装器冒烟，如 `test_product_scripts.py`、`test_repo_gates.py`、`install_smoke.sh`），由 `scripts/validate_skills.py` 红线 10 机器强制；`docs/` 整目录本地维护（规划文档与设计稿不入库）；新增合法产品路径须同步扩展脚本中的白名单常量并更新本条

## 提交前自检

- [ ] 未引入任何真实环境地址、账号、密钥、内部系统名
- [ ] `python3 scripts/validate_skills.py` 通过（与 CI 同一校验：frontmatter / description ≤300 字符 / SKILL.md ≤500 行 / When NOT to Use / core 依赖单元声明 / 引用完整含 md 链接 / 无跨 skill 引用 / 版本一致 / JSON 合法 / 无 eval 越界引用 / 跟踪面白名单）
- [ ] `python3 scripts/validate_repo.py` 通过（仓库面守门：py 语法 / yml 合法性 / json / README 双语等门面文档链接 / 落地页资产引用）
- [ ] 改动 install.sh / uninstall.sh 的，`bash tests/install_smoke.sh` 通过（copy/link 安装、重装幂等、防误删、卸载干净）
- [ ] 改动后的 skill 仍符合 [Agent Skill 规范](https://docs.claude.com/en/docs/claude-code/skills)：每个 skill 有 `SKILL.md`，frontmatter 含 `name` 与 `description`
- [ ] 改动影响用例产出的，在 PR 中说明预期影响（正式 Benchmark 复验由维护者在本地黄金集执行，判定标准以冻结的 EXPECTED 门为准；外部贡献者无需自行运行）
- [ ] 客观指标（可执行性 / 编译 / 真实执行 / 植入 Bug 检出）不依赖 LLM judge，回退即拦截；judge 类指标回退需先排除同源宽容偏差（成对评审大量平局是信号）
- [ ] 代码示例可独立运行，或已用占位符（如 `<你的测试环境地址>`）标注需替换处

## Pull Request 流程

1. 从 `main` 拉出特性分支（如 `docs/clarify-trigger`、`skill/api-assertions`）
2. 一个 PR 聚焦一个主题；跨领域混改会拖慢评审
3. 提交信息：标题一行说清"改了什么"，正文列出关键变更与理由（可参考仓库既有提交的风格）
4. 按 [PR 模板](./.github/PULL_REQUEST_TEMPLATE.md) 勾选自检清单；涉及 skill 方法论、影响用例产出的，在评测结果一节说明预期影响
5. PR 需通过 CI（validate + label）；Skill 改动以黄金集指标不回退为合入前提（复验由维护者执行）
6. 合入后由维护者按[发版规则](./RELEASING.md)收敛对外版本——GitHub 仓、skills 市场、npm 插件市场、官网落地页四个分发面需同步

## 许可证

提交的内容将按 [MIT](./LICENSE) 许可证发布。
