## 改动类型

<!-- 勾选一项 -->

- [ ] skill 方法论（SKILL.md / references / templates）
- [ ] core/ 共享知识库
- [ ] eval（golden 集 / harness / fixtures）
- [ ] 文档（README / CONTRIBUTING / CHANGELOG）
- [ ] CI / 工程配置

## 改动说明

做了什么、为什么。涉及方法论的说明与现有推导链（证据 → 风险 → 策略 → 用例）的关系。

## 自检清单

- [ ] 未引入真实环境地址、账号、密钥、内部系统名
- [ ] `python3 scripts/validate_skills.py` 通过（frontmatter / ≤500 行 / 引用完整）
- [ ] 新增引用的 references/core 文件存在且路径正确
- [ ] 改动影响用例产出的，已在黄金集上跑过 Benchmark：`python3 eval/harness/run_eval.py generate --samples 3 --tasks <相关任务>` + `score --samples 3`
- [ ] 改过标注或 judge 配置的，已删除对应 judge/pairwise 缓存再评分
- [ ] CHANGELOG.md 已更新（用户可感知的变更）

## 评测结果（涉及 eval/ 时必填）

<!-- 指标变化与门判定，回退需说明原因 -->
