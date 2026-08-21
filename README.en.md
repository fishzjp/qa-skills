**English** | [简体中文](./README.md)

# QA Skills

> A full-lifecycle QA engineering skill framework for AI coding agents: methodology, 10 skills, and a reproducible benchmark.
>
> Make AI work like a senior QA engineer — one sentence, *"test this feature for me"*, runs the complete pipeline: **requirement understanding → risk analysis → test strategy → test-case writing → review → automated execution → bug analysis → regression → test report**.

![CI](https://github.com/fishzjp/qa-skills/actions/workflows/ci.yml/badge.svg) ![License](https://img.shields.io/badge/license-MIT-green) ![Skills](https://img.shields.io/badge/skills-10-blue) ![Benchmark](https://img.shields.io/badge/benchmark-golden%20set%20%2B%20harness-orange)

Not a handful of test prompts — a **QA engineering skill framework** for AI coding agents (Claude Code and others), built as three layers: **methodology + 10 skills + a reproducible benchmark**. Every number published here was actually measured. The project is Chinese-first; this README summarizes it in English.

---

## Why this project exists

### Problem 1: AI-written test cases look professional but cannot be executed

```markdown
- Verify coupon creation with valid input; the feature works      ← vague: what counts as "works"?
- Fill in {coupon name}, click {submit button}                    ← placeholders
- After expiry, status automatically changes to "ended"           ← how long until it's a failure?
- Open the campaign page and verify the claim logic               ← which page? which entry?
```

A polished coverage matrix, professional terminology — and the test engineer stalls on the very first step. The framework's single output standard: **a person who has never read the requirements, with no walkthrough, can start working from the file alone.** In the benchmark this is a veto metric — a non-executable case scores zero no matter how broad its coverage.

### Problem 2: More instructions make the agent weaker, not stronger

Stuffing methodology, templates, and rules into a single SKILL.md reduces the rules an agent actually follows (per [Red Hat's ACE practice notes](https://next.redhat.com/2026/07/28/building-skills-for-ai-agents-pitfalls-and-best-practices/), performance degrades beyond ~500 lines of instructions). The solution is a three-layer architecture:

```text
L1  SKILL.md header    Trigger boundaries: when to use, when not to, who hands off to whom
L2  SKILL.md body      Workflow: the backbone every invocation walks (≤500-line ceiling)
L3  references/ + core/  Methods/rules/templates: loaded on demand, explicitly referenced by workflow steps
```

Each SKILL.md keeps only the workflow; state-machine methods, boundary-value formulas, permission matrices, and format constraints are pushed down and loaded on demand — the agent faces only the instructions it needs at each step.

## What it does

| You say | The framework does | Output |
|---------|--------------------|--------|
| "Test this requirement" | `qa` orchestrates the 9-stage pipeline with human checkpoints (clarifications, execution strategy, bug triage) | Full QA assets + test report |
| "Write test cases from this PRD" | Code-first: requests the repo, reads the implementation, finds latent bugs, then writes | markmap test cases (human) + Test Case Schema (machine) |
| "How should we test this?" | Risk Map (Impact × Likelihood, ratings require evidence) → scope/depth/rationale | `测试策略.md` (test strategy) |
| "Review these existing cases" | Independent review: testable-point denominator + coverage + executability | Revised case file + review record |
| "Convert cases to automation" | Page Object conventions, listeners-before-actions, self-built data & cleanup | Runnable Playwright / pytest code |
| "Root-cause this bug" | Reproduce → read code to the line → 3-dimension impact analysis → regression advice | Bug entry (root cause / evidence / regression) |

Also usable standalone: `exploratory-testing` (charter-driven), `api-testing` (API-level), `bug-analysis`, `regression-testing` (diff → regression scope).

## Quick start

```bash
git clone https://github.com/fishzjp/qa-skills.git
cd qa-skills
./install.sh        # interactive: auto-detects agent skills directories (~/.agents/skills, ~/.claude/skills, ...)
# then tell your agent:
# "Test this requirement: {description + repo URL}"
```

Uninstall: `./uninstall.sh`. Manual install works too: `cp -r skills/* <your skills directory>/` (**core/ must be copied along** — every skill references it by relative path). Single-stage tasks (write cases / review / convert to automation / regression scope) trigger the corresponding skill directly, no full pipeline needed.

Skills are plain Markdown (frontmatter + relative-path references) with no host-specific dependencies, so any agent host supporting the Agent Skills convention works. See the [compatibility table](./README.md#宿主兼容性) in the Chinese README for details.

## How it works

- **Files are the pipeline state** — every stage persists its output to disk; stages consume files, not session memory. Interrupted runs resume from files in a fresh session.
- **Evidence & risk models** — every finding carries an evidence level (E0–E4: user statement → docs → code → runtime → cross-validated); risk ratings without evidence are invalid. The chain evidence → risk → strategy → cases is traceable end to end.
- **Human-in-the-loop checkpoints** — end-to-end ≠ zero human input. Clarifications, execution strategy, and bug triage are *your* decisions; the agent proposes, never decides. Once recorded, later stages cannot overturn them.
- Full design rationale (why 10 narrow skills instead of 1 big one, why markmap is the single human-maintained source, why evaluation precedes feature growth): [DESIGN.md](./docs/DESIGN.md) (Chinese).

## Measured results (Skill On / Off)

Golden set of 12 tasks, same model, same harness; the only difference is whether this framework is injected. Numbers from the heterogeneous-judge re-evaluation (judge from a different model family than the generator); full study in the [📄 benchmark paper (PDF)](./eval/reports/2026-08-21-benchmark-study.pdf). All numbers are reported as measured — including the adverse ones:

| Metric | Without | With | Notes |
|--------|:---:|:---:|-------|
| Case-conformance score (formerly "executability") | 0.26 | **0.98** | Format × content-rubric composite, no judge; the gap is primarily format adoption — both arms near ceiling on content red lines (decomposition in paper §5.1); zero-caliber (earlier 0.77 was pre-fix caliber — see eval errata); replicated across two generator models (0.20→0.99) |
| E2E real execution (single task × 3 samples) | 0/3 runnable | 1 full + 2×(2/3) | Real browser + real app, no judge; on the On side the same failing test reproduces stably across two samples; Off mixes no-code and failing-code outcomes (full granularity in paper §5.1) |
| Planted-bug detection | — | **75%** | Heterogeneous judge (100% under same-family judge) |
| Quality (LLM judge) | 0.70 | **0.76** | Heterogeneous judge; Δ +6.1pp (95%CI includes zero; significant under same-family judging) |
| API real-execution pass rate | **74%** | 52% | Disclosed adverse result: skill-enforced strict assertions fail more visibly (full 3-sample caliber; earlier 87% was a 2-sample mean) |
| Token cost | 1× | 3.3× | Better but more expensive; a single-file ablation shows the gains cannot be obtained by taking just the core standards document (paper §5.3) |

Pre-registered gates: 4/7 under the same-family judge, 5/8 under the heterogeneous judge (different compositions incl. a sign flip — full table in paper Table 6). Coverage gains (heterogeneous judge): **+8.7pp** on case-writing tasks (CI [0.5, 15.4]), **+13.2pp** all tasks (CI [2.8, 26.3]), **+9.7pp** defect detection (CI [3.3, 16.4]) — all significant; the same-family figure was +3.8pp (quantified judge leniency toward the baseline and errata in [eval/EXPECTED.md](./eval/EXPECTED.md)). An early +29pp single-sample estimate was later shown to be noise.

> **Validity boundary**: the On mode of the eval pre-injects all skill instruction files (real hosts load them on demand), so On-side numbers are an upper bound — an in-situ probe (n=1) observed no decay; pairwise judging exceeded tie limits under all three judges tested (win rate voided — a mechanism issue, see paper §6).

## Documentation

- [DESIGN.md](./docs/DESIGN.md) (Chinese) — design rationale and key decisions
- [Benchmark paper (PDF)](./eval/reports/2026-08-21-benchmark-study.pdf) — pre-registered evaluation and gain attribution
- [eval/harness/README.md](./eval/harness/README.md) — evaluation methodology and harness usage
- [examples/](./examples/) — Skill On/Off output comparison on the same PRD
- [CHANGELOG.md](./CHANGELOG.md) — release history

## Community

- 💬 [Discussions](https://github.com/fishzjp/qa-skills/discussions) for Q&A and experience sharing; [Issues](https://github.com/fishzjp/qa-skills/issues) for confirmed bugs and concrete feature requests
- 🛡️ Security: private reporting per [SECURITY.md](./.github/SECURITY.md)
- 📜 [Code of Conduct](./.github/CODE_OF_CONDUCT.md) · 📋 [CHANGELOG](./CHANGELOG.md) · 🤝 [Contributing](./CONTRIBUTING.md)

## License

[MIT](./LICENSE)
