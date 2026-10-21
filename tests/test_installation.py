"""Installer recovery and installed-payload checks; no model calls or network."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("verify_install", REPO / "scripts/verify_install.py")
verify_install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_install)


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="qa-installer-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        shutil.copytree(REPO / "skills", self.source / "skills", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("install.sh", "uninstall.sh"):
            shutil.copy2(REPO / name, self.source / name)
        self.target = self.root / "target with spaces"
        self.git("init", "-q")
        self.git("config", "user.name", "Installer Test")
        self.git("config", "user.email", "installer@example.invalid")
        self.git("add", ".")
        self.git("commit", "-qm", "v1 fixture")
        self.git("tag", "v0.9.0")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.source), *args], capture_output=True, text=True, check=True)

    def run_script(self, name="install.sh", extra=(), env=None):
        return subprocess.run(["bash", str(self.source / name), "--target", str(self.target), *extra],
                              capture_output=True, text=True, env=env, timeout=20)

    def install(self, extra=()):
        result = self.run_script(extra=extra)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def snapshot(self):
        result = {}
        for p in self.target.rglob("*"):
            if p.is_symlink():
                result[str(p.relative_to(self.target))] = ("link", os.readlink(p))
            elif p.is_file():
                result[str(p.relative_to(self.target))] = ("file", p.read_bytes())
            elif p.is_dir():
                result[str(p.relative_to(self.target))] = ("dir",)
        return result

    def update_source(self):
        p = self.source / "skills/api-testing/SKILL.md"
        p.write_text(p.read_text() + "\nUpdated fixture content.\n")
        self.git("add", ".")
        self.git("commit", "-qm", "v2 fixture")
        self.git("tag", "v0.9.1")

    def failure_env(self, command, condition):
        bindir = self.root / "bin"
        bindir.mkdir(exist_ok=True)
        actual = shutil.which(command)
        self.assertIsNotNone(actual)
        wrapper = bindir / command
        wrapper.write_text('#!/bin/bash\nset -eu\n' + condition + '\nexec "' + actual + '" "$@"\n')
        wrapper.chmod(0o755)
        return dict(os.environ, PATH=str(bindir) + os.pathsep + os.environ["PATH"])

    def test_later_conflict_leaves_entire_install_unchanged(self):
        self.install()
        self.update_source()
        conflict = self.target / "automated-e2e-testing"
        shutil.rmtree(conflict)
        conflict.mkdir()
        (conflict / "foreign.txt").write_text("keep")
        before = self.snapshot()
        self.assertNotEqual(self.run_script().returncode, 0)
        self.assertEqual(self.snapshot(), before)

    def test_commit_failure_rolls_back_content_and_version(self):
        self.install()
        self.update_source()
        before = self.snapshot()
        env = self.failure_env("mv", 'case "$1" in */new/core) exit 71 ;; esac')
        result = self.run_script(env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.snapshot(), before)

    def test_version_marker_failure_rolls_back_all_units(self):
        self.install()
        self.update_source()
        before = self.snapshot()
        env = self.failure_env("mv", 'case "$1" in */new/qa-skills.VERSION) exit 72 ;; esac')
        self.assertNotEqual(self.run_script(env=env).returncode, 0)
        self.assertEqual(self.snapshot(), before)

    def test_staging_failure_leaves_previous_install_unchanged(self):
        self.install()
        before = self.snapshot()
        env = self.failure_env("cp", 'exit 73')
        self.assertNotEqual(self.run_script(env=env).returncode, 0)
        self.assertEqual(self.snapshot(), before)

    def test_failed_first_install_removes_partial_units(self):
        env = self.failure_env("mv", 'case "$1" in */new/core) exit 74 ;; esac')
        self.assertNotEqual(self.run_script(env=env).returncode, 0)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_link_upgrade_failure_restores_original_links(self):
        self.install(extra=("--link",))
        before = self.snapshot()
        env = self.failure_env("mv", 'case "$1" in */new/core) exit 75 ;; esac')
        self.assertNotEqual(self.run_script(extra=("--link",), env=env).returncode, 0)
        self.assertEqual(self.snapshot(), before)

    def test_lock_blocks_install_and_uninstall(self):
        self.install()
        lock = self.target / ".qa-skills.lock"
        lock.mkdir()
        (lock / "pid").write_text("another-operation")
        before = self.snapshot()
        for script in ("install.sh", "uninstall.sh"):
            self.assertNotEqual(self.run_script(name=script).returncode, 0)
            self.assertEqual(self.snapshot(), before)

    def test_provenance_records_commit_method_and_dirty_state(self):
        (self.source / "skills/api-testing/SKILL.md").write_text("dirty fixture")
        self.install()
        marker = (self.target / "qa-skills.VERSION").read_text()
        self.assertIn("v0.9.0-dirty", marker)
        self.assertIn(self.git("rev-parse", "HEAD").stdout.strip(), marker)
        self.assertIn("method: copy", marker)

    def test_verifier_accepts_complete_install_and_detects_missing_core(self):
        self.install()
        # skills.sh does not create a VERSION file: absence is supported.
        (self.target / "qa-skills.VERSION").unlink()
        self.assertEqual(verify_install.verify(self.target)[0], [])
        shutil.rmtree(self.target / "core")
        errors, _ = verify_install.verify(self.target)
        self.assertTrue(any("core" in e for e in errors))

    def test_help_succeeds(self):
        for script in ("install.sh", "uninstall.sh"):
            result = subprocess.run(["bash", str(self.source / script), "--help"], capture_output=True)
            self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
