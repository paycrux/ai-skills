import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

FLOW = Path(__file__).with_name("flow.py")


def run(cwd, *args):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def flow(cwd, *args):
    return run(cwd, sys.executable, str(FLOW), *args)


class Fixture:
    """A throwaway git repo with one domain, one task on branch feat/x, and src/ files."""

    def __init__(self, root, kind="기능 수정"):
        self.root = Path(root)
        self.docs = self.root / "docs"
        self.task = self.docs / "d" / "tasks" / "t.json"
        run(self.root, "git", "init", "-q", "-b", "main")
        run(self.root, "git", "config", "user.email", "t@t")
        run(self.root, "git", "config", "user.name", "t")
        (self.root / "src").mkdir()
        for name in ("a.ts", "b.ts", "c.ts", "a.test.ts"):
            (self.root / "src" / name).write_text("export {}\n")
        self.docs.mkdir()
        flow(self.root, "domain", str(self.docs), "d", "--title", "Domain")
        self.commit("init")
        run(self.root, "git", "switch", "-q", "-c", "feat/x")
        flow(self.root, "task", str(self.docs / "d"), "t", "--title", "Task", "--type", kind, "--stages", "tasks")

    def commit(self, msg):
        run(self.root, "git", "add", "-A")
        run(self.root, "git", "commit", "-q", "-m", msg)
        return run(self.root, "git", "rev-parse", "--short", "HEAD").stdout.strip()

    def plan(self, status, items):
        t = json.loads(self.task.read_text())
        t["stages"]["tasks"] = {"status": status, "summary": "s", "conclusion": ["c"],
                                "blocks": [{"type": "checklist", "id": "P1", "title": "P1", "items": items}]}
        self.task.write_text(json.dumps(t, ensure_ascii=False))
        flow(self.root, "build", str(self.docs))

    def check(self):
        return flow(self.root, "check", str(self.docs))


def item(i, *files, extra=()):
    return {"id": i, "title": i, "done": False,
            "rows": [["파일", " ".join(f"<code>{f}</code>" for f in files)], *extra]}


class PlanDriftTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_in_progress_prints_drift_without_failing(self):
        self.fx.plan("now", [item("P1-1", "src/a.ts:12", "src/b.ts")])
        (self.fx.root / "src" / "a.ts").write_text("export const a = 1\n")
        (self.fx.root / "src" / "c.ts").write_text("export const c = 1\n")
        r = self.fx.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("계획에 없는 변경 파일 1개 — src/c.ts", r.stdout)
        self.assertIn("계획에 있는데 안 바뀐 파일 1개 — src/b.ts", r.stdout)

    def test_done_with_drift_fails(self):
        self.fx.plan("done", [item("P1-1", "src/a.ts")])
        (self.fx.root / "src" / "c.ts").write_text("export const c = 1\n")
        r = self.fx.check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("src/c.ts", r.stdout)

    def test_matching_plan_is_silent(self):
        self.fx.plan("done", [item("P1-1", "src/a.ts")])
        (self.fx.root / "src" / "a.ts").write_text("export const a = 1\n")
        self.fx.commit("fix")
        r = self.fx.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("계획", r.stdout)

    def test_paths_outside_repo_are_ignored(self):
        self.fx.plan("now", [item("P1-1", "~/elsewhere/x.ts", "src/a.ts")])
        (self.fx.root / "src" / "a.ts").write_text("export const a = 1\n")
        r = self.fx.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("x.ts", r.stdout)


class ReproTestTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(self.tmp.name, "버그 수정")
        (self.fx.root / "src" / "a.test.ts").write_text("expect(a).toBe(1)\n")
        self.sha = self.fx.commit("repro")

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, status="now", sha=None):
        self.fx.plan(status, [item("P1-1", "src/a.ts", extra=(
            ["테스트", "<code>src/a.test.ts</code>"], ["실패 커밋", f"<code>{sha or self.sha}</code>"]))])

    def test_untouched_test_passes(self):
        self.plan()
        (self.fx.root / "src" / "a.ts").write_text("export const a = 1\n")
        self.fx.commit("fix")
        r = self.fx.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_test_edited_after_failing_commit_fails(self):
        self.plan()
        (self.fx.root / "src" / "a.test.ts").write_text("expect(a).toBe(2)\n")
        r = self.fx.check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("재현 테스트가 실패 커밋", r.stdout)
        self.fx.commit("edit test")
        self.assertEqual(self.fx.check().returncode, 1)

    def test_unknown_commit_fails(self):
        self.plan(sha="deadbee")
        r = self.fx.check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("deadbee", r.stdout)

    def test_finished_bug_fix_without_repro_fails(self):
        self.fx.plan("done", [item("P1-1", "src/a.ts")])
        (self.fx.root / "src" / "a.ts").write_text("export const a = 1\n")
        self.fx.commit("fix")
        r = self.fx.check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("재현 테스트(테스트 · 실패 커밋 행)도 verify 단계도 없어요", r.stdout)


if __name__ == "__main__":
    unittest.main()
