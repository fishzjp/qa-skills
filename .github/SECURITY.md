# 安全策略 / Security policy

## 支持范围 / Supported scope

请报告当前 `main` 或最新 GitHub Release 中的问题，并注明 tag 或完整 commit。旧版本不承诺单独回补；修复和迁移建议会在 Release 中说明。

Report issues in current `main` or the latest GitHub Release. Include the tag or full commit. Separate backports to older versions are not guaranteed; releases document fixes and migration guidance.

## 私密报告 / Report privately

**不要在公开 Issue、Discussion 或 PR 中披露漏洞细节和凭证。**

**Do not disclose vulnerability details or credentials in a public issue, discussion or PR.**

- [GitHub 私密漏洞报告 / Private vulnerability report](https://github.com/fishzjp/qa-skills/security/advisories/new)
- 邮箱 / Email: [fishzjp@foxmail.com](mailto:fishzjp@foxmail.com), subject: `[security] qa-skills`

包括受影响的 skill / 脚本、安装来源与版本、最小复现、预期与实际行为、潜在影响。先提供脱敏材料；不要发送生产凭证或完整私有仓库。

Include the affected skill/script, installation method and version, a minimal reproduction, expected/actual behavior and potential impact. Redact secrets; do not send production credentials or an entire private repository.

项目目前由个人维护，目标在 3 个工作日内确认；这不是响应 SLA。未收到回复时可通过另一个私密渠道重试。修复后协商披露时间与致谢方式，尊重匿名要求。

This is an individually maintained project. We aim to acknowledge reports within 3 business days; this is not an SLA. If you receive no response, retry through the other private channel. Disclosure timing and credit are coordinated with the reporter; anonymity requests are respected.

## 边界 / Boundaries

项目分发 Agent 指令和本地辅助脚本，不运营测试托管服务。安装器覆盖/删除错误、脚本不当读写、由项目指令造成的凭证泄露等问题在报告范围内。未经授权测试外部系统、宿主或模型提供商自身的漏洞，应向对应责任方报告；涉及本项目共同成因时仍欢迎说明。

The project ships agent instructions and local helpers, without a hosted testing service. Installer overwrite/deletion defects, unsafe script file access and credential disclosure caused by project instructions are in scope. Unauthorized testing of external systems and vulnerabilities solely in a host or model provider belong with that owner; report shared causes involving this project as well.

行为投诉使用 [行为准则的邮箱](./CODE_OF_CONDUCT.md#联系方式--contact)，不要填写为软件漏洞。

For conduct complaints, use the [Code of Conduct contact](./CODE_OF_CONDUCT.md#联系方式--contact), not a software vulnerability report.
