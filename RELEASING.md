# 发版规则（RELEASING）

> 适用对象：仓库维护者。日常改动走 [CONTRIBUTING.md](./CONTRIBUTING.md) 的提交前自检；
> 本文约束"把一批变更收敛成一个对外版本"的完整动作。当前分发渠道为 GitHub、skills 市场与官网。
> 2026-10-21 起停止 npm 插件包分发，发布无需 npm 账号或凭证。

## 分发面全景（发版 = 三面同步）

| # | 分发面 | 载体 | 更新方式 | 是否自动 |
|---|--------|------|----------|----------|
| 1 | GitHub 仓与 Release | `main` + tag `vx.y.z` + Release 说明 | 精确推送分支 / tag，并创建 Release | 手动 |
| 2 | skills 市场（`npx skills add fishzjp/qa-skills --skill '*'`） | GitHub 源，随 tag/release 可见 | 随 #1 自动获得 | ✅ |
| 3 | 官网落地页 | GitHub Pages | push 中命中 `pages.yml` 的 paths（页面、分享图、字体、`llms.txt` 或 workflow）时触发 | 条件自动 |

dsh 用户与其他宿主统一从 GitHub 安装：`./install.sh --target ~/.dsh/skills`；升级为 `git pull` 后重跑同一安装命令。迁移前通过 dsh 插件管理器移除旧插件，避免重复装载。

`package.json` 保留版本校验与历史插件兼容元数据，必须保持 `private: true`，不再作为 npm 发布清单使用。`npx` 仅用于运行第三方 skills.sh 安装器，技能内容来自 GitHub，无需发布本项目的 npm 包。

## 安装形态实测矩阵（触达安装面/引用路径的发版必登记）

`npx skills add fishzjp/qa-skills --skill '*'` 是第三方安装器，产物形态不受我方 install.sh 把控——凡影响共享依赖相对引用（`../core/`）的变更，发版前按此矩阵登记实测结果（含日期与命令）。下表是历史快照，单元数按实测当时版本记录，不能随当前 skill 数回填；安装 / 引用验证不等于触发与产出效果验证：

| # | 宿主目录 | 安装形态 | 结果 | 凭证 |
|---|---|---|---|---|
| 1 | 共享目录（沙箱实测） | 整仓 `--skill '*'` | ✅ 当轮 11 skill + core（共 12 单元）就位、`../core/` 引用完好 | 2026-09-07 营销批（7fce53f） |
| 2 | 共享目录（沙箱实测） | 单装 `--skill qa` | ❌ 不带 core（引用断，设计内）→ README 警示随行 | 同上 |
| 3 | Claude Code（`~/.claude/skills`，裸 HOME 沙箱） | 整仓 `--skill '*' -g -a claude-code` | ✅ 12 单元全就位、core 文档在位 | 2026-09-07 C0 批（0.8.0） |
| 4 | Codex 目标（`-a codex`，裸 HOME 沙箱） | 整仓 `--skill '*'` | ✅ 12 单元落位共享目录 `~/.agents/skills`（CLI 对 Codex 的承载形态，未建 `~/.codex/`）、85 处 `../core/` 引用全通、core 完整 | 2026-09-08 C0 收官批 |

## 版本号规则

遵循语义化版本与 Keep a Changelog（CHANGELOG.md 头部已声明）。

- **pre-1.0 阶段（当前 0.x）**：
  - minor 位升级 = 能力新增（新 skill 单元 / 新 core 共享文档 / 新消费钩子），如 v0.6.0（triage 分流规范）
  - patch 位升级 = 缺陷修复、文案订正、名实对齐补落，如 v0.5.1（审查修复批次）
  - 破坏性重构以 minor 位承载并在 CHANGELOG 显式标注（0.x 社区惯例）
- **tag 一律带前缀 `vx.y.z`**：install.sh 写出的 `qa-skills.VERSION` 经 `git describe --tags` 读取，裸数字会破坏安装溯源
- **CHANGELOG 工作法**：平时向 `[Unreleased]` 段累积条目；定版时改名 `[x.y.z] - YYYY-MM-DD`（保留各条目原始完成日期于正文）
- **版本三处同步由 validate_skills.py 规则 7 机械强制**（校验器自身的规则编号，非 CONTRIBUTING 架构红线表）：全部 `skills/*/SKILL.md` frontmatter `version:` ↔ `package.json` `version` ↔ CHANGELOG 存在同名小节

## 分级发版门

| 级别 | 典型场景 | 门 |
|------|----------|-----|
| patch | 修复 / 订正批次 | 流程 §1–§5 + §6 自证；**含触发面变更时追加迭代纪律门**（含下方里程碑回写项） |
| minor 及以上 | 能力新增（上文判定） | patch 全部项 **+ 迭代纪律门**（§3 追加项） |

迭代纪律门（依据 AGENTS.md，均属维护者本地评测链路，产物不进公开仓）：

- 模型矩阵常设回归：**最弱模型段位增益不回退**是一票否决项
- 只有类别性 / 大效应信号才触发 skill 变更；±2pp 级差异一律视为采样噪声
- in-situ 三数量达标：触发正确率 / 装载文件集合 / 产出质量（新增消费钩子类变更为重点观测对象）
- 对外数字发布前跑零成本污染三件套：cutoff 核对 / n-gram 扫描 / canary
- 里程碑版（minor 及以上，或含触发面变更的 patch）：总目标章程**轻轮回路已跑并回写**——维护者本地 `docs/GOAL.md` §6 有当版轮次记录（规划文件不入库，本检查单仅登记完成状态）

## 标准发版流程（按序执行）

### §1 内容完备性审查 —— 防"宣称了但没落地"

- [ ] CHANGELOG `[Unreleased]` 段逐条核对：条目声称的每个文件真实存在、行为与描述一致
- [ ] CHANGELOG 底部链接区随版前移：`[Unreleased]` 指向 `{V_NEW}...HEAD` 并补齐新版本 compare 定义（防止断更多版）
- [ ] 新增 / 下线 skill 已同步中英文 README 的完整技能表；共享文档已同步 `skills/core/SKILL.md` 索引，用户入口已进 README 文档导航。结构树只列目录职责，避免重复维护全量文件清单
- [ ] README 中英文与 `llms.txt` 的安装步骤、依赖、语言成熟度、兼容性及指标口径一致；历史数据注明轮次 / 限制，未重新评测不得改写成当前版本保证
- [ ] `index.html` 若含指标 / 能力宣称，口径与最新勘误后的证据一致（不得挂已证伪旧叙事）
- [ ] 本次变更涉及的任务若用于评测对照，GT 已双人复核

### §2 机械同步 —— 版本号与随动字段

固定项（每版必做，锚定行首防误伤正文提及旧版本的文字）：

```bash
V_NEW="0.7.0"; V_OLD="0.6.0"   # ← 换成本次目标值
# 函数级说明：锚定 frontmatter 整行做版本替换，避免 sed 撞上正文中的历史版本字样
grep -rl "^version: ${V_OLD}$" skills/*/SKILL.md | wc -l        # 预检：结果应等于实际 skills/*/SKILL.md 文件数（含 core）
sed -i '' "s/^version: ${V_OLD}$/version: ${V_NEW}/" skills/*/SKILL.md
sed -i '' "s/\"version\": \"${V_OLD}\"/\"version\": \"${V_NEW}\"/" package.json
git diff --stat                                                  # 复验：每个文件仅 version 行变动
```

随后 CHANGELOG 定版：`## [Unreleased]` → `## [x.y.z] - YYYY-MM-DD`。

条件项（命中才做，漏掉会在下游渠道炸）：

| 触发条件 | 必做同步 |
|----------|----------|
| 定版触及 `index.html`（或每版例行） | `index.html` JSON-LD `softwareVersion` 随版本号同步（0.9.0 审查发现该字段曾停更两个版本——GEO 层的机器可读事实不得陈旧） |
| 新增 / 下线 skill 单元 | 安装器清单自动派生自 `skills/*/SKILL.md`（install.sh / uninstall.sh 无需改清单）；package.json description 中的 skill 计数与枚举；双语 README 技能表与徽章、`llms.txt` skill 清单与计数；`tests/install_smoke.sh` 的单元数下限与 bug_report.yml 问题区域下拉（如适用）；`index.html` ticker 枚举与 featureList 能力项；`.dsh/plugins/qa-skills.js` 文件头注释的技能计数（历史兼容代码中的事实陈述） |
| 新增 / 下线 core 共享文档 | `skills/core/SKILL.md` 的完整索引与 README 中受影响的说明；涉及指纹文件的更名需同改 `install.sh`/`uninstall.sh` 的 `owns_unit` 判据 |
| core 文档在触发措辞上影响其他 skill | 相互指向的 description / When NOT to Use 同步修订 |

（dsh 插件**运行时**无需任何随动：`.dsh/plugins/qa-skills.js` 以 `readdirSync` 动态枚举 skills 目录；文件头注释计数属上表同步项。）

### §3 测试关

```bash
python3 scripts/validate_skills.py
python3 scripts/validate_repo.py
python3 -m unittest discover -s tests -p "test_*.py"
node --check .dsh/plugins/qa-skills.js
bash -n install.sh
bash -n uninstall.sh
bash tests/install_smoke.sh
```

维护者改 skill / 加 skill 后还必须运行 `python3 -m pytest tests/ -q`，包含本地 harness 单测；unittest 不能替代该门。详细依赖见 [CONTRIBUTING 开发环境](./CONTRIBUTING.md#开发环境)。

本地全部检查通过后进入 §4；§5 推送后观察 CI「架构红线与语法校验」job 为绿，再继续发布其余分发面。

minor 及以上追加（本地链路）：按分级门跑模型矩阵 + in-situ，结论写入本次 CHANGELOG 条目或 Release notes。

### §4 隔离面审查 —— 进公开仓最后一道

- [ ] `git diff --cached --name-only` 暂存清单不含 `eval/`、`tests/test_harness.py`、`.in-situ-lab/`、`docs/` 等本地评测 / 规划产物（`tests/` 下已跟踪的产品回归测试与安装器冒烟允许提交）（.gitignore 已隔离，但要肉眼复核）
- [ ] 工作区 `skills/*/SKILL.md` 的单元集合与 `git ls-files skills/` 中已跟踪的单元集合一致。安装器按工作区取文件，未跟踪草稿也会被安装；草稿放本地暂存区，过门合入时再进 `skills/`
- [ ] `package.json` 保持 `private: true`；README / 官网 / `llms.txt` 无 npm 插件安装命令、包下载入口或 npm 发布承诺
- [ ] 无真实环境地址、账号、密钥、内部系统名（CONTRIBUTING 自检第 1 条）
- [ ] 跟踪面白名单校验通过（validate_skills.py 红线 10 随 §3 测试关自动执行；`git ls-files` 中不得出现临时文件、测试数据、实验·开发报告、开发计划等与 skills 无关内容，白名单维护规则见 CONTRIBUTING 架构红线 8）

### §5 发布动作（三面依次）

```bash
# 1) 提交：中文单行概要体例，覆盖本轮全部实质变更
git add -A && git commit -m "<单行概要>"

# 2) 打标
git tag v0.7.0                                 # ← 用本次实际版本

# 3) 推送 #1/#2：分支与 tag 精确推送
git push origin main
git push origin v0.7.0                         # 禁止 --tags：会重推全部历史 tag，已被拒项制造噪音报错
```

- GitHub Release 页：贴 CHANGELOG 对应节原文，并附跨模型增益矩阵快照（README 对外承诺：快照按里程碑随 Release 附带；非里程碑小版本无新数据时，贴完整表格并标注"数据沿用 vX.Y.Z"或不贴并在 body 说明）
- 官网：按 `.github/workflows/pages.yml` 的实际 paths 检查本次变更（含 `llms.txt`、字体与 workflow 本身）；命中时确认 pages workflow 部署成功，未命中且无需更新时登记理由

### §6 发布后自证

- [ ] 安装冒烟：`./install.sh --target <临时目录>`，核对输出尾部 `✅ 完成。版本：v0.7.0` 与 `qa-skills.VERSION` 文件内容为新 tag
- [ ] skills 市场：GitHub Releases 页新 release 可见（npx skills add 按 GitHub 源拉取）
- [ ] GitHub Release：`gh release list` 核对最新 tag 在列且为 Latest；逐渠道记录完成凭证（URL / 输出摘要），无需更新时也登记理由
- [ ] dsh 安装：临时目标目录安装后包含全部 skill 与 core；确认文档引导使用 Git 安装
- [ ] 官网：需要部署时确认 Pages workflow 成功，双语页面与复制的命令均使用当前安装方式

## 历史经验与渠道变更

- **2026-10-21 渠道裁决**：停止 npm 插件包分发，不再执行 npm 发布、补版或版本同步。历史 CHANGELOG 中的 npm 发布记录仅描述当时状态，不是当前安装指引。
- **精确推送 tag**：使用单个 tag 的 push，避免 `--tags` 重推全部历史 tag。
- **声明与文件一致**：CHANGELOG 声称的修复必须在工作区中逐条核验；版本替换锚定 frontmatter 整行，避免修改历史正文。
- **工作区与发布源一致**：安装器会读取未跟踪的技能草稿，因此发布前要核对工作区与 git 跟踪集合；运行缓存不得进入宿主。
- **push tag 不等于创建 Release**：GitHub 仓、skills 市场和官网各自验证完成，不能凭一个渠道推断其余渠道已更新。
