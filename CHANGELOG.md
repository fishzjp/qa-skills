# 更新日志

本项目所有显著变更都记录在此，格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 变更

- **全面审查修复**（第三轮审查闭环，2026-08-26）：**对外物料**——落地页 API 行改为复验口径
  100% / 99.2% 并撤下已证伪的"严断言"归因（页面此前仍挂 74% → 52% 旧叙事，与 README
  勘误冲突）；`pages.yml` 随单文件补部署 `og.jpg`（og:image 绝对 URL 指向它、此前分享图必然
  404）；落地页运行时生图补端点故障本地兜底（内联 SVG 占位 + no-referrer）。**文档同步**——
  CONTRIBUTING 架构红线 3 与 DESIGN 硬规则 5 改写为 core 依赖单元现实（原文"core 不含
  SKILL.md"与现状矛盾，CHANGELOG 的红线编号指称一并改为按名指称）；qa-skills-v2 对目录树 /
  core 硬规则 / type 枚举三处冻结表述补演进注记；DESIGN 如实披露条目为 API 反转加历史定案
  限定；英文 README 补 DESIGN 章节指针与仓库结构注释对齐中文信息量。**skills 本体**——
  api-testing 两处向用户提问接线 clarify-pattern（clarify-pattern 宣称其为消费者却从未被引用，
  "问题卡片跨 skill 同构"承诺在此漏接）；qa frontmatter 流水线词序对齐正文阶段表（"风险分析"
  独立环节 → 并入测试策略）；轴 2 补 `[安全]` 标签消费规格；风险扫描五维 ↔ scope 六轴映射
  落进 risk-model dimension 注释；e2e 去唯一英文 Overview 标题；test-case-review Schema 复验
  由"可用"改强制措辞；test-case-writing"修复 v3"记法消歧为日期描述。**工具链**——
  validate_skills.py 新增三类检查并经负向自测：core 内裸相对引用存在性 / markdown 链接目标
  存在性 / 全部 SKILL.md version ↔ package.json 一致性（发版三处同步的机械防线），eval 缺省时
  明示跳过不再静默假绿；install.sh 重装前归属校验（slug 指纹与 uninstall 对齐——共享目录中
  其他框架同名 qa/core 不再被无声覆盖删除）、uninstall.sh 非 core 目录认领收紧到 slug 指纹 +
  补 --auto 参数对称；scan_signals.py 补可执行位；core 内部互引统一规范为自所在文件可解析的
  相对路径写法（markmap 模板 2 处补 ../../ 前缀）。提交前自审补漏四处：uninstall
  的 -h 输出随新增行扩范围（--auto 用法此前漏打）、pages.yml 触发条件纳入 og.jpg
  （否则单独换图不重新部署）、校验器版本检查改为单次 frontmatter 解析复用、
  CONTRIBUTING 红线 5 去除已删 Overview 标题的示例指称。第三轮（环境 / 线上 /
  一致性视角）复审新增一修复：markmap 模板模块 16 补 `[安全]` 标签注，对齐其余
  类型域模块的标签注写法与矩阵轴 2 的标签规格。
- **README 实测表 API 行改用修复后复验口径**（勘误，2026-08-26）：「API 代码真实执行
  通过率」一行由历史反向结果（无/有 skill 组 74% / 52%）改为契约与截断修复后的干净
  复验值（**100% / 99.2%**，差距 0.8pp，n=3 噪声带内，反转消除；弱模型段位同向
  0.30 / 0.67）。上一轮勘误只更新了脚注归因、表格头条仍挂旧数字，造成"表格说存在
  反转、脚注说反转消除"的名实不符；本次对齐「用例规格符合度」（0.77 → 0.26/0.98
  勘误留档）的既有处理模式——表格放当前口径，历史数字与根因定案完整保留在逐项口径
  注。英文版同步。
- **产物链路末端闭环**（第二轮全面审查修复，2026-08-25）：① **Bug 生命周期状态字段**——
  report-template §3 条目新增"状态"（新建 / 已修复待验证 / 已验证关闭 / 不予修复），
  使用约定 6 定义回归驱动的状态同步规则；qa 收尾按回归结果逐条同步、regression-testing
  §4 衔接、bug-analysis 字段枚举同步（前 7 → 前 8）——修复"风险有状态列而 Bug 没有"的
  闭环不对称（ISTQB 缺陷生命周期在产物层的最后断点）。② **手动执行路径结果回流**——
  qa 阶段 5 手动路径定义落盘产物 `手动执行记录_{日期}.md`（TC × 结果）与 ⏸ 结果回收
  检查点，作为报告 §2 执行统计的数据来源——修复"手动路径无产物、未执行列成永久状态"
  的自动/手动不对称。③ **上轮修改的下游接线**——report-template §1 新增"范围假设"
  标注位（系统级黑盒结论的前提是否已验证），使用约定 2 为 api-testing 结构覆盖摘要
  提供正式挂靠；顺带消除使用约定 3 与 bug-analysis 之间的循环权威引用（统一为
  report-template §3 唯一来源）。④ **校验器补轴 2 硬默认告警**——validate_schema.py
  V3 对 security_business exclude 且 rationale 未声明非 Web/API 依据时告警级提示复核
  （矩阵 §4：Web/API 系统无排除出口），双用例验证通过。⑤ **探索启发式补 HTSM 的
  P/T 两维**（平台与环境 / 时间与时钟），SFDIPOT 主干补全。
- **组合测试降档策略 + 系统级范围声明 + 结构覆盖补充证据**（专业性审查闭环，2026-08-25）：
  ① `core/methods/data-driven.md` 新增第 2 节"多参数组合降档策略"——全组合 /
  成对组合（pairwise，默认档）/ 风险挑选三档显式选档，降档与被排除组合面留痕；
  依据 NIST 实证（Kuhn et al. 2004）：参数交互类缺陷约 70% 以上可被两两组合捕获。
  补齐 ISTQB 黑盒技术体系中组合测试的缺位——原"逐参数 × 逐属性"在大参数面接口
  上组合爆炸或静默漏测；api-testing 用例设计与 Common Mistakes 补执行点，
  testing-principles 方法表 API 行补路由。② test-strategy 边界补**系统级黑盒范围
  假设声明**（单元/集成测试为开发侧职责，风险评级与"已覆盖"结论以该层已有保障为
  前提，落盘时进入策略文档开头）——防"系统级全过 = 质量有保障"的无错谬论式误读。
  ③ api-testing 运行结果补**可选结构覆盖补充证据**（被测服务可插桩时取行/分支
  覆盖率，只用于发现零覆盖/低覆盖的漏测信号，不作追高虚荣指标，无插桩不阻塞
  交付）——补齐测试充分性三支柱（需求 / 风险 / 结构）中的结构维度。
- **DeepSeek Harness（dsh）插件化发布**：新增 dsh Cordis 插件三件套（`package.json`
  的 `dsh.bundle` manifest、`.dsh/cordis.patch.yml` 补丁层、`.dsh/plugins/qa-skills.js`
  注册器——Node 内建零依赖，参照 superpowers 的 dsh 适配模式），已发布至 npm
  （[`dsh-qa-skills@0.5.0`](https://www.npmjs.com/package/dsh-qa-skills)，MIT、零依赖；
  发布动作发生在 v0.5.0 tag 之后、包版本随内容基线取 0.5.0，故记于本 Unreleased 段），
  `dsh plugin --profile web add dsh-qa-skills` 一键安装；已提交 awesome-dsh-plugin
  收录 PR #3068（skill 分类）。core 单元
  在插件注册时标记双不可调用（modelInvocable/userInvocable 均为 false），技能目录中
  不再出现——比文件安装路径更干净（文件路径下 core 会进目录，靠 description 免触发）。
  端到端实测（dsh 0.1.0-rc.8 + deepseek-v4-flash 最弱段位）：文件路径与插件路径双轨
  验证——11 单元识别 / 中文 description 触发 / 阶段〇索取仓库 / markmap+schema 双产物
  落盘（24 条用例）/ `../core/*` 按需加载 / core/scripts/validate_schema.py 被正确调用；
  npm 包安装路径复验通过（10/10 注册、core 隐藏）。
  双轨均发现同一弱点：v4-flash 对 `../` 相对路径存在解析抖动（一次正确一次丢 `../`），
  已作为 dogfooding 案例记入迭代池候选。`install.sh`/`uninstall.sh` 增加 `~/.dsh/skills`
  检测，README 双语增补 dsh 安装说明与兼容性矩阵行。
- **分发渠道接入 skills.sh（`npx skills`，Vercel Labs 开放技能生态，50+ Agent 宿主）**：
  `npx skills add fishzjp/qa-skills` 即装（全装 `--skill '*'`）。上架适配：`core/` 新增
  非触发型 SKILL.md（声明仅被引用、不独立执行任务），使其成为安装器可识别的依赖单元——
  此前安装器只复制含 SKILL.md 的目录，core 会被丢弃导致全部 `../core/` 引用断裂。
  架构红线同步：core 条目由"core 禁含 SKILL.md"演进为内容检查（SKILL.md 必须声明
  不独立触发）；跨 skill 引用禁令将 core 排除出判定（skill → core 合法不变）。隔离环境双源验证
  （本地路径 + GitHub 源）：11 个单元全部落地，core/scripts 完整，引用路径有效。
  skills.sh 排行榜为安装驱动（无提交入口），用户真实安装即自动上榜。
- **国内渠道上架腾讯 SkillHub（skillhub.cn，skillId 172576 起 11 个单元）**：v0.5.0
  全量发布，进入三线审核（内容合规 / 科恩漏洞扫描 / 云鼎 AI 安全评估）。发布元数据
  （slug / displayName / version）以开放规范扩展字段写入各 SKILL.md frontmatter，
  不影响 skills.sh 渠道（dry-run 预检与 npx skills 复测均通过）。附带确认：npx skills
  原生支持 Trae / Trae CN 宿主（`-a trae-cn` 实测落地 `~/.trae-cn/skills/`），
  skills.sh 上架已自动覆盖字节 Trae 生态；SkillsMP（skillsmp.com）为自动抓取，
  GitHub push 后自行收录。

- **测试数据守约束扩展到跨字段业务规则**（test-case-writing + api-testing 各一条分句）：
  参数矩阵逐参数独立变化时，每格组合回检材料声明的跨字段规则（如"使用门槛不能低于面额"），
  违反规则的组合改取合法值或拆为显式负向用例。依据：glm-5.2 干净复验 On 臂 155 个测试中
  唯一失败用例的取证（2026-08-24）——金额顶格 1000 配低于面额的门槛，被 mock 按业务规则
  正确拒绝（400 THRESHOLD_INVALID）而用例期望 201；与 maxLength 自伤同族（数据自建缺陷
  第二例），属字段约束纪律的跨字段补全而非新机制。
- **API 反转最终定案（glm-5.2 干净复验，2026-08-24 晚）**：修复链全落地后（任务契约
  状态机补全 + 登录响应契约补全 + 撞顶续写 + 续写接缝围栏修复 + 文件横幅剥离），
  主模型段位干净复验：无/有 skill 组 **100% / 99.2%**（差距 0.8pp，n=3 噪声带内），
  反转彻底消除；弱模型段位同向（0.67 > 0.30）。README 双语实测表 API 行脚注同步
  更新为定案根因 + 修复后数字。注：api-openapi-coupon 任务材料已补登录契约，
  该任务后续跑数须新开 run 目录。
- **README 双语 API 反转归因勘误**：实测表 API 行的脚注由"严断言更易暴露失败"（已被
  2026-08-24 逐失败归类证伪：46 个失败中仅 4 个与断言强度相关，且属超出书面契约的
  过严断言）改为已定案根因：评测任务契约状态机断裂（无发布路径，题目缺陷）为主因，
  叠加输出截断与采样退化。
- **撞顶续写协议端到端验证 + 二阶效应修复（本地评测链路）**：续写在真实 run 中触发闭环
  （mimo 14K 上限：撞顶→续写→接缝干净→usage 累加→合并产物真实执行收集 46 测试）。
  验证中发现并修复续写二阶效应：续写会重发已输出文件（缩短版），exec 组装"后写覆盖"
  冲掉截断前完整原件——改为**先写优先**并强化续写指令。另两项修复：exec 阶段按模型 tag
  遍历产物（此前 `--model` 运行的产物被整体跳过）；exec 0 收集补 detail 标注（与全挂
  可区分）。附注：zen 端点对 deepseek-v4-flash 无视 max_tokens（18–39K 报 stop），撞顶
  实验只能用尊重上限的模型（mimo 精确生效）。README 双语 Token 成本口径补基准标注
  （任务级均值、含全量注入；主模型轮 3.3× / 弱模型轮最高 9.5×）。
- **撞顶续写协议 + 产物提取双修复（本地评测链路测量修复）**：①finish_reason 全链路透传 +
  `call_model_cont` 撞 max_tokens 续写一轮（On/Off 对称、usage 跨轮累加如实计成本、
  接缝重叠剥离），meta 落档 finish_reason/continued，truncation 统计进 metrics 与报告；
  ②`extract_code_blocks` 两处缺陷：markdown 转义下划线文件头（`test\_a\_b.py` 被切成
  `_a_b.py` → pytest 收集 0 测试记 0 分）与文件提示优先级（markdown 标题笔误压过代码
  首行注释 → 文件写错位置炸掉全部收集）。依据（本地评测链路存档，2026-08-24 撞顶
  与成本构成诊断 + 复跑验证）：撞顶系统性只打 On 臂——flash 段位 R3 前 32%、
  v4-pro hardened 任务 3/6 撞顶；mimo 30720 撞顶样本可见产物仅 5.8KB（~29K token 为
  推理开销）；提取双 bug 实测把复跑轮 On 臂执行分从 0.667 记成 0.33（腰斩）。skills
  本轮不动（绑定约束在推理侧与测量层，证据不支持顺序倒置等 skill 改动）；受影响段位
  （flash / v4-pro hardened / 弱模型执行分）的历史增益数字修复复跑前慎引。另加裁判
  同族披露（同族自评虚高 ~10pp，Wataoka 2024）。
- **测试数据守约束纪律**（test-case-writing 输出预算纪律新增一条 + api-testing 数据自建条目扩展）：
  生成的测试数据/唯一名模板须先核对材料声明的字段约束（maxLength/枚举/格式）并预留余量（模板总长
  ≤ 约束上限 −2）。依据：api-openapi-coupon 任务执行侧取证（2026-08-24）——唯一名模板 22 字符
  撞契约 maxLength 20，整条用例 NAME_INVALID 自伤；与 R3 输出预算纪律同源（用例有条数预算，
  数据自身也有约束预算）。

## [0.5.0] - 2026-08-24

决策层 Phase A + skills 自包含架构 + 仓库收敛为产品本体（v0.4.0 后 19 提交，60 文件）。
本版 Release 附跨模型增益矩阵快照（核心指标 + 决策层 flash/glm-5.2 两段位矩阵）与
飞轮迭代记录（R1 格式锤闭环）；发布前污染三件套全过（cutoff 核对 / n-gram 扫描 /
canary，见本地评测链路存档）。

### 变更

- **公开仓库收敛为 skills 产品内容**（2026-08-22 决定，本次落地）：eval/（黄金集 /
  harness / 运行归档 / 研究报告）、tests/（harness 单测）与 benchmark workflow
  移出公开仓库、转为本地维护（.gitignore 防误提交）；公开面收敛为 skills 产品
  本体 + 设计文档（DESIGN / 决策层设计 / v2 规划）+ examples + 安装与 CI 链路。
  公开证据链改为：每版 Release 附跨模型增益矩阵快照。README / CONTRIBUTING /
  .github 模板同步清理指向本地目录的死链，仓库结构说明同步更新。**本节涉及
  eval/ / tests/ 的既有条目描述的是本地评测链路的变更，不随仓库分发**
- **决策层（精准测试）Phase A 落地**：测试策略升级为**功能域 + 类型域两域决策**——
  类型域十轴（性能 / 业务安全 / 可靠 / 并发 / 兼容 / 无障碍 / 视觉 / 国际化 /
  迁移 / 契约）全轴必答，include 必须挂信号、exclude 必须挂 G+S 双清单理由、
  full 档有预算上限（两域合并 ≤3，冲突时 R6 > R1 并触发预算裁决检查点）。
  设计全文见 `docs/decision-layer-design.md`（取代 v2 §6.3"性能/安全不自研"决策，
  升级为"方法论与决策自研，执行层对接专业工具"）。新增 / 改造：
  - 新增 `core/test-type-matrix.md`（十轴决策矩阵唯一真相源：信号 / 默认档 /
    档位语义 / 消费方式，按轴成节支持分组加载）
  - 新增 `core/scripts/scan_signals.py`（G 级代码信号扫描 + 决策预填表，零依赖、
    确定性输出；S 级语义信号由 agent 照单复核，exclude 永不预填防橡皮图章）
  - `validate_schema.py` 新增策略校验模式 V1–V5（全轴必答 / include 挂证据 /
    exclude 挂双清单 / full 挂风险且 ≤3 / 移交不断链），type 枚举扩
    reliability / concurrency / security / compatibility 四值
  - `test-strategy` SKILL.md 重写：分轴组推进 + 受限选择 + 预填修订（弱模型
    增益四机制）；功能域新增 state / data_consistency 两轴；handoff 协议做实
    （专项移交包 + 报告专项结果回收表）
  - 同步改写：coverage 类型性维度上收注记、risk-model 维度对齐、
    schema-extraction / case-format 枚举与标签、report-template 新增 §7 专项
    结果、qa 新增第四类人工检查点（预算裁决）、test-case-writing 增消费方式
    映射（用例型 / 脚本型 / 审查型；无障碍轴任意档位产 axe 扫描任务）；
    markmap 模板模块 20 改写为并发一致性（type: concurrency + [并发] 标签，
    性能轴按脚本型不再设手动用例模块），模块 11/18/19/21 补类型标签注
  - **R1 格式锤**（2026-08-23 首轮实测修复）：47% 弱模型样本把 type_scope 轴
    写成多行块式 YAML 致机械校验解析失败（决策内容无恙，纯格式损耗）——
    SKILL.md 增补"每轴单行 flow、禁止拆多行、写前照抄上一行形状"硬约束；
    复验轮格式失败归零、类型查全率 0.53 → 0.88（最弱模型，n=3，类别性判读）。
    注意分母口径：此为 On 臂首轮严格口径 → 复验轮自身对比；README 头条的 0 → 0.88
    是 Off 臂基线 vs On 复验轮对比，两处数字不等是分母不同而非矛盾。
    配套修复：scan_signals.py 中文关键词 `\b` 词边界失效（Python re Unicode
    下中文属 \w，永不命中）
- **Skill 自包含重构（消除跨 skill 引用）**：被多 skill 消费的方法 / 格式 / 规则
  全部下沉 `core/`——boundary / data-driven / permission / state-machine 四篇设计
  方法迁入 `core/methods/`，coverage（覆盖检查表）与 templates（升格更名
  case-format，用例格式硬约束）迁入 `core/`；test-case-review / api-testing 不再
  引用兄弟 skill 目录内的文件。新增 core 单一来源文档：schema-extraction.md
  （Schema 抽取规则，自 test-case-writing SKILL.md 抽出）、clarify-pattern.md
  （统一澄清 / 确认提问格式，替代三处各自为政的提问模板）、scripts/
  validate_schema.py（零依赖 Schema 校验器：YAML 转义 / TC 编号一致 / 占位符）
- **automated-e2e-testing 瘦身**：SKILL.md 473 → 188 行，Playwright 脚手架 / 配置 /
  场景代码模板 / Page Object 规范下沉新文件 references/playwright-conventions.md，
  SKILL.md 只保留工作流与决策点；Bug 条目字段表去重，统一引用
  core/report-template.md §3（唯一来源；严重度口径后经 S 系消歧升级，见下）
- **Bug 严重程度 S 系消歧（2026-08-23）**：Bug 严重程度从 P0/P1/P2 改为
  **S0/S1/S2**（bug-analysis 定级规则与 report-template §3 同步），与用例优先级
  P 系、风险等级 Critical 系词汇彻底分离；report-template 补 S 一词多义注
  （严重度 S 系 ≠ 类型矩阵「S 级语义信号」）
- **test-case-writing 弱模型行为修复群（2026-08-23 评测轮闭环）**：新增「逐模块
  推进与交付核对」硬约束（多模块输入只完成首模块 = 最严重交付缺陷）；阶段三增
  「维度核对」三条（主流程不可省 / 时间类规则双侧边界 / 状态机型负向底数——
  依据：评测轮两任务主流程用例丢 2/2、边界维度零增益的"维度坍缩"）；新增输出
  预算纪律（用例数封顶 min(可测点×1.5, 80)、附录仅代码模式产出、导读压缩——
  依据：实测 32K 截断事故与澄清仪式开销同源）；阶段四全检降级为轻量抽查
  （逐文档溯源 / coverage 19 维全检 / 多角色四视角全检废除，执行点迁至阶段三
  交付核对，coverage.md 自查表口径同步）；澄清"无需澄清"输出并入导读不单列
  章节；api-testing 参数矩阵明确为分析过程、不落盘中间文件
- **部署双形态适配（2026-08-23）**：evidence §6 声明「此时加载」在真实宿主
  （按需加载）与注入式形态（全部在场，靠阶段顺序防串扰）下的双重语义，qa 增
  注入式例外声明；boundary 降格为方法参考（强制边界纪律内联 test-case-writing
  阶段三维度核对——知识文件注入不改变弱模型行为，约束须在生成路径内联）；
  evidence / risk-model 的 status 示例 needs_verification → hypothesis 对齐枚举
- **description 全量瘦身**：10 个 skill 的 frontmatter description 统一为"正触发
  话术 + 一句产出 + 反触发指向"，机制细节（代码优先流程、Schema 抽取、增量更
  新等）移入正文新增的 When to Use 段（8 个 skill 补齐，与 qa / e2e 统一骨架）。
  常驻上下文合计 1929 → 1683 字符（-13%；前期"约 4300 字符"的读数为字节数口径
  的误判，实际中文 3 字节/字）；description 瘦身属触发行为变更，合入前需按迭
  代纪律跑触发评测确认不回退
- **架构红线新增三条**（validate_skills.py 同步实现并已负向自测）：① 禁止跨
  skill 引用（skill → 兄弟 skill 目录文件均违规，CI 拦截）；② description ≤300
  字符上限；③ 产品自包含——skills/ 内禁止引用 eval/ 等本地评测链路路径
  （公开收敛配套）。core 校验范围扩展到 core/**/*.md（含 methods/ 子目录）
- **eval 档案同步**：12 个 golden 任务的 skill_files_on 与 run_eval.py
  PIPELINE_STAGES 注入路径跟随迁移更新，内容外移的文件（schema-extraction /
  clarify-pattern / playwright-conventions / report-template）按"信息量等价"原则
  补入对应任务注入集；exploratory-testing 补无浏览器自动化时的降级路径说明
- **README 视觉重排**：顶部启用 banner 主视觉（hero.png，1600×800 压缩版，中心
  化排版），快速开始前置到首屏，实测效果表拆为"紧凑指标表 + 逐项口径清单"（长
  说明移出表格单元格），流水线 ASCII 图简化重排；中英双语同构
- **banner 整体重设计**：旧版（标题 + 标语 + 八流程块 + 三指标卡 + 元信息行）
  信息过载观感杂乱，重设计为极简 lockup——翡翠渐变 squircle 图标（放大镜 + 勾，
  QA 双关）+ "QA Skills" 词标（渐变强调）+ 标语一行 + 底部流程条一行；指标卡
  撤出图面（README 表格已有，不再重复）；social-preview / hero 双尺寸同源渲染
- **文档专业化（对齐主流开源项目规范）**：中英 README / CONTRIBUTING / DESIGN /
  examples / .github 社区文件 / eval 两级 README 全量风格统一（全角标点、中英文
  间距、口语化标题改客观表述、统一引号）；README 中英双语同构改写并新增"更多文档
  导航"；CONTRIBUTING 补开发环境与 PR 流程；修正 DESIGN.md 内指向仓库根文件的
  相对路径（./ → ../）与 harness README 两处 DESIGN 章节号过期引用。所有数字与
  口径声明逐字保留，未做任何语义变更（已做 token 级 diff 验证）
- **banner 口径勘误**：social-preview 图上"植入 bug 检出率 100% / 4-7 门通过"
  为旧同源裁判口径，改为与 README 一致的异构裁判口径（75% / 5-8，标注"异构
  裁判"），banner.html 同步并按既有流程 Playwright 重渲染
- **README 暗色模式与资产压缩**：hero 主视觉支持 prefers-color-scheme: dark
  自动切换（新增 hero-dark.png / banner-dark.html 同源暗色版）；hero.png 与
  social-preview.png 压缩重渲染（645KB→42KB、1.0MB→581KB，暂存产物实测值）
- **仓库布局重构**：11 个 skill 目录（10 skill + core）从仓库根迁入 `skills/`，
  产品本体与工程目录（eval/docs/examples/scripts/tests）一眼可分；安装后的
  宿主布局不变。install/uninstall、CI 校验、评测 harness、黄金集标注的路径
  已同步。**已用 `--link` 安装的用户 git pull 后需重跑 `install.sh`**（旧软链
  指向根目录已失效）；拷贝安装不受影响
- CI 拆为 validate + label 两个 job（PR 自动打领域标签）
- **README 实测数字换异构裁判口径**：可执行性改"规格符合度"并勘误旧称
  （Off 0.77→0.26 计 0 同口径）、检出 100%→75%（异构）、质量 Δ+6.1pp、API
  反向结果收窄 74% vs 52%；新增"口径边界"声明（预注入上界 + in-situ 探针 +
  成对胜率作废）
- **澄清反向结果修复闭环**：requirement-analysis 增补八类歧义强制扫描表
  （后经 2026-08-23 收敛迁至 core/clarify-pattern.md 单一权威源，两消费方改引用），
  test-case-writing 增 YAML 转义纪律；复验轮（clafix）澄清任务 On 检出 100%
  vs Off 85.2%，反向结果消除
- harness：X5 pass³ / X6 成对区分度守卫（平局率>80% 作废胜率）/ X7 judge 引文
  grounding 三个观察指标；G4 环境错误不入分母；skill 卡片 frontmatter 解析与
  YAML schema 校验；CI 依赖补 pyyaml；单测扩至 ~57 项（含冻结阈值防误改）
- EXPECTED.md：G4 勘误、异构复评结论（同源宽容偏差证实、G1a 转显著）、G7
  方向性通过、成对机制结论、v1.2 门提案、已知限制 #8/#9

### 新增

- **安装体验**：`install.sh` / `uninstall.sh`（自动检测宿主 skills 目录
  ~/.agents/skills 等，支持拷贝/软链两种方式与重装覆盖，安装时写入版本标识）；
  README 新增宿主兼容性矩阵与 markmap 渲染指引
- **DESIGN.md**：公开版设计文档（设计动机、三层架构、证据/风险模型、编排
  会话模型、可执行性失败模式、评测方法学、设计决策速查）
- **examples/**：同一 PRD 的 Skill On/Off 完整产出对照（取自验证轮真实产物）
- **README.en.md** 英文版，中英双语切换
- **assets/**：社交预览图及其 HTML 源（regenerate：改 banner.html 后 Playwright 截图）
- **Benchmark 手动工作流**（workflow_dispatch，本地维护、不入公开仓库）：CI 上
  跑黄金集质量门，产物上传 artifact；token 成本原因不随 push 触发
- **tests/**：harness 纯函数单测 20 项（统计/judge 校验/代码块解析/可执行性
  检查/确定性）——随 eval 本地维护，公开 CI 不跑
- Issue 模板升级为 YAML issue forms；PR 按路径自动打标（labeler）
- README "500 行红线"补 Red Hat ACE 实践出处链接
- **评测研究论文**（eval/reports/2026-08-21-benchmark-study，md/pdf/html 三格式，
  本地维护）：预注册基准评测与增益归因（§5 消融、§6 机制发现），配套单文件对照实验报告
- **评测新相位与新任务族**：routing（触发路由，35/35）与 pipeline（五阶段产物链
  交叉引用）两个观察型相位；golden 新增 req-clarify-ambiguity（澄清质量）与
  schema-extract-markmap（Schema 抽取，On-only）两任务；CONTAMINATION.md 污染
  检查机制设计；in-situ 探针 #1（n=1 无衰减）
- **AGENTS.md** 项目指令与 **docs/qa-skills-v2.md** v2 规划基线；DESIGN.md 归位
  docs/（与 v2 文档汇合）
- 运行归档补全：异构复评 / G7 泛化 / 强裁判成对 / 单文件消融 / s3 新任务族 /
  澄清复验共 8 个 run 目录登记入册（eval/results/，本地维护）

## [0.4.0] - 2026-08-20

全面审查修复（评测可信度 + skills 一致性 + harness 工程加固，41 文件）。

### 变更

- **评测数字对齐落盘数据**：成对评审实际 23 对/21 平（原引用中间态 20/18）；
  标注审计一致率均值 0.872（原宣称 0.90），12 个 annotation 逐任务写入真实值
- **预注册纪律补留痕**：EXPECTED.md 新增修订记录，如实披露 G2 阈值 0.75→0.85
  与验证轮同提交落地；立规门阈值修订必须独立提交先行
- **反向结果披露**：API 真实执行 On 52% < Off 87% 进入结论层与 v1.1 门提案
- harness：judge 增 GT-id 本地校验（幻觉 id 丢弃）与 GT 分母；G5 配对缺失判
  FAIL、G6 单主指标判定；mock 就绪探测 + 端口预检 + 执行异常包裹；可执行性
  指标无格式采样计 0 并新增无格式依赖的 content_violations
- skills：api-testing 修复 `requests.Session.base_url` 无效示例；markmap 模板
  附录 B 对齐 Critical/High/Medium/Low 新等级；Bug 条目字段/发现方式枚举/改动
  分类三处不一致归一
- golden：bug-import-offbyone 去除材料中泄露根因的注释；三处 annotation 计数
  纠正；P26 歧义与 strategy/rev 格式锚定可测点改写

## [0.3.0] - 2026-08-20

### 变更

- README 重写为开源项目首页风格（价值主张 + before/after 实例 + 实现逻辑）
- 文档全面对齐科学评估体系 v2 的命令、目录、工作流与验证状态

## [0.2.0] - 2026-08-20

Benchmark 重构为科学评估体系 v2。

### 新增

- 多样本生成（n=3）量化生成方差；任务层配对 bootstrap 95%CI
- 成对评审 + 位置互换；judge 3 采样多数表决
- E2E/API 真实执行环境（mock 被测应用 + chromium / mock 服务 + pytest）
- GT 标注独立审计与人工复核流程
- 预期效果门预注册冻结（EXPECTED.md v1.0）

### 变更

- 验证轮门判定 4/7 如实记录（含失败门诊断），不因数据改门
- 校准轮覆盖类数字被多样本复验证实为噪声膨胀（+28.8pp → +6.2pp）

## [0.1.0] - 2026-08-20

v2 改造：从两个 skill 升级为全生命周期 QA Agent Skills 框架。

### 新增

- 10 个 skill：qa 编排 + requirement-analysis / test-strategy / test-case-writing
  （references 6 篇方法）/ test-case-review / automated-e2e-testing / api-testing
  / exploratory-testing / bug-analysis / regression-testing
- core/ 共享知识库五件套：evidence / risk-model / executability /
  testing-principles / report-template
- 双轨产物：markmap（人执行）+ Test Case Schema（机器消费）
- 早期迭代：test-case-writing 代码驱动增强、两层审查架构、二阶交叉覆盖

[Unreleased]: https://github.com/fishzjp/qa-skills/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/fishzjp/qa-skills/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/fishzjp/qa-skills/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/fishzjp/qa-skills/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/fishzjp/qa-skills/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/fishzjp/qa-skills/releases/tag/v0.1.0
