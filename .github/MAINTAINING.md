# 维护与决策 / Maintenance and decisions

qa-skills 当前由 [fishzjp](https://github.com/fishzjp) 维护，负责范围裁决、评审、模型评测与发版。贡献者可独立运行公开检查；私有评测链路不需要也不应上传到贡献者的 PR。

[fishzjp](https://github.com/fishzjp) currently maintains qa-skills and makes scope, review, evaluation and release decisions. Contributors can run public checks independently; the private evaluation system is neither required from contributors nor uploaded in PRs.

- 普通变更走 PR 和必需 CI；main 禁止强推。单维护者阶段不要求无法完成的第二人批准；重要变更仍应争取独立评审。
- 影响 skill 触发、方法论或产出的变更，维护者须按 AGENTS.md 复验并在 PR 记录范围、结论、限制。没有完成适用门时不声称效果通过。
- 明确的工程和文档修复可独立合入；它们不构成新的模型效果证据。
- 方案与进度在 Issue/PR 中说明，Release 记录用户可感知变化。私有规划与评测资料继续留在维护者本地。
- 紧急维护也优先使用小 PR；如确需改保护规则，记录原因、时间和恢复结果，不将绕过当常规路径。
- 新维护者资格通过持续贡献、评审与现维护者明确授权建立；不以添加 CODEOWNERS 文件冒充已有多人维护。

Normal changes use PRs and required CI; force pushes to main are disabled. A second approval is not mandatory while there is only one maintainer; seek independent review for significant changes. The maintainer records applicable skill-evaluation results and limits in the PR. Engineering/documentation checks are not evidence of model-quality gains. Release notes describe user-visible changes; planning and evaluation resources remain local. Emergency changes should still use small PRs; any protection change must record why, when and how it was restored. Additional maintainers require sustained contribution and explicit authorization.

当前安装渠道为 skills.sh 与 Git 安装器，不再发布项目 npm 插件包。发版流程见 [RELEASING](../RELEASING.md)，贡献入口见 [中文](../CONTRIBUTING.md) / [English](../CONTRIBUTING.en.md)。

Current installation channels are skills.sh and the Git installer. The project npm plugin is discontinued. See the release and contribution guides linked above.
