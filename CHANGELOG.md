# 更新日志

本项目所有显著变更都记录在此，格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

- 开源工程化：CI 工作流（架构红线校验 + 语法检查）、Issue/PR 模板、行为准则、
  安全策略、dependabot、`scripts/validate_skills.py` 本地校验脚本

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

[Unreleased]: https://github.com/fishzjp/qa-skills/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/fishzjp/qa-skills/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/fishzjp/qa-skills/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/fishzjp/qa-skills/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/fishzjp/qa-skills/releases/tag/v0.1.0
