import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

FLOW = Path(__file__).with_name("flow.py")


# Personal settings live under $FLOW_HOME; point it at an empty folder so this machine's own
# settings never leak into a test. A test that needs them sets HOME_DIR's contents itself.
HOME_DIR = tempfile.TemporaryDirectory()
os.environ["FLOW_HOME"] = HOME_DIR.name


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


class TaskBaseTest(unittest.TestCase):
    def test_base_limits_drift_to_the_tasks_own_commits(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            (fx.root / "src" / "a.ts").write_text("export const earlier = 1\n")
            base = fx.commit("an earlier task on this branch")
            fx.plan("done", [dict(item("P1-1", "src/b.ts"), done=True)])
            (fx.root / "src" / "b.ts").write_text("export const mine = 1\n")
            self.assertIn("src/a.ts", fx.check().stdout)
            t = json.loads(fx.task.read_text())
            t["base"] = base
            fx.task.write_text(json.dumps(t, ensure_ascii=False))
            flow(fx.root, "build", str(fx.docs))
            self.assertNotIn("src/a.ts", fx.check().stdout)


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


class FeatureTitleTest(unittest.TestCase):
    def test_sub_issue_titles_follow_the_teams_learned_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            self.assertEqual(flow(fx.root, "feature", str(fx.docs), "gift", "--title", "선물", "--root", "main").returncode, 0)
            fd = fx.docs / "features" / "gift"
            (fd / "issues" / "shop.md").write_text("# shop")

            def save(jira, title):
                f = json.loads((fd / "feature.json").read_text())
                f["jira"].update(jira)
                f["rows"] = [{"id": "shop", "story": "COMP-1", "title": title, "domain": "d",
                              "issueBody": "issues/shop.md", "approved": True}]
                (fd / "feature.json").write_text(json.dumps(f, ensure_ascii=False))
                return fx.check().stdout

            self.assertIn("jira.titlePrefix가 없어요", save({}, "기프트샵"))
            self.assertIn("팀 접두어 [FE]로 시작하지 않아요", save({"titlePrefix": "[FE]"}, "[프론트] 기프트샵"))
            out = save({"titlePrefix": "[FE]"}, "[FE] 기프트샵")
            self.assertNotIn("titlePrefix", out)
            self.assertNotIn("접두어", out)
            self.assertNotIn("접두어", save({"titlePrefix": ""}, "기프트샵"))


def set_personal(config=None, files=None):
    """Write $FLOW_HOME/config.json (plus files next to it); none clears it."""
    home = Path(os.environ["FLOW_HOME"])
    shutil.rmtree(home, ignore_errors=True)
    home.mkdir(parents=True)
    for name, text in (files or {}).items():
        (home / name).write_text(text)
    if config is not None:
        (home / "config.json").write_text(json.dumps(config, ensure_ascii=False))


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(self.tmp.name)
        set_personal()

    def tearDown(self):
        set_personal()
        self.tmp.cleanup()

    def team(self, wf):
        (self.fx.docs / "flow.config.json").write_text(json.dumps({"workflow": wf}, ensure_ascii=False))

    def test_release_stage_has_its_page_and_checklist(self):
        r = flow(self.fx.root, "add", str(self.fx.task), "release")
        self.assertEqual(r.returncode, 0, r.stderr)
        t = json.loads(self.fx.task.read_text())
        self.assertEqual([i["id"] for i in t["stages"]["release"]["blocks"][0]["items"]], ["L1", "L2", "L3"])
        flow(self.fx.root, "build", str(self.fx.docs))
        self.assertTrue((self.fx.docs / "d" / "t" / "06-release.html").exists())

    def test_every_core_stage_is_required_and_labels_only_rename(self):
        set_personal({"off": ["grill"], "labels": {"tasks": "작업 쪼개기"}})
        r = flow(self.fx.root, "workflow", str(self.fx.docs))
        self.assertEqual(r.returncode, 1)
        self.assertIn("off는 기본 단계는 모두 필수라서", r.stdout)
        flow(self.fx.root, "add", str(self.fx.task), "grill")
        flow(self.fx.root, "build", str(self.fx.docs))
        page = self.fx.docs / "d" / "t"
        self.assertTrue((page / "02-grill.html").exists())
        self.assertIn("작업 쪼개기", (page / "03-tasks.html").read_text())
        self.team({"required": ["grill"]})
        set_personal({"labels": {"tasks": "작업 쪼개기"}})
        r = flow(self.fx.root, "workflow", str(self.fx.docs))
        self.assertEqual(r.returncode, 1)
        self.assertIn("workflow.required는", r.stdout)
        self.team({"labels": {"verify": "QA"}})
        r = flow(self.fx.root, "workflow", str(self.fx.docs))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("코어 · 필수", r.stdout)

    def test_bad_team_and_personal_entries_fail(self):
        self.team({"required": ["nope"], "order": 1})
        set_personal({"off": ["zzz"], "labels": {"yyy": "x"}, "style": "missing.css", "theme": 1,
                      "custom": [{"key": "Bad Key"}]})
        r = flow(self.fx.root, "workflow", str(self.fx.docs))
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.fx.check().returncode, 1)
        for word in ("workflow.required", "order", "off는", "yyy", "missing.css", "theme", "Bad Key", "id가 있어야"):
            self.assertIn(word, r.stdout)

    def test_done_still_needs_its_record_to_finish(self):
        self.fx.plan("done", [dict(item("P1-1", "src/a.ts"), done=True)])
        r = flow(self.fx.root, "prune", str(self.fx.task))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("05 완료 단계가 없어요", r.stderr)
        finish(self.fx)
        self.assertEqual(flow(self.fx.root, "prune", str(self.fx.task)).returncode, 0)

    def test_personal_style_reaches_only_this_persons_pages(self):
        home = Path(os.environ["FLOW_HOME"])
        set_personal({"style": "my.css"})
        (home / "my.css").write_text(":root { --st-now: #2f6f5e }")
        flow(self.fx.root, "build", str(self.fx.docs))
        self.assertIn("--st-now: #2f6f5e", (self.fx.docs / "d" / "t" / "index.html").read_text())
        set_personal()
        flow(self.fx.root, "build", str(self.fx.docs))
        self.assertNotIn("--st-now: #2f6f5e", (self.fx.docs / "d" / "t" / "index.html").read_text())

    def test_own_stage_runs_its_check_and_teammates_see_a_plain_page(self):
        set_personal({"id": "mine", "custom": [{"key": "perf", "title": "성능 측정", "after": "verify",
                                               "instructions": "perf.md", "check": "test -f perf-ok"}]},
                     files={"perf.md": "# perf"})
        self.assertEqual(flow(self.fx.root, "add", str(self.fx.task), "mine:perf").returncode, 0)
        t = json.loads(self.fx.task.read_text())
        self.assertEqual(t["stages"]["mine:perf"]["title"], "성능 측정")
        del t["stages"]["mine:perf"]["title"]
        self.fx.task.write_text(json.dumps(t, ensure_ascii=False))
        self.assertIn("mine:perf: title이 없어요", self.fx.check().stdout)
        t["stages"]["mine:perf"].update({"title": "성능 측정", "status": "done", "conclusion": ["측정함"]})
        self.fx.task.write_text(json.dumps(t, ensure_ascii=False))
        flow(self.fx.root, "build", str(self.fx.docs))
        self.assertTrue((self.fx.docs / "d" / "t" / "x-mine-perf.html").exists())
        self.assertIn("성능 측정", (self.fx.docs / "d" / "t" / "index.html").read_text())
        self.assertIn("perf.md", flow(self.fx.root, "brief", str(self.fx.task), "--stage", "mine:perf").stdout)
        r = self.fx.check()
        self.assertEqual(r.returncode, 1)
        self.assertIn("test -f perf-ok", r.stdout)
        (self.fx.root / "perf-ok").write_text("")
        self.assertNotIn("mine:perf", self.fx.check().stdout)
        set_personal()
        flow(self.fx.root, "build", str(self.fx.docs))
        self.assertNotIn("없는 단계", self.fx.check().stdout)
        teammate = (self.fx.docs / "d" / "t" / "x-mine-perf.html").read_text()
        self.assertIn("성능 측정", teammate)
        self.assertIn("측정함", teammate)
        self.assertIn("성능 측정", (self.fx.docs / "d" / "t" / "index.html").read_text())

    def test_attach_collects_more_data_on_a_core_stage(self):
        set_personal({"id": "mine", "attach": [{"stage": "verify", "title": "성능 측정", "instructions": "perf.md",
                                               "fields": ["score", "lcp"]}]}, files={"perf.md": "# perf"})
        flow(self.fx.root, "add", str(self.fx.task), "verify")
        self.assertIn("perf.md", flow(self.fx.root, "brief", str(self.fx.task), "--stage", "verify").stdout)
        self.assertIn("성능 측정", flow(self.fx.root, "workflow", str(self.fx.docs)).stdout)

        def verify(ext):
            t = json.loads(self.fx.task.read_text())
            t["stages"]["verify"].update({"status": "done", "conclusion": ["확인함"]})
            if ext is not None:
                t["stages"]["verify"]["ext"] = {"mine": ext}
            self.fx.task.write_text(json.dumps(t, ensure_ascii=False))
            flow(self.fx.root, "build", str(self.fx.docs))

        verify(None)
        self.assertIn("score, lcp", self.fx.check().stdout)
        verify({"score": 92, "inferred": ["score"], "unknown": {"lcp": "실기기 측정 불가"}})
        self.assertIn("ext.mine.title이 없어요", self.fx.check().stdout)
        verify({"title": "성능 측정", "score": 92, "inferred": ["score"], "unknown": {"lcp": "실기기 측정 불가"}})
        self.assertNotIn("이 없어요", self.fx.check().stdout)
        page = (self.fx.docs / "d" / "t" / "04-verify.html").read_text()
        self.assertIn("붙임 · 성능 측정", page)
        self.assertIn("실기기 측정 불가", page)
        self.assertIn("사람 확인 안 된 추정 1건 · 모르는 값 1건", flow(self.fx.root, "brief", str(self.fx.task)).stdout)
        set_personal()
        flow(self.fx.root, "build", str(self.fx.docs))
        teammate = (self.fx.docs / "d" / "t" / "04-verify.html").read_text()
        self.assertIn("붙임 · 성능 측정", teammate)
        self.assertIn("실기기 측정 불가", teammate)
        self.assertNotIn("이 없어요", self.fx.check().stdout)
        self.assertEqual(json.loads(self.fx.task.read_text())["stages"]["verify"]["ext"]["mine"]["score"], 92)

    def test_bad_attach_entries_fail(self):
        set_personal({"id": "mine", "attach": [{"stage": "nope"}, {"stage": "verify", "fields": ["unknown"], "extra": 1}]})
        r = flow(self.fx.root, "workflow", str(self.fx.docs))
        self.assertEqual(r.returncode, 1)
        for word in ("'nope'", "inferred · title · unknown", "extra", "instructions"):
            self.assertIn(word, r.stdout)

    def test_own_commands_run_on_request_or_after_build(self):
        set_personal({"commands": [
            {"name": "notes", "title": "옵시디언에 복사", "run": "echo synced > \"$FLOW_DOCS/../synced.txt\"", "on": "build"},
            {"name": "broken", "run": "exit 3", "on": "build"},
            {"name": "export-mine", "title": "내 형식으로 내보내기", "run": "echo \"task=$FLOW_TASK\""}]})
        r = flow(self.fx.root, "build", str(self.fx.docs))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.fx.root / "synced.txt").exists())
        self.assertIn("내 명령 broken (broken): 실패 (3)", r.stdout)
        self.assertNotIn("export-mine", r.stdout)
        r = flow(self.fx.root, "run", str(self.fx.docs), "export-mine", "--task", str(self.fx.task))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"task={self.fx.task.resolve()}", r.stdout)
        r = flow(self.fx.root, "run", str(self.fx.docs), "nope")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("notes, broken, export-mine", r.stderr)
        self.assertIn("옵시디언에 복사 · build 뒤마다", flow(self.fx.root, "workflow", str(self.fx.docs)).stdout)
        set_personal({"commands": [{"name": "x"}, {"name": "y", "run": "true", "on": "always"}]})
        r = flow(self.fx.root, "workflow", str(self.fx.docs))
        self.assertEqual(r.returncode, 1)
        self.assertIn("commands x: run", r.stdout)
        self.assertIn("commands y: on은", r.stdout)

    def test_share_copies_are_written_only_on_export(self):
        flow(self.fx.root, "add", str(self.fx.task), "grill")
        flow(self.fx.root, "build", str(self.fx.docs))
        share_dir = self.fx.docs / "d" / "t" / "share"
        self.assertFalse(share_dir.exists())
        self.assertIn("내보내기", (self.fx.docs / "d" / "t" / "index.html").read_text())
        r = flow(self.fx.root, "export", str(self.fx.task), "--to", "plan", "--format", "html")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((share_dir / "plan.html").exists())
        self.assertEqual(self.fx.check().returncode, 0, self.fx.check().stdout)

    def test_ext_is_kept_by_prune_and_its_ids_are_ignored(self):
        flow(self.fx.root, "add", str(self.fx.task), "grill")
        t = json.loads(self.fx.task.read_text())
        t["ext"] = {"mine": {"minutes": 30}}
        t["stages"]["tasks"] = {"status": "done", "summary": "s", "conclusion": ["c"], "blocks": [
            {"type": "checklist", "id": "P1", "title": "P1", "items": [
                {"id": "P1-1", "title": "a", "done": True, "rows": [["메모", "x"]], "ext": {"mine": {"id": "P1-1"}}}]}]}
        t["intent"] = [{"text": "i", "state": "confirmed", "basis": "b"}]
        t["stages"]["grill"] = {"rounds": [{"id": "R1", "title": "r", "questions": [
            {"id": "Q1", "title": "q", "intent": "i", "decision": "d", "reason": {"text": "r", "by": "user"},
             "appliedTo": "[[P1-1]]", "body": "x", "ext": {"mine": {"seen": True}}}]}]}
        self.fx.task.write_text(json.dumps(t, ensure_ascii=False))
        finish(self.fx)
        self.assertNotIn("겹쳐요", self.fx.check().stdout)
        self.assertEqual(flow(self.fx.root, "prune", str(self.fx.task)).returncode, 0)
        t = json.loads(self.fx.task.read_text())
        self.assertEqual(t["ext"], {"mine": {"minutes": 30}})
        self.assertEqual(t["stages"]["tasks"]["blocks"][0]["items"][0]["ext"], {"mine": {"id": "P1-1"}})
        self.assertEqual(t["stages"]["grill"]["rounds"][0]["questions"][0]["ext"], {"mine": {"seen": True}})
        self.assertNotIn("body", t["stages"]["grill"]["rounds"][0]["questions"][0])

    def test_unconfirmed_record_is_counted_shown_and_does_not_block(self):
        flow(self.fx.root, "add", str(self.fx.task), "grill")
        t = json.loads(self.fx.task.read_text())
        t["intent"] = [{"text": "i", "state": "guess", "basis": "대화"}]
        t["skipped"] = [{"stage": "tasks", "stop": "계획 승인", "why": "꺼짐"}]
        t["stages"]["grill"] = {"rounds": [{"id": "R1", "title": "r", "questions": [
            {"id": "Q1", "title": "q", "intent": "i", "recommended": "yes", "answer": {"choice": "yes"},
             "decision": "d", "reason": {"text": "대화에서 유추", "by": "inferred"}, "appliedTo": "[[P1-1]]"}]}]}
        t["stages"]["tasks"] = {"status": "done", "summary": "s", "conclusion": ["c"], "blocks": [
            {"type": "checklist", "id": "P1", "title": "P1", "items": [
                {"id": "P1-1", "title": "a", "done": True, "by": "inferred", "rows": [["파일", "<code>src/a.ts</code>"]]}]}]}
        self.fx.task.write_text(json.dumps(t, ensure_ascii=False))
        finish(self.fx)
        t = json.loads(self.fx.task.read_text())
        d5 = t["stages"]["done"]["blocks"][0]["items"][4]
        d5.update({"done": False, "unknown": "PR을 물을 수 없음 — 05 꺼짐"})
        self.fx.task.write_text(json.dumps(t, ensure_ascii=False))
        flow(self.fx.root, "build", str(self.fx.docs))
        brief = flow(self.fx.root, "brief", str(self.fx.task)).stdout
        self.assertIn("사람 확인 안 된 추정 2건 · 건너뛴 멈춤 1건 · 모르는 값 1건", brief)
        cover = (self.fx.docs / "d" / "t" / "index.html").read_text()
        self.assertIn("사람 확인 없이 남은 것", cover)
        self.assertIn("계획 승인", cover)
        r = self.fx.check()
        self.assertIn("모르는 값 1건", r.stdout)
        self.assertNotIn("skipped", r.stdout)
        self.assertEqual(flow(self.fx.root, "prune", str(self.fx.task)).returncode, 0)
        t = json.loads(self.fx.task.read_text())
        self.assertEqual(t["skipped"][0]["stop"], "계획 승인")

    def test_bad_record_entries_fail(self):
        t = json.loads(self.fx.task.read_text())
        t["skipped"] = [{"stage": "nope"}]
        t["stages"]["tasks"] = {"status": "now", "summary": "s", "conclusion": [], "blocks": [
            {"type": "checklist", "id": "P1", "title": "P1", "items": [{"id": "P1-1", "title": "a", "by": "ai", "unknown": " "}]}]}
        self.fx.task.write_text(json.dumps(t, ensure_ascii=False))
        flow(self.fx.root, "build", str(self.fx.docs))
        r = self.fx.check()
        self.assertEqual(r.returncode, 1)
        for word in ("skipped[0]", "by는", "unknown에는"):
            self.assertIn(word, r.stdout)


class LegacyMarkdownTest(unittest.TestCase):
    """A .md under docs/ outside a domain gets a rendered view page beside it; the source is untouched."""

    def test_md_gets_a_view_page_and_index_links_to_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Fixture(tmp)
            plans = fx.docs / "old" / "plans"
            plans.mkdir(parents=True)
            src = "# Tasks\n\n- [x] done\n\nsee [spec](../spec.md#a) and <!-- note --> </script>\n"
            (plans / "tasks.md").write_text(src)
            (fx.docs / "old" / "spec.md").write_text("# Spec\n")
            flow(fx.root, "build", str(fx.docs))

            view = plans / "tasks.md.html"
            self.assertTrue(view.exists())
            self.assertEqual((plans / "tasks.md").read_text(), src)
            index = (fx.docs / "index.html").read_text()
            self.assertIn('href="old/plans/tasks.md.html"', index)
            self.assertNotIn('href="old/plans/tasks.md"', index)
            html = view.read_text()
            self.assertIn('"../spec.md"', html)
            self.assertNotIn("<!-- note", html.split('id="md-data">')[1].split("</script>")[0])
            self.assertIn("*.md.html", (fx.docs / ".gitignore").read_text())
            self.assertEqual(fx.check().returncode, 0, fx.check().stdout)

            (plans / "tasks.md").unlink()
            flow(fx.root, "build", str(fx.docs))
            self.assertFalse(view.exists())


if __name__ == "__main__":
    unittest.main()
