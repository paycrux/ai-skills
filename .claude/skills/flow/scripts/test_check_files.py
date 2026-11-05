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


def finish(fx, ticked=True):
    """Add a 05 완료 stage, all ticked and done unless ticked=False."""
    flow(fx.root, "add", str(fx.task), "done")
    t = json.loads(fx.task.read_text())
    st = t["stages"]["done"]
    for b in st["blocks"]:
        for it in b.get("items", []):
            it["done"] = ticked
    st.update({"status": "done", "conclusion": ["리뷰 · 수정 뒤 테스트 · PR 없음"]})
    fx.task.write_text(json.dumps(t, ensure_ascii=False))
    flow(fx.root, "build", str(fx.docs))


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

    def test_pruned_bug_fix_keeps_its_repro_rows(self):
        self.plan("done")
        (self.fx.root / "src" / "a.ts").write_text("export const a = 1\n")
        self.fx.commit("fix")
        finish(self.fx)
        self.assertEqual(flow(self.fx.root, "prune", str(self.fx.task)).returncode, 0)
        r = self.fx.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

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



class PruneTimingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(self.tmp.name)
        self.fx.plan("done", [item("P1-1", "src/a.ts")])
        (self.fx.root / "src" / "a.ts").write_text("export const a = 1\n")
        self.fx.commit("fix")

    def tearDown(self):
        self.tmp.cleanup()

    def current(self):
        return flow(self.fx.root, "current", str(self.fx.root)).stdout

    def test_implementation_only_is_not_finished(self):
        r = self.fx.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        p = flow(self.fx.root, "prune", str(self.fx.task))
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("05 완료 단계가 없어요", p.stderr)
        self.assertIn("구현만 끝남", self.current())
        self.assertIn("진행 중", (self.fx.docs / "d" / "index.html").read_text())

    def test_unticked_review_or_retest_blocks_prune(self):
        finish(self.fx, ticked=False)
        p = flow(self.fx.root, "prune", str(self.fx.task))
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("05 완료 체크리스트", p.stderr)
        self.assertNotIn("정리하지 않았어요", self.fx.check().stdout)

    def test_finished_task_without_pr_must_be_pruned(self):
        finish(self.fx)
        r = self.fx.check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("끝난 작업인데 정리하지 않았어요", r.stdout)
        self.assertIn("끝났는데 정리 전", self.current())
        p = flow(self.fx.root, "prune", str(self.fx.task))
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        r = self.fx.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("끝났는데", self.current())


class RecommendedReasonTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(self.tmp.name)
        flow(self.fx.root, "add", str(self.fx.task), "grill")

    def tearDown(self):
        self.tmp.cleanup()

    def question(self, choice, by, user=False):
        t = json.loads(self.fx.task.read_text())
        answer = {"choice": choice, "why": ""}
        if user:
            answer["by"] = "user"
        q = {"id": "Q1", "title": "Q", "intent": "i", "recommended": "a",
             "options": [{"value": "a", "label": "A"}, {"value": "b", "label": "B"}],
             "recommendation": "A를 추천해요. 화면을 떠나지 않아요.", "answer": answer}
        if not user:
            q.update({"decision": "A로 해요.", "appliedTo": "P1-1",
                      "reason": {"text": "화면을 떠나지 않게 하려고", "by": by}})
        t["stages"]["grill"] = {"rounds": [{"id": "R1", "questions": [q]}]}
        t["intent"] = [{"text": "x", "state": "guess", "basis": "PRD"}]
        self.fx.task.write_text(json.dumps(t, ensure_ascii=False))
        flow(self.fx.root, "build", str(self.fx.docs))

    def test_recommended_reason_on_recommended_choice_passes(self):
        self.question("a", "recommended")
        r = self.fx.check()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        page = (self.fx.docs / "d" / "t" / "02-grill.html").read_text()
        self.assertIn("추천대로 고름", page)

    def test_recommended_reason_on_other_choice_fails(self):
        self.question("b", "recommended")
        r = self.fx.check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("추천과 다른 답인데", r.stdout)

    def test_changes_says_which_reason_to_write(self):
        self.question("a", None, user=True)
        self.assertIn("by: recommended", flow(self.fx.root, "changes", str(self.fx.docs)).stdout)
        self.question("b", None, user=True)
        self.assertIn("by: inferred", flow(self.fx.root, "changes", str(self.fx.docs)).stdout)


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(self.tmp.name)
        self.fx.plan("now", [item("P1-1", "src/a.ts")])

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, data, css=None):
        (self.fx.docs / "flow.config.json").write_text(json.dumps(data, ensure_ascii=False))
        if css is not None:
            (self.fx.docs / "flow.css").write_text(css)
        return flow(self.fx.root, "build", str(self.fx.docs))

    def test_style_is_inlined_and_hidden_page_is_not_written(self):
        flow(self.fx.root, "add", str(self.fx.task), "verify")
        self.config({"style": "flow.css", "hide": ["page:verify", "block:checklist"]}, ":root{--ink:#123456}")
        page = (self.fx.docs / "d" / "t" / "03-tasks.html").read_text()
        self.assertIn("--ink:#123456", page)
        self.assertNotIn('id="P1-1"', page)
        self.assertFalse((self.fx.docs / "d" / "t" / "04-verify.html").exists())
        self.assertNotIn("04-verify.html", (self.fx.docs / "d" / "t" / "index.html").read_text())
        r = self.fx.check()
        self.assertNotIn("flow.config.json", r.stdout)
        self.assertNotIn("HTML:", r.stdout)

    def test_bad_entries_fail_check(self):
        self.config({"style": "missing.css", "hide": ["field:why", "page:nope"], "theme": 1})
        r = self.fx.check()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        for word in ("missing.css", "field:why", "page:nope", "theme"):
            self.assertIn(word, r.stdout)


if __name__ == "__main__":
    unittest.main()
