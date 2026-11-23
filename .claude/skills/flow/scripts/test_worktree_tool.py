import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import feature  # noqa: E402

FLOW = Path(__file__).with_name("flow.py")


def sh(cwd, *args):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


class Fixture:
    """A repository with an `origin` remote carrying `develop`, an approved feature document whose row
    already has its Jira issue, and a bin dir on PATH where stand-in worktree tools log their calls."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.origin = base / "origin.git"
        self.repo = base / "app"
        self.bin = base / "bin"
        self.calls = base / "calls.log"
        self.bin.mkdir()
        sh(base, "git", "init", "--bare", "-q", str(self.origin))
        sh(base, "git", "init", "-q", "-b", "develop", str(self.repo))
        sh(self.repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init")
        sh(self.repo, "git", "remote", "add", "origin", str(self.origin))
        sh(self.repo, "git", "push", "-q", "origin", "develop")
        self.feature = self.repo / "docs" / "features" / "gift" / "feature.json"
        self.feature.parent.mkdir(parents=True)
        self.feature.write_text(json.dumps({
            "id": "gift", "root": "develop", "rows": [
                {"id": "r1", "title": "선물 목록", "story": "APP-9", "issue": "APP-10", "domain": "gift",
                 "stages": "tasks", "approved": True}]}, ensure_ascii=False))
        self.path = os.environ["PATH"]
        os.environ["PATH"] = f"{self.bin}{os.pathsep}{self.path}"
        for tool in ("orca", "paseo"):
            exe = self.bin / tool
            exe.write_text(f'#!/bin/sh\necho "{tool} $*" >> "{self.calls}"\n')
            exe.chmod(0o755)

    def start(self, *args):
        return subprocess.run([sys.executable, str(FLOW), "start", str(self.feature), *args],
                              capture_output=True, text=True)

    def close(self):
        os.environ["PATH"] = self.path
        self.tmp.cleanup()


class StartLeavesWorktreesToTheHostTest(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.close()

    def test_missing_worktree_stops_with_branch_and_base_and_runs_no_tool(self):
        p = self.fx.start()
        self.assertNotEqual(p.returncode, 0, p.stdout)
        self.assertIn("feat/APP-10", p.stdout)
        self.assertIn("origin/develop", p.stdout)
        self.assertFalse(self.fx.calls.exists(), "start must not run any worktree tool")
        self.assertIsNone(feature.worktree_of(str(self.fx.repo), "feat/APP-10"))

    def test_rerun_after_any_worktree_exists_continues_from_it(self):
        self.fx.start()
        wt = Path(self.fx.tmp.name).resolve() / "made-by-host"
        sh(self.fx.repo, "git", "worktree", "add", "-q", "-b", "feat/APP-10", str(wt), "origin/develop")
        p = self.fx.start()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue((wt / "docs" / "gift" / "tasks" / "APP-10.json").is_file(), p.stdout)
        self.assertFalse(self.fx.calls.exists())

    def test_dry_run_lists_the_worktree_to_make(self):
        p = self.fx.start("--dry-run")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("feat/APP-10", p.stdout)
        self.assertFalse(self.fx.calls.exists())

    def test_worktree_tool_flag_is_gone(self):
        p = self.fx.start("--worktree-tool", "orca")
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse(self.fx.calls.exists())


if __name__ == "__main__":
    unittest.main()
