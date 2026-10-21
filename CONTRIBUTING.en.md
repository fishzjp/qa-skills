# Contributing

[中文](./CONTRIBUTING.md)

Contributions are welcome. Read the [Code of Conduct](./.github/CODE_OF_CONDUCT.md), [support routes](./.github/SUPPORT.md) and [maintenance process](./.github/MAINTAINING.md). Report vulnerabilities [privately](./.github/SECURITY.md).

## Choose a contribution

Reproducible bug reports, clearer instructions, portable helper scripts and corrections to testing methods are useful. Keep a PR focused on one problem. For a new skill or substantial methodology change, discuss the use case first. Small documentation and script fixes do not require a proposal.

Include a redacted input, host/model versions, installation method and tag/commit, actual loaded files, expected behavior and observed output. Never submit credentials, internal URLs or private business data.

## Development environment and checks

Public scripts support Python 3.9–3.14. CI tests Linux with 3.9/3.12/3.14 and macOS with 3.12. Installers require Bash 3.2+ and standard Unix tools. Native Windows is not covered; use WSL, and validate host paths separately. Node.js 24 is used for legacy dsh syntax checks, not project npm distribution.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
bash scripts/check.sh
```

Set `QA_PYTHON` to select another interpreter. Browser checks are separate:

```bash
python3 -m pip install -r tests/browser/requirements.txt
python3 -m playwright install chromium
python3 tests/browser/smoke.py
```

Browser checks require Python 3.10+ (CI uses 3.12); public helpers retain their lower minimum. The website builder (`python3 scripts/build_site.py`) generates Chinese root and static `/en/` pages from one source; `_site/` is ignored and must be empty before a build. These checks invoke no models. Maintainers additionally run local harness unit tests through pytest when applicable; `eval/`, ground truth, raw data and planning documents remain private and are not required from contributors. Model evaluations are a separate maintainer gate, not a public CI job.

## Product architecture

- Keep each `SKILL.md` within 500 lines and description within 300 characters. Keep trigger boundaries and workflows in the entry point; methods and templates belong in references or shared core.
- Include a substantive **When NOT to Use** section. `qa` owns end-to-end intent; other skills have distinct stage intent. `bug-analysis` intentionally retains its Chinese description after routing regressions; do not translate it as a cosmetic fix.
- Install core alongside every skill. Core is a dependency, not a standalone workflow. Shared material should have at least two consumers; do not reference sibling skills' files directly.
- Save stage outputs as files. Distinguish risk levels Critical/High/Medium/Low, case priorities P0/P1/P2 and bug severity S0/S1/S2.
- Schema changes require matching validator and regression-test changes. Preserve evidence, uncertainty and human decision boundaries.
- Keep version fields synchronized and local references valid. Follow the validators rather than bypassing a failing gate.
- Product files are allowlisted. Private plans, evaluation assets and generated results stay outside the public repository. Add a legitimate product path to `scripts/validate_skills.py` and document it when necessary.

The detailed architecture checklist is in the [Chinese guide](./CONTRIBUTING.md#架构红线改-skill-前必读). English documentation does not imply English skill bodies or gains across all hosts/models.

## Pull requests

1. Branch from `main`; make one focused change.
2. Run public checks and update the changelog for user-visible changes.
3. Keep affected facts aligned across both READMEs, the website and `llms.txt`. Historical metrics must retain their experiment scope and limitations.
4. Describe the problem, resulting behavior and validation in the PR template.
5. All required CI must pass. The maintainer runs applicable private evaluations for skill changes and records the result and limits in the PR. Do not claim an unrun evaluation passed.
6. Normal changes use PRs; main does not allow force pushes. The project currently has one maintainer, so no second approval is required by policy.

Contributions are released under [MIT](./LICENSE); bundled third-party fonts retain their [own license](./assets/fonts/OFL.txt). Current distribution uses GitHub/Release, skills.sh and the website; no project npm publication is required.
