## 改动类型

<!-- 勾选一项 -->

- [ ] skill 方法论（SKILL.md / references / templates）
- [ ] core/ 共享知识库
- [ ] 文档（README / CONTRIBUTING / CHANGELOG / docs 设计文档）
- [ ] CI / 工程配置（安装脚本 / 校验器 / workflows）

## 改动说明

做了什么、为什么。涉及方法论的，请说明与现有推导链（证据 → 风险 → 策略 → 用例）的关系。

## 自检清单

- [ ] 未引入真实环境地址、账号、密钥、内部系统名
- [ ] `python3 scripts/validate_skills.py` 通过（frontmatter / ≤500 行 / 引用完整）
- [ ] 新增引用的 references / core 文件存在且路径正确
- [ ] 改动影响用例产出的，已在评测结果一节说明预期影响（正式 Benchmark 复验由维护者执行）
- [ ] CHANGELOG.md 已更新（用户可感知的变更）

## 评测结果（涉及 skill 方法论、影响用例产出时必填）

<!-- 说明预期影响（哪个环节、哪类产出）；指标复验由维护者在本地黄金集执行，结果会回贴在此 PR -->
