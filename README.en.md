**English** | [简体中文](./README.md)

# QA Skills

> Make AI work like a senior QA engineer: one sentence — *"test this feature for me"* — runs the full pipeline: **requirement understanding → risk analysis → test strategy → test-case writing → review → automated execution → bug analysis → regression → test report**.

![CI](https://github.com/fishzjp/qa-skills/actions/workflows/ci.yml/badge.svg) ![License](https://img.shields.io/badge/license-MIT-green) ![Skills](https://img.shields.io/badge/skills-10-blue) ![Benchmark](https://img.shields.io/badge/benchmark-golden%20set%20%2B%20harness-orange)

A **QA engineering skill framework** for AI coding agents (Claude Code and others). Not a handful of test prompts — a three-layer system of **methodology + 10 skills + a reproducible benchmark**, with every number actually measured. The docs are Chinese-first; this README summarizes the project in English.

---

## Why it exists

**Problem 1: AI-written test cases look professional but can't be executed.**

```markdown
- Verify coupon creation with valid input; the feature works      ← vague: what counts as "works"?
- Fill in {coupon name}, click {submit button}                    ← placeholders
- After expiry, status automatically changes to "ended"           ← how long until it's a failure?
- Open the campaign page and verify the claim logic               ← which page? which entry?
```

The framework's single output standard: **a person who has never read the requirements, with no walkthrough, can start working from the file alone.** In the benchmark this is a veto metric — a non-executable case scores zero no matter how broad its coverage.

**Problem 2: More instructions make the agent weaker, not stronger.**

External practice (Red Hat's ACE team) validates a ~500-line ceiling for skill instructions. The solution is a three-layer architecture: L1 trigger boundaries, L2 ≤500-line workflow in each SKILL.md, L3 methodology/templates loaded on demand via explicit workflow references.

## What it does

| You say | The framework does | Output |
|---------|--------------------|--------|
| "Test this requirement" | `qa` orchestrates the 9-stage pipeline with human checkpoints (clarifications, execution strategy, bug triage) | Full QA assets + test report |
| "Write test cases from this PRD" | Code-first: requests the repo, reads the implementation, finds latent bugs, then writes | markmap test cases (human) + Test Case Schema (machine) |
| "How should we test this?" | Risk Map (Impact × Likelihood, ratings require evidence) → scope/depth/rationale | `测试策略.md` (test strategy) |
| "Review these existing cases" | Independent review: testable-point denominator + coverage + executability | Revised case file + review record |
| "Convert cases to automation" | Page Object conventions, listeners-before-actions, self-built data & cleanup | Runnable Playwright / pytest code |
| "Root-cause this bug" | Reproduce → read code to the line → 3-dimension impact analysis → regression advice | Bug entry (root cause / evidence / regression) |

Also usable standalone: `exploratory-testing` (charter-driven), `api-testing`, `bug-analysis`, `regression-testing` (diff → regression scope).

## Quick start

```bash
git clone https://github.com/fishzjp/qa-skills.git
cd qa-skills
./install.sh        # interactive: auto-detects agent skills directories (~/.agents/skills, ~/.claude/skills, ...)
# then tell your agent:
# "Test this requirement: {description + repo URL}"
```

Skills are plain Markdown (frontmatter + relative-path references), so any agent host supporting the Agent Skills convention works. See the [compatibility table](./README.md#宿主兼容性) in the Chinese README for details. Uninstall: `./uninstall.sh`.

## How it's built

- **Files are the pipeline state** — every stage persists its output to disk; stages consume files, not session memory. Interrupted runs resume from files in a fresh session.
- **Evidence & risk models** — every finding carries an evidence level (E0–E4 user statement → docs → code → runtime → cross-validated); risk ratings without evidence are invalid. Chain: evidence → risk → strategy → cases, traceable end to end.
- **Talking checkpoints** — end-to-end ≠ zero human input. Clarifications, execution strategy, and bug triage are *your* decisions; the agent proposes, never decides. Once recorded, later stages can't overturn them.
- Full design rationale (why 10 narrow skills instead of 1 big one, why markmap is the single human-maintained source, why evaluation precedes feature growth): [DESIGN.md](./DESIGN.md) (Chinese).

## Measured results (Skill On / Off)

Golden set of 12 tasks, same model, same harness; the only difference is whether this framework is injected. Honest numbers — including the ones that hurt:

| Metric | Without | With | Notes |
|--------|:---:|:---:|-------|
| E2E real-execution pass rate | 0% | **78%** | Real browser + real app, no LLM judge |
| Planted-bug detection | — | **100%** | Code-review tasks |
| Quality (LLM judge) | 0.87 | **0.92** | Paired bootstrap 95%CI significant |
| Case executability | 0.77 | **0.98** | Objective regex scan; metric includes skill-template adherence (construct favors On — see eval docs) |
| API real-execution pass rate | **87%** | 52% | Disclosed adverse result: skill-enforced strict assertions fail more visibly |
| Token cost | 1× | 3.3× | Better but more expensive |

Coverage gains: +3.8pp on case-writing tasks (CI [0.5, 7.1], significant); +5.2pp all tasks (CI includes 0). Gate verdicts: **4/7 passed, recorded as-is under pre-registration discipline** — including the finding that an early +29pp single-sample estimate was later shown to be noise. See [eval/EXPECTED.md](./eval/EXPECTED.md) and [eval/results/LATEST.md](./eval/results/LATEST.md).

## Community

- 💬 Discussions for Q&A and experience sharing; Issues for confirmed bugs and concrete feature requests
- 🛡️ Security: private reporting per [SECURITY.md](./.github/SECURITY.md)
- 📜 [Code of Conduct](./.github/CODE_OF_CONDUCT.md) · 📋 [CHANGELOG](./CHANGELOG.md) · 🤝 [CONTRIBUTING](./CONTRIBUTING.md)

## License

[MIT](./LICENSE)
