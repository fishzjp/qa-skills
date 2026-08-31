# 发版规则（RELEASING）

> 适用对象：仓库维护者。日常改动走 [CONTRIBUTING.md](./CONTRIBUTING.md) 的提交前自检；
> 本文约束"把一批变更收敛成一个对外版本"的完整动作。qa-skills 有四个对外分发面，
> `git push` 只覆盖其中两个——其余靠本检查单兜住，缺一项就是用户拿不到该拿的东西。

## 分发面全景（发版 = 四面同步，漏一即事故）

| # | 分发面 | 载体 | 更新方式 | 是否自动 |
|---|--------|------|----------|----------|
| 1 | GitHub 仓 | `main` + tag `vx.y.z` | `git push` | 手动 |
| 2 | skills 市场（`npx skills add fishzjp/qa-skills`） | GitHub 源，随 tag/release 可见 | 随 #1 自动获得 | ✅ |
| 3 | **dsh 插件市场**（npm 包 `dsh-qa-skills`） | npmjs.com | `npm publish` | ❌ **必须手动** |
| 4 | 官网落地页 | GitHub Pages | push 中 `index.html`/`assets/og.jpg`/`assets/landing/**` 变更触发 `pages.yml` | 条件自动 |

反面实例：v0.5.1、v0.6.0 均只完成了 #1，npm 侧停留在 0.5.0（详见文末踩坑记录）。

## 版本号规则

遵循语义化版本与 Keep a Changelog（CHANGELOG.md 头部已声明）。

- **pre-1.0 阶段（当前 0.x）**：
  - minor 位升级 = 能力新增（新 skill 单元 / 新 core 共享文档 / 新消费钩子），如 v0.6.0（triage 分流规范）
  - patch 位升级 = 缺陷修复、文案订正、名实对齐补落，如 v0.5.1（审查修复批次）
  - 破坏性重构以 minor 位承载并在 CHANGELOG 显式标注（0.x 社区惯例）
- **tag 一律带前缀 `vx.y.z`**：install.sh 写出的 `qa-skills.VERSION` 经 `git describe --tags` 读取，裸数字会破坏安装溯源
- **CHANGELOG 工作法**：平时向 `[Unreleased]` 段累积条目；定版时改名 `[x.y.z] - YYYY-MM-DD`（保留各条目原始完成日期于正文）
- **版本三处同步是红线 7**（validate_skills.py 机械强制）：全部 `skills/*/SKILL.md` frontmatter `version:` ↔ `package.json` `version` ↔ CHANGELOG 存在同名小节

## 分级发版门

| 级别 | 典型场景 | 门 |
|------|----------|-----|
| patch | 修复 / 订正批次 | 流程 §1–§5 + §6 自证 |
| minor 及以上 | 能力新增（上文判定） | patch 全部项 **+ 迭代纪律门**（§3 追加项） |

迭代纪律门（依据 AGENTS.md，均属维护者本地评测链路，产物不进公开仓）：

- 模型矩阵常设回归：**最弱模型段位增益不回退**是一票否决项
- 只有类别性 / 大效应信号才触发 skill 变更；±2pp 级差异一律视为采样噪声
- in-situ 三数量达标：触发正确率 / 装载文件集合 / 产出质量（新增消费钩子类变更为重点观测对象）
- 对外数字发布前跑零成本污染三件套：cutoff 核对 / n-gram 扫描 / canary

## 标准发版流程（按序执行）

### §1 内容完备性审查 —— 防"宣称了但没落地"

- [ ] CHANGELOG `[Unreleased]` 段逐条核对：条目声称的每个文件真实存在、行为与描述一致
- [ ] CHANGELOG 底部链接区随版前移：`[Unreleased]` 指向 `{V_NEW}...HEAD` 并补齐新版本 compare 定义（防止断更多版）
- [ ] 新增文件已进 README（中/英双份）的结构树与关键文档区——结构树是穷举不是举例
- [ ] `index.html` 若含指标 / 能力宣称，口径与最新勘误后的证据一致（不得挂已证伪旧叙事）
- [ ] 本次变更涉及的任务若用于评测对照，GT 已双人复核

### §2 机械同步 —— 版本号与随动字段

固定项（每版必做，锚定行首防误伤正文提及旧版本的文字）：

```bash
V_NEW="0.7.0"; V_OLD="0.6.0"   # ← 换成本次目标值
# 函数级说明：锚定 frontmatter 整行做版本替换，避免 sed 撞上正文中的历史版本字样
grep -rl "^version: ${V_OLD}$" skills/*/SKILL.md | wc -l        # 预检 SYNC COUNT = skill 目录数（当前 11）
sed -i '' "s/^version: ${V_OLD}$/version: ${V_NEW}/" skills/*/SKILL.md
sed -i '' "s/\"version\": \"${V_OLD}\"/\"version\": \"${V_NEW}\"/" package.json
git diff --stat                                                  # 复验：每个文件仅 version 行变动
```

随后 CHANGELOG 定版：`## [Unreleased]` → `## [x.y.z] - YYYY-MM-DD`。

条件项（命中才做，漏掉会在下游渠道炸）：

| 触发条件 | 必做同步 |
|----------|----------|
| 新增 / 下线 skill 单元 | `install.sh` 的 `SKILL_DIRS` 数组；`uninstall.sh` 清单对齐；package.json description 中的 skill 计数；双语 README 结构树计数与行列排布 |
| 新增 / 下线 core 共享文档 | 双语 README 结构树 core 行的文档枚举；涉及指纹文件的更名需同改 `install.sh`/`uninstall.sh` 的 `owns_unit` 判据 |
| core 文档在触发措辞上影响其他 skill | 相互指向的 description / When NOT to Use 同步修订 |

（dsh 插件侧无需任何随动：`.dsh/plugins/qa-skills.js` 以 `readdirSync` 动态枚举 skills 目录。）

### §3 测试关

```bash
python3 scripts/validate_skills.py            # 架构红线全绿，退出码 0（与 CI 同一校验）
node --check .dsh/plugins/qa-skills.js       # 仅插件单元有改动时：语法通过
bash -n install.sh && bash -n uninstall.sh  # 仅安装器有改动时：语法通过
npm pack --dry-run                           # 触达发包范围时必跑：清单里不得出现 __pycache__/*.pyc 等运行时产物（踩坑 6）
```

push 后观察 CI「架构红线与语法校验」 job 为绿再进入 §4（skills 市场 #2 的可见性以 CI 绿为前提）。

minor 及以上追加（本地链路）：按分级门跑模型矩阵 + in-situ，结论写入本次 CHANGELOG 条目或 Release notes。

### §4 隔离面审查 —— 进公开仓最后一道

- [ ] `git status --short` 暂存面不含 `eval/`、`tests/`、`.in-situ-lab/` 等本地评测产物（.gitignore 已隔离，但要肉眼复核）
- [ ] 无真实环境地址、账号、密钥、内部系统名（CONTRIBUTING 自检第 1 条）
- [ ] 跟踪面白名单校验通过（validate_skills.py 红线 10 随 §3 测试关自动执行；`git ls-files` 中不得出现临时文件、测试数据、实验·开发报告、开发计划等与 skills 无关内容，白名单维护规则见 CONTRIBUTING 架构红线 8）

### §5 发布动作（四面依次）

```bash
# 1) 提交：中文单行概要体例，覆盖本轮全部实质变更
git add -A && git commit -m "<单行概要>"

# 2) 打标
git tag v0.7.0                                 # ← 用本次实际版本

# 3) 推送 #1/#2：分支与 tag 精确推送
git push origin main
git push origin v0.7.0                         # 禁止 --tags：会重推全部历史 tag，已被拒项制造噪音报错

# 4) 推送 #3 npm 插件市场（手动强制项！）
NPM_REGISTRY="https://registry.npmjs.org"    # 本机默认源可能是 npmmirror 只读镜像（踩坑 5），一律显式官方源
npm whoami --registry "$NPM_REGISTRY"        # 未登录先：npm login --registry "$NPM_REGISTRY" --auth-type=web
npm view dsh-qa-skills version --registry "$NPM_REGISTRY"   # 预检：latest ≠ 本次版本（既防重发、也暴露断档）
npm pack --dry-run                           # 清单核对：仅 skills 与 .dsh 本体，无 pyc 缓存（踩坑 6）
npm publish --registry "$NPM_REGISTRY" --otp="<验证器当前6位动态码>"   # 强制 2FA 下必带第二因子（踩坑 7）
npm view dsh-qa-skills version --registry "$NPM_REGISTRY"   # 复验：latest == 本次版本
```

- \#4 GitHub Release 页：贴 CHANGELOG 对应节原文，并附跨模型增益矩阵快照（README 对外承诺：每版 Release 附快照）
- \#5 官网：本次若未触碰 `index.html`/`assets/og.jpg`/`assets/landing/` 则 pages 不触发、无需动作；触发了则确认 pages workflow 部署成功

### §6 发布后自证

- [ ] 安装冒烟：`./install.sh --target <临时目录>`，核对输出尾部 `✅ 完成。版本：v0.7.0` 与 `qa-skills.VERSION` 文件内容为新 tag
- [ ] skills 市场：GitHub Releases 页新 release 可见（npx skills add 按 GitHub 源拉取）
- [ ] 插件市场：任一新环境 `dsh plugin add dsh-qa-skills` 拉到新版本且注册数量日志正常
- [ ] npm 断档自查归零：`npm view dsh-qa-skills versions` 中最大值 == git 最新 tag

## 历史踩坑记录（本规则的由来）

1. **npm 断档**（2026-08-27 发现）：v0.5.1、v0.6.0 只推了 GitHub，npm latest 停在 0.5.0——插件市场用户长期拿不到增量。§5 第 4 步因此列为强制项。
2. **`--tags` 重推噪音**：v0.6.0 发布时 `git push origin main --tags` 把 v0.1.0–v0.4.0 一并重推，远端已存在被拒、退出码非 0。改为精确推送单个 tag。
3. **名实分离**（第五轮审查）：发布文案宣称的修复在实际写盘时静默丢失。由此确立"同文件串行编辑 + 每批写盘即回验"协议，以及 §1 的逐条实体核对。
4. **sed 误伤正文**：版本替换若不锚定行首（`^version: x\.y\.z$`），会改掉正文中作为历史叙述出现的版本字样。§2 固定命令已内置防御。
5. **默认源是 npmmirror 只读镜像**（2026-08-27 补发实战）：本机 npm 默认 registry 指向淘宝镜像，镜像不能 publish，首次 `npm login` 会把人带去 `registry.npmmirror.com` 空转。§5 第 4 步所有 npm 命令因此一律显式 `--registry https://registry.npmjs.org`。
6. **pyc 编译缓存混入发包**（2026-08-27 补发实战；2026-08-28 复发修正）：发包前核对 tarball 清单，发现 `skills/core/scripts/__pycache__/*.pyc` 入包（38 files）。npm 的 `files` 白名单是目录级，兜不住运行时生成的缓存子目录；处理 = 即时删除 + 根级 `.npmignore`（排除 `__pycache__/`、`*.pyc`），并把 `npm pack --dry-run` 固化为 §3 测试关与 §5 第 4 步的固定动作。复核后 37 files 干净入站。**2026-08-28 复发**：根级 `.npmignore` 拦不住 `files` 白名单内路径（pyc 再次入包、40 files）——真正根治 = `package.json` `files` 数组加否定模式（`!skills/**/__pycache__`、`!skills/**/*.pyc`），dry-run 复核 38 files、pyc 计数 0。
7. **npm 发布认证新政：EOTP/E403 两段墙**（2026-08-27 补发实战）：publish 必须携带第二因子，且策略因账号而异——绑定 TOTP 时报 `EOTP`（等码）；关掉 2FA 或使用未获 bypass 授权的令牌反而报 `E403`（"Two-factor authentication or granular access token with bypass 2fa enabled is required"）。另据官方公告，bypass-2fa 细粒度令牌正被限制直接发布——令牌路线是死路。正解：①账号 Two-Factor Authentication 以 Authenticator App 方式绑定（服务端 `two-factor auth: auth-and-writes` 即就绪）②发版用 `npm publish --otp=<当前6位动态码>`。实测兜底：CLI 的 `--otp` 位也接受恢复码（每条一次性消耗），验证器不在手边时可应急；恢复码已多次暴露的应整体重新生成。
8. **push tag ≠ GitHub Release 已建**（2026-08-27 补发实战）：v0.6.0 当轮全副精力陷在 npm 认证墙（踩坑 7）里，§5 的 #4 步（Release 页）被执行悬空——tag 推上远端后被心理上当作"已发布完毕"，直到用户质疑才经 `gh release list` 发现 v0.4.0–v0.5.1 三条在列而 v0.6.0 缺席。教训：四个分发面互不等价、彼此独立可见，任一面都不会替另一面兜底；checklist 靠记忆执行必然有洞，且某一面反复排障时会挤占其余面的注意力——恰恰是洞最可能出现的位置。由此固化两条纪律：①§5 逐面执行后各写一行完成凭证（URL / 命令输出摘要），**本面确认无需动作也必须显式写下"不动的理由"**，禁止留白跳过；②§6 自证须包含 `gh release list` 核对最新 tag 在列且为 Latest——这是所有"以为发了实际没发"类断档的统一兜底探针。
