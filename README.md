# QA Skills

> A full-lifecycle QA skill framework for AI coding agents — methodology, 10 skills, and a reproducible benchmark.（中文项目，文档以中文为准）
>
> 让 AI 像资深测试工程师一样工作:一句"帮我测试这个需求",跑完 **需求理解 → 风险分析 → 测试策略 → 用例编写 → 审查 → 自动化执行 → Bug 分析 → 回归 → 测试报告** 的完整流水线。

![CI](https://github.com/fishzjp/qa-skills/actions/workflows/ci.yml/badge.svg) ![License](https://img.shields.io/badge/license-MIT-green) ![Skills](https://img.shields.io/badge/skills-10-blue) ![Benchmark](https://img.shields.io/badge/benchmark-golden%20set%20%2B%20harness-orange)

面向 [Claude Code 等 Agent](https://docs.claude.com/en/docs/claude-code/skills) 的一套**测试工程 Skill 框架**:不是几个测试 Prompt,而是「方法论 + Skills + Benchmark」三层,且每个数字都实测过。

---

## 为什么需要它

### 坑一:AI 写的用例"看着专业,拿着没法执行"

直接让 AI 写测试用例,产出的常常是这样:

```markdown
- 验证优惠券创建功能,输入合法数据,功能正常        ← 判定模糊:怎么算"正常"?
- 填写 {优惠券名称},点击 {提交按钮}               ← 占位符:执行的人填什么?
- 到达有效期后,状态自动变更为已结束               ← 多久没变算失败?
- 打开活动页,验证领取逻辑                        ← 入口在哪?新人根本找不到页面
```

覆盖矩阵漂亮、术语专业,测试工程师拿到手第一步就卡住。**本框架的核心产出标准只有一条:没读过需求、没人讲解的人,拿着文件能直接开工。** 同一个需求,框架产出长这样:

```markdown
> 前置:运营账号已登录,进入「营销中台 → 券工场 → 活动列表」

- **TC-02-05 到期自动结束** [P1]
  - 操作步骤: 1. 选一张结束时间为 2 分钟后的已发布券「满100减20-测试」 2. 等待到期
  - 预期结果: 到期后 1 小时内状态自动变为「已结束」,超过 1 小时未变判失败
```

具体数据、明确入口、可判定的预期、异步行为带时限——这背后是 `core/executability.md` 的 8 条硬标准,评测里它是一票否决项:**不可执行的用例,覆盖再全也计零分**。

### 坑二:指令堆得越多,AI 反而越弱

把方法论、模板、规则全塞进一个 SKILL.md,Agent 有效遵循的规则反而变少(外部实践验证的 500 行红线)。本框架的解法是**三层架构**:

```text
L1  SKILL.md 头部      触发边界:什么时候用、什么时候不用、交给谁
L2  SKILL.md 正文      工作流:每次触发都要走的主干(≤500 行红线)
L3  references/ + core/  方法/规则/模板:按需加载,工作流步骤里显式引用
```

于是"写用例"这件事被拆成:SKILL.md 只管流程编排,状态机方法、边界值公式、权限矩阵、格式硬约束全部下沉按需加载——Agent 每一步只面对当前需要的指令。

---

## 它能做什么

| 你说 | 框架做 | 产出 |
|------|--------|------|
| "帮我测试这个需求" | `qa` 编排 9 阶段流水线,澄清/执行策略/Bug 定性等检查点暂停等你裁决 | 全套测试资产 + 测试报告 |
| "根据这份 PRD 写用例" | 代码优先:主动索取仓库、读实现、审出潜在 bug 再写用例 | `测试用例_markmap.md`(人执行)+ `测试用例.schema.yaml`(机器消费) |
| "这个功能应该怎么测" | Risk Map(Impact×Likelihood,评级强制挂证据)→ 范围/深度/理由 | `测试策略.md` |
| "审一下这份存量用例" | 独立审查:可测点基准分母 + 覆盖 + 可执行性双线 | 直接修订用例文件 + 审查记录 |
| "把用例转成自动化" | Page Object 规范、监听先于操作、自建数据自清理 | 可跑的 Playwright / pytest 代码 |
| "这个 Bug 帮我定位下" | 复现 → 读代码到行 → 影响三面分析 → 回归建议 | Bug 条目(根因/证据/回归) |

另有 `exploratory-testing`(charter 驱动探索)、`api-testing`(接口级)、`bug-analysis`、`regression-testing`(diff → 回归范围)各自独立可用。

## 快速开始

```bash
# 1. 复制到你的 Agent skills 目录(core/ 必须一起,各 skill 相对引用它)
cp -r qa core requirement-analysis test-strategy test-case-writing test-case-review \
      automated-e2e-testing api-testing exploratory-testing bug-analysis regression-testing \
      <项目>/.claude/skills/

# 2. 对 Agent 说一句话
"帮我测试这个需求:{需求描述 + 仓库地址}"
```

单阶段任务(写用例/审查/转自动化/回归范围)直接描述即可触发对应 skill,不需要走全流水线。

---

## 工作原理

### 1. 文件即流水线状态

每个阶段的产出落盘为文件,下一阶段只消费上一阶段的**文件**而非会话记忆——长流水线不依赖上下文,中断后新会话读文件即可续跑:

```text
PRD / 代码
   │  requirement-analysis
   ▼
需求模型.md ──────────── ⏸ 澄清检查点(模糊项等你裁决,不硬猜)
   │  test-strategy(风险 → 策略)
   ▼
测试策略.md(Risk Map)
   │  test-case-writing
   ▼
测试用例_markmap.md + 测试用例.schema.yaml ── 双轨:markmap 给人,
   │  test-case-review                      schema 单向抽取给机器(审查/回归/执行消费)
   ▼
   │  ⏸ 执行策略裁决(手动 / Playwright / API)
   ▼
执行产物 + Bug 证据(E3)
   │  bug-analysis → regression-testing
   ▼
回归清单.md → 测试报告.md
```

### 2. 让 AI 不瞎说:证据与风险模型

- **证据体系(E0–E4)**:每条结论标注证据等级(用户陈述 → 文档 → 代码 → 运行结果 → 交叉验证)与状态(事实/推断/风险/假设)。静态问题以代码为准(测准声明),文档偏离记附录——AI 不再凭 PRD 想象系统行为
- **风险模型(Impact × Likelihood)**:评级必须挂证据,没有证据的评级视为无效;风险等级(Critical/High/Medium/Low)与用例优先级(P0/P1/P2)是两套体系,推导链可追溯:证据 → 风险 → 策略 → 用例

### 3. 会说话的检查点

端到端不等于零人工:澄清、执行策略、Bug 定性三类决策由你裁决,Agent 只提案不代答;裁决落盘后,后续阶段不得推翻。

---

## 实测效果(Skill On / Off)

黄金集 12 个任务(PRD/代码注入 bug/无 UI 后端/状态机/增量更新等),同模型同 harness,唯一差异是否注入本框架([方法学与完整报告](./eval/harness/README.md)):

| 指标 | 无 Skill | 有 Skill | 说明 |
|------|:---:|:---:|------|
| 用例可执行性 | 0.77 | **0.98** | 正则逐条扫描(占位符/模糊判定/虚构入口/无时限),无 judge 参与;该口径含 skill 模板遵从度(编号/导读),构造上偏向 On,详见 eval 文档 |
| E2E 代码真实执行通过率 | 0% | **78%** | 生成的 Playwright 代码跑真实浏览器 + 被测应用,无 judge 参与 |
| 植入 bug 检出率 | — | **100%** | 代码审查类任务 |
| 产出质量(LLM judge) | 0.87 | **0.92** | 配对 bootstrap 95%CI 显著 |
| API 代码真实执行通过率 | **87%** | 52% | 如实披露的反向结果:skill 的三件套严断言更易暴露失败,弱断言易通过(1 个截断采样;诊断见 eval/EXPECTED.md) |
| token 成本 | 1× | 3.3× | 如实披露:更好但更贵 |

覆盖类增益:tcw 口径 +3.8pp(CI[0.5,7.1] 显著);全任务口径 +5.2pp(CI 含 0,方向为正但不显著)。早期单采样表观的 +29pp 经多样本复验为噪声。诚实声明与门判定详见 [eval/EXPECTED.md](./eval/EXPECTED.md) 与 [eval/results/LATEST.md](./eval/results/LATEST.md)。

---

## 目录

```text
qa/                    编排入口(薄,无领域知识)
core/                  共享知识库:evidence / risk-model / executability /
                       testing-principles / report-template(无 SKILL.md,不被触发)
requirement-analysis/  test-strategy/  test-case-writing/(references 6 篇方法)
test-case-review/      automated-e2e-testing/  api-testing/
exploratory-testing/   bug-analysis/  regression-testing/
eval/                  黄金集 + 评测 harness(多样本/统计推断/成对评审/真实执行)
```

## 贡献

Skill 改动以黄金集为质量门(改完跑 `eval/harness/run_eval.py`,指标回退拦截);架构红线(SKILL.md ≤500 行、Every skill 必须有 When NOT to Use、core/ 不含 SKILL.md)见 [CONTRIBUTING.md](./CONTRIBUTING.md)——本地一条命令自检:`python3 scripts/validate_skills.py`(与 CI 同一校验)。

## 社区

- 🐛 缺陷 / 💡 功能建议:先看 [Discussions](https://github.com/fishzjp/qa-skills/discussions)(使用问答与经验分享),确定是缺陷或明确诉求再开 [Issue](https://github.com/fishzjp/qa-skills/issues)
- 🛡️ 安全漏洞:请勿公开讨论,按 [安全策略](./.github/SECURITY.md) 私密报告
- 📜 行为准则:[CODE_OF_CONDUCT.md](./.github/CODE_OF_CONDUCT.md)
- 📋 版本历史:[CHANGELOG.md](./CHANGELOG.md)

## 许可证

[MIT](./LICENSE)
