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

需要 Python 3.9+、PyYAML、Bash；完整复现 CI 还需要 Node.js 检查 dsh 插件语法。建议在虚拟环境安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install "pyyaml>=6.0"
```

**公开仓库 / 贡献者自检**（与 CI 对齐）：

```bash
python3 scripts/validate_skills.py
python3 scripts/validate_repo.py
python3 -m unittest discover -s tests -p "test_*.py"
bash -n install.sh
bash -n uninstall.sh
bash tests/install_smoke.sh
node --check .dsh/plugins/qa-skills.js
```

两个校验器分别检查 skill 架构与仓库结构 / 语法 / 文档链接 / 落地页一致性；缺 PyYAML 会报错，不会跳过 YAML 门。

**维护者本地合入门**：改 skill 或加 skill 后，除上述检查外，必须运行 `python3 -m pytest tests/ -q`（本地 harness 使用 Python 3.10+，建议 Python 3.12，并需安装 pytest；创建虚拟环境时请选择对应解释器）。本地 `tests/test_harness.py` 只能由 pytest 收集，unittest 不能替代；用例数以实际收集为准。`eval/`、harness 单测与规划文件不随公开仓库分发，外部贡献者无需补齐或运行这部分。

## 架构红线（改 skill 前必读）

1. **SKILL.md ≤ 500 行**：只装触发边界（L1）与工作流（L2）；方法 / 规则 / Checklist / 模板一律下沉本 skill 的 `references/` 或 `core/`，工作流步骤中显式引用执行（"此步执行 references/xxx.md 全部检查项"），不得降级为可选参考
2. **每个 skill 必须有 When NOT to Use**，且指明"交给谁"；触发措辞保持现状约定——`qa` 独占"端到端 / 帮我测试"意图词，其余 skill 的 description 均含正向触发词与反触发（"不用于…→ 对应 skill"），新增 / 修改 skill 时对照既有 description 的写法。**例外登记：`bug-analysis` 的 description 保持中文单语是有意决策**——三个双语变体均实测触发路由刃口新增错判（R26，按预注册回滚，见 CHANGELOG 0.9.0 与 X20 观测），勿按双语样本"补齐"
3. **core/ 是共享依赖单元**：`skills/core/SKILL.md` 仅为安装依赖单元而存在（frontmatter 显式声明"不可独立触发"，不参与任务触发竞争）；其余核心文件为纯共享引用内容，加入新内容需确认至少两个 skill 消费
4. **skill 自包含，禁止跨 skill 引用**：任何 skill 的文件不得引用兄弟 skill 目录内的文件（含另一 skill 的 SKILL.md / references / scripts）；被多 skill 消费的方法 / 格式 / 规则一律下沉 `core/`（设计方法细则放 `core/methods/`，工具脚本放 `core/scripts/`）
5. **description ≤ 300 字符**：description 常驻宿主每个会话的上下文，只装正触发话术 + 一句产出 + 反触发指向；机制细节写进 SKILL.md 正文（When to Use 等）
6. **风险等级（Critical / High / Medium / Low）与用例优先级（P0 / P1 / P2）是两套体系**，不得混用命名；Bug 严重程度用 **S0/S1/S2**（缺陷影响等级，口径说明见 `skills/core/report-template.md` §3），与用例优先级的 P 系词汇分离
7. **产出落盘**：skill 的阶段产物必须落盘为文件（落盘清单见各 SKILL.md 的「落盘产物」行与 `skills/qa/SKILL.md` 的流水线表），Skill 间只通过文件衔接
8. **跟踪面白名单，与 skills 无关的内容禁止入库**：临时文件、测试数据、实验报告、开发报告、开发计划等一律不得提交（此类内容属维护者本地评测链路，`.gitignore` 已隔离 `eval/`、`tests/test_harness.py`、`.in-situ-lab/`、`docs/` 等；营销定位与分发物料文档同归 `docs/` 本地维护）；仓库跟踪面为白名单制——git 跟踪的每个文件必须落在白名单内（根目录既有文件，含 `llms.txt`——站点根机器可读摘要、随 `pages.yml` 与落地页一同部署 + `skills/`、`scripts/`、`.github/`、`.dsh/`、`assets/`、`examples/`、`tests/` 前缀；`tests/` 仅放随产品脚本与守门脚本的回归测试及安装器冒烟，如 `test_product_scripts.py`、`test_repo_gates.py`、`test_memory_validator.py`、`install_smoke.sh`），由 `scripts/validate_skills.py` 红线 10 机器强制；`docs/` 整目录本地维护（规划文档与设计稿不入库）；新增合法产品路径须同步扩展脚本中的白名单常量并更新本条
9. **知识库 schema 与门禁同源**：`qa-memory` 的条目 schema（字段 / 枚举 / 预算 / 解析规则）定义改动必须同步 `skills/qa-memory/scripts/memory_validate.py` 与 `tests/test_memory_validator.py`（规则权威文档为 `skills/qa-memory/references/entry-schemas.md`），禁止只改文档不改门禁
10. **skills/ 下每个一级子目录必须含 SKILL.md**：skill 目录的最低合法形态（core 同样满足）；临时杂物不得放 skills/ 下——无 SKILL.md 的新目录会逃过全部 per-skill 红线，由 `scripts/validate_skills.py`（校验器 docstring 内编号 11）机器强制。注：本清单编号与校验器 docstring 的红线编号不一一对应（校验器额外含引用 / JSON / eval 等机器面条目），对外以本清单为准

## 提交前自检

- [ ] 未引入任何真实环境地址、账号、密钥、内部系统名
- [ ] `python3 scripts/validate_skills.py` 通过（与 CI 同一校验：frontmatter / description ≤300 字符 / SKILL.md ≤500 行 / When NOT to Use / core 依赖单元声明 / 引用完整含 md 链接与引用式定义 / 无跨 skill 引用 / 版本一致 / JSON 合法 / 无 eval 越界引用 / 跟踪面白名单 / skills 目录形态）
- [ ] `python3 scripts/validate_repo.py` 通过（仓库面守门：py 语法 / yml 合法性 / json / README 双语等门面文档链接 / 落地页资产引用）
- [ ] 上方公开自检通过：产品与守门单测、安装器语法与冒烟、插件语法；维护者改 / 加 skill 另跑本地 pytest 门
- [ ] 改动后的 skill 仍符合 [Agent Skill 规范](https://docs.claude.com/en/docs/claude-code/skills)：每个 skill 有 `SKILL.md`，frontmatter 含 `name` 与 `description`
- [ ] 改动影响用例产出的，在 PR 中说明预期影响（正式 Benchmark 复验由维护者在本地黄金集执行，判定标准以冻结的 EXPECTED 门为准；外部贡献者无需自行运行）
- [ ] 客观指标（可执行性 / 编译 / 真实执行 / 植入 Bug 检出）不依赖 LLM judge，回退即拦截；judge 类指标回退需先排除同源宽容偏差（成对评审大量平局是信号）
- [ ] 代码示例可独立运行，或已用占位符（如 `<你的测试环境地址>`）标注需替换处
- [ ] 文档改动同步中英文 README 与 `llms.txt` 中受影响的产品事实（安装、skill 清单、语言成熟度、兼容性）；示例数字注明指标、选样与历史轮次，不把安装验证写成效果验证
- [ ] 文档中的本地链接指向公开跟踪文件；不把维护者本地 `docs/`、`eval/` 当作读者可访问的入口

## Pull Request 流程

1. 从 `main` 拉出特性分支（如 `docs/clarify-trigger`、`skill/api-assertions`）
2. 一个 PR 聚焦一个主题；跨领域混改会拖慢评审
3. 提交信息：标题一行说清"改了什么"，正文列出关键变更与理由（可参考仓库既有提交的风格）
4. 按 [PR 模板](./.github/PULL_REQUEST_TEMPLATE.md) 勾选自检清单；涉及 skill 方法论、影响用例产出的，在评测结果一节说明预期影响
5. PR 需通过 CI（validate + label）；Skill 改动以黄金集指标不回退为合入前提（复验由维护者执行）
6. 合入后由维护者按[发版规则](./RELEASING.md)收敛对外版本——GitHub 仓、skills 市场、npm 插件市场、官网落地页四个分发面需同步

## 许可证

提交的内容将按 [MIT](./LICENSE) 许可证发布。
