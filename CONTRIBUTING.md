# 贡献指南

欢迎提交 Issue 和 Pull Request。

## 如何贡献

- **报告问题**：在 Issue 中描述复现场景与预期行为。
- **改进方法论**：两个 skill 的工作流、检查表、模板都欢迎补充。改动请保持「一条用例 / 一个 test 只测一个点」「先熟悉业务再写测试」「不确定就提问」等核心原则。
- **补充代码模板**：新增的 Page Object / Helper 模板请保持通用、不绑定具体业务，且不包含任何真实账号、URL 或内部信息。

## 提交前自检

- [ ] 未引入任何真实环境地址、账号、密钥、内部系统名
- [ ] 改动后的 skill 仍符合 [Agent Skill 规范](https://docs.claude.com/en/docs/claude-code/skills)：每个 skill 有 `SKILL.md`，frontmatter 含 `name` 与 `description`
- [ ] 代码示例可独立运行，或已用占位符（如 `<你的测试环境地址>`）标注需替换处

## 许可证

提交的内容将按 [MIT](./LICENSE) 许可证发布。
