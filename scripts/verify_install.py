#!/usr/bin/env python3
"""Check installed units and core references without invoking an agent or model.

Usage: python3 scripts/verify_install.py /path/to/host/skills
This verifies files, not triggering or output quality. It also works for skills.sh
installs, which do not create the repository installer's version marker.
"""
import argparse
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CORE_REF = re.compile(r"\.\./core/[\w./-]+\.(?:md|py|ya?ml)\b")


def verify(target, source=REPO / "skills"):
    errors = []
    units = sorted(p.name for p in source.iterdir() if (p / "SKILL.md").is_file())
    if not units or "core" not in units:
        return ["Source checkout is incomplete: expected skill units and core."], 0
    for unit in units:
        entry = target / unit / "SKILL.md"
        if not entry.is_file():
            errors.append(f"Missing {unit}/SKILL.md")
            continue
        text = entry.read_text(encoding="utf-8")
        match = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|$)", text, re.S)
        if not match or not re.search(rf"^slug: {re.escape(unit)}$", match[1], re.M):
            errors.append(f"Unexpected identity in {unit}/SKILL.md")
        for ref in sorted(set(CORE_REF.findall(text))):
            if not (entry.parent / ref).is_file():
                errors.append(f"Broken reference in {unit}: {ref}")
    # Check the entire expected product payload, including helpers and references.
    for path in sorted(source.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            rel = path.relative_to(source)
            if not (target / rel).is_file():
                message = f"Missing product file: {rel}"
                if message not in errors:
                    errors.append(message)
    return errors, len(units)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    try:
        errors, count = verify(args.target.expanduser())
    except (OSError, UnicodeError) as exc:
        parser.exit(1, f"Cannot verify installation: {exc}\n")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        print("Repair: reinstall all units with core; see README installation instructions.")
        return 1
    print(f"PASS: {count} units, product files and core references present.")
    print("This checks installation only. Verify actual skill loading in your host separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
