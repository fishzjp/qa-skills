#!/usr/bin/env python3
"""Verify the external skills.sh installer against this checkout in a temp project.

Requires Node 24 and network to fetch the pinned third-party installer.
No global install, user-home change or model calls. Opt in; not part of offline checks.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

from verify_install import verify

REPO = Path(__file__).resolve().parents[1]
SKILLS_CLI_VERSION = "1.7.4"


def main():
    with tempfile.TemporaryDirectory(prefix="qa-skills-cli-") as tmp:
        project = Path(tmp)
        subprocess.run(["git", "init", "-q", str(project)], check=True)
        command = ["npx", "--yes", f"skills@{SKILLS_CLI_VERSION}", "add", str(REPO),
                   "--skill", "*", "--agent", "codex", "--yes"]
        subprocess.run(command, cwd=project, check=True, timeout=180)
        errors, count = verify(project / ".agents/skills")
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"PASS: skills CLI {SKILLS_CLI_VERSION}, Codex project scope, {count} units and core references.")
        print("This verifies filesystem installation, not host triggering or model quality.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
