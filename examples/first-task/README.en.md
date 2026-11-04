# First task: turn a brief into reviewable test cases

[中文](./README.md)

Use a fictional room-booking brief to try clarification, strategy, case writing and independent review. No production account or test service is required. This is a document exercise; it **does not prove tests were executed or establish overall model gains**.

## 1. Install and confirm loading

Follow the [README](../../README.en.md#quick-start), installing every unit including core. From this checkout, check the actual host skills directory:

```bash
python3 scripts/verify_install.py ~/.agents/skills
```

Use the directory your host actually reads. Then inspect its loading records for the relevant skill and core files. File presence alone is insufficient.

## 2. Submit the brief

Start your agent in this repository and send the following request. You may copy this folder into a separate practice project; adjust paths accordingly.

```text
Use requirement-analysis to analyze examples/first-task/requirement.md.
This is a fictional product with no code, UI or test service. Design documents only;
do not send network requests. Write outputs to .qa-practice/.
First list the questions requiring my decision and wait for my answer.
Do not invent entry points, accounts, locators or executed results.
```

You may explicitly approve these exercise assumptions: server time in UTC; in-progress bookings cannot be cancelled; UI entry points, accounts and messages remain unresolved. Ask the agent to record your decisions and outstanding questions in the requirement model. Assumptions take effect only after your confirmation.

## 3. Continue by stage

```text
I approve the exercise assumptions above. Record them in the requirement model.
Use test-strategy to design the strategy, test-case-writing to write cases,
and test-case-review for an independent review. Save outputs to .qa-practice/.
Mark missing execution conditions as unresolved or blocked.
Document review is not test execution; do not report passing runs.
```

Expect a requirement model, strategy, markmap cases, Schema and review record, named according to the skills. If the host cannot dispatch stages, request each stage separately and provide the previous output paths. Skill instruction bodies are currently Chinese; this English walkthrough does not imply complete product localization.

## 4. Review the output

- Explicit verdicts cover the 30/120-minute boundaries, invalid ordering, adjacent and overlapping bookings.
- Permissions distinguish ordinary/admin users and own/other users' bookings.
- Concurrent conflicts have an “at most one succeeds” verdict, without an invented execution rate.
- Time-zone and cancellation rules refer to your decisions; unknown accounts and entry points stay unresolved.
- Cases include preconditions, steps and expected results, with missing execution conditions identified.
- Review records specific gaps or justified changes rather than only “passed”.

This learning checklist is separate from private evaluation ground truth and scoring. If the workflow fails, retain the input, actual loaded paths and failing output, then follow [support guidance](../../.github/SUPPORT.md).

Generated `.qa-practice/` files are ignored in this repository. Do not commit outputs, accounts or business data.
