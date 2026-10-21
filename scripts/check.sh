#!/usr/bin/env bash
# Public contribution checks. No model evaluation or external service calls.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
QA_PYTHON="${QA_PYTHON:-python3}"
"$QA_PYTHON" scripts/validate_skills.py
"$QA_PYTHON" scripts/validate_repo.py
"$QA_PYTHON" -m unittest discover -s tests -p 'test_*.py'
bash -n install.sh
bash -n uninstall.sh
bash tests/install_smoke.sh
node --check .dsh/plugins/qa-skills.js
