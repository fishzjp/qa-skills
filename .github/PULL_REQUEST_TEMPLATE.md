## Change type / 改动类型

- [ ] Skill methodology / skill 方法论（SKILL.md / references / templates）
- [ ] Shared core / core 共享知识库
- [ ] Documentation / 文档
- [ ] Engineering / CI、安装器、校验器或脚本

## Problem and resulting behavior / 问题与修改后的行为

<!-- Explain the concrete trigger, previous behavior and resulting behavior. / 说明具体触发条件、之前与之后的行为。 -->

## Validation / 验证

<!-- State what actually ran, its result and remaining limits. Never mark unrun model evaluations as passed. / 写实际执行的检查、结果与限制。 -->

- [ ] No credentials, private addresses or business data / 无凭证、私有地址或业务数据
- [ ] `bash scripts/check.sh` passes / 公开检查通过
- [ ] Website changes pass `python3 tests/browser/smoke.py` / 网站改动通过实际浏览器检查（如适用）
- [ ] References resolve relative to the consuming SKILL.md; shared dependencies remain intact / 引用按消费方 SKILL.md 解析且共享依赖完整
- [ ] User-visible changes are recorded in CHANGELOG / 用户可感知改动已记日志
- [ ] Affected product facts match across README zh/en, website and llms / 受影响的产品事实已同步

## Skill evaluation / Skill 评测（方法论改动必填）

<!-- Describe expected impact, affected stage/output and whether maintainer evaluation is pending. Contributors do not need private eval assets. / 说明预期影响、环节与产出；维护者复验是否待办。 -->

[English contribution guide](https://github.com/fishzjp/qa-skills/blob/main/CONTRIBUTING.en.md) · [中文贡献指南](https://github.com/fishzjp/qa-skills/blob/main/CONTRIBUTING.md)
