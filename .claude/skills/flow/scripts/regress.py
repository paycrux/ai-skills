#!/usr/bin/env python3
"""Replay past /flow requests against the current skill and judge only by files and exit codes.

    python3 regress.py [--case GLOB]... [-j N] [--model MODEL] [--keep]

Each case is evals/<name>/: case.json (prompt, branch, expect), fixture/ (a repository at the
moment the request was made), optionally branch/ (files committed on the branch on top of it) and
optionally home/ (the personal $FLOW_HOME — plugins; without it the case runs with an empty one, so
this machine's own plugins never leak in). The fixture is copied to a temp git repo on `branch`, `claude -p`
runs the prompt there, then the checks below run. No LLM grades anything. Exit 1 when any case fails.
"""
import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS = HERE.parent / "evals"
FLOW = HERE / "flow.py"


def sh(cwd, *args, **kw):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, **kw)


def stage(task, key):
    return (task.get("stages") or {}).get(key) or {}


def checklist_items(task, key="tasks"):
    for b in stage(task, key).get("blocks", []):
        if b.get("type") == "checklist":
            yield b, b.get("items", [])


def task_files(repo, domain=None):
    return sorted((repo / "docs").glob(f"{domain or '*'}/tasks/*.json"))


def judge_copy(repo, expect):
    """copy entries must say where, when and in what form each string appears (references/feature.md)."""
    p = repo / expect["feature"]
    if not p.is_file():
        return [f"기능 문서가 없어요: {expect['feature']}"]
    f = json.loads(p.read_text())
    want, items, fails = expect["copy"], f.get("copy") or [], []
    if len(items) < want.get("min", 1):
        fails.append(f"copy {len(items)}개 (기대 {want.get('min', 1)}개 이상)")
    for i, it in enumerate(items):
        missing = [k for k in ("where", "when", "kind", "text", "row") if not str(it.get(k) or "").strip()]
        if missing:
            fails.append(f"copy[{i}] {str(it.get('text', ''))[:30]}: {', '.join(missing)} 없음")
    if want.get("buttons") and not any("[" in str(it.get("kind", "")) for it in items if "모달" in str(it.get("kind", ""))):
        fails.append("모달 copy의 kind에 버튼 이름이 없어요")
    if want.get("multiLine") and not any("” / “" in str(it.get("text", "")) for it in items):
        fails.append("여러 줄 모달을 “…” / “…” 한 항목으로 묶지 않았어요")
    n = want.get("sameTextScreens")
    if n:
        screens = {}
        for it in items:
            screens.setdefault(it.get("text"), set()).add(it.get("where"))
        if not any(len(w) >= n for w in screens.values()):
            fails.append(f"같은 문구를 화면 {n}곳에 따로 적은 항목이 없어요")
    header = expect.get("issueCopyHeader")
    if header:
        for r in f.get("rows", []):
            body = p.parent / (r.get("issueBody") or "")
            if not body.is_file() or header not in body.read_text():
                fails.append(f"{r.get('id')} 이슈 설명에 문구 표 머리 '{header}'가 없어요")
    return fails


def judge_plugin(repo, env, want):
    """The personal plugins Claude wrote: which stages they use and what they rename."""
    home = Path(env["FLOW_HOME"])
    cfg = home / "config.json"
    ids = json.loads(cfg.read_text()).get("plugins", []) if cfg.is_file() else []
    if not ids:
        return ["켜진 플러그인이 없어요 ($FLOW_HOME/config.json plugins)"]
    fails, uses, labels, attached = [], [], {}, []
    for pid in ids:
        pj = home / "plugins" / pid / "plugin.json"
        if not pj.is_file():
            fails.append(f"플러그인 {pid}의 plugin.json이 없어요")
            continue
        body = json.loads(pj.read_text())
        attached += [x.get("stage") for x in body.get("attach") or [] if isinstance(x, dict)]
        st = body.get("stages") or {}
        if "use" in st:
            uses.append(set(st["use"]))
        labels.update(st.get("labels") or {})
    for k in want.get("useLacks") or []:
        if not uses or any(k in u for u in uses):
            fails.append(f"플러그인이 {k} 단계를 끄지 않았어요")
    for k in want.get("attachTo") or []:
        if k not in attached:
            fails.append(f"플러그인이 {k} 단계에 붙지(attach) 않았어요 — 붙은 단계 {attached}")
    for k, v in (want.get("labels") or {}).items():
        if labels.get(k) != v:
            fails.append(f"{k} 단계 이름 {labels.get(k)} (기대 {v})")
    r = sh(repo, sys.executable, str(FLOW), "plugin", "check", "docs", env=env)
    if r.returncode:
        fails.append(f"flow.py plugin check exit {r.returncode}: {r.stdout.strip()[-300:]}")
    return fails


def judge(repo, fixture, expect, env=None, result=""):
    """Returns a list of failure lines; empty means the case passed."""
    fails = []
    env = env or dict(os.environ)
    r = sh(repo, sys.executable, str(FLOW), "check", "docs", env=env)
    if r.returncode:
        fails.append(f"flow.py check exit {r.returncode}: {r.stdout.strip()[-400:]}")
    task = None
    if expect.get("task"):
        p = repo / expect["task"]
        if not p.is_file():
            return fails + [f"작업 파일이 없어요: {expect['task']}"]
        task = json.loads(p.read_text())
    for key, want in (expect.get("status") or {}).items():
        got = stage(task, key).get("status")
        if got != want:
            fails.append(f"{key} 상태 {got} (기대 {want})")
    for key, bad in (expect.get("statusNot") or {}).items():
        if stage(task, key).get("status") == bad:
            fails.append(f"{key} 상태가 {bad}이면 안 돼요")
    if expect.get("checklistEndsWithV"):
        blocks = list(checklist_items(task))
        if not blocks:
            fails.append("03에 Phase 체크리스트가 없어요")
        for b, items in blocks:
            if not items or not str(items[-1].get("id", "")).endswith("-V"):
                fails.append(f"{b.get('id')}의 마지막 항목이 검증(-V)이 아니에요")
    if expect.get("rowLabel"):
        label = expect["rowLabel"]
        first = next(iter(checklist_items(task)), (None, []))[1]
        if not any(row[0] == label for i in first for row in i.get("rows", [])):
            fails.append(f"03 첫 Phase에 '{label}' 행이 없어요")
    if expect.get("grillQuestions"):
        qs = [q for rd in stage(task, "grill").get("rounds", []) for q in rd.get("questions", [])]
        if not qs:
            fails.append("02 질문이 없어요")
        if any(not q.get("intent") for q in qs):
            fails.append("intent 없는 질문이 있어요")
        if not task.get("intent"):
            fails.append("작업 intent가 없어요")
    for tag in expect.get("decided") or []:
        rid, qid = tag.split("-")
        q = next((q for rd in stage(task, "grill").get("rounds", []) if rd.get("id") == rid
                  for q in rd.get("questions", []) if q.get("id") == qid), None)
        if not q:
            fails.append(f"{tag} 질문이 없어요")
            continue
        for key in ("decision", "appliedTo"):
            if not q.get(key):
                fails.append(f"{tag}에 {key}가 없어요")
        if not (q.get("reason") or {}).get("text"):
            fails.append(f"{tag}에 reason이 없어요")
    for tag, want in (expect.get("reasonBy") or {}).items():
        rid, qid = tag.split("-")
        q = next((q for rd in stage(task, "grill").get("rounds", []) if rd.get("id") == rid
                  for q in rd.get("questions", []) if q.get("id") == qid), {})
        got = (q.get("reason") or {}).get("by")
        if got != want:
            fails.append(f"{tag} reason.by {got} (기대 {want})")
    if expect.get("maxRounds") is not None:
        n = len(stage(task, "grill").get("rounds", []))
        if n > expect["maxRounds"]:
            fails.append(f"질문 라운드 {n}개 (기대 {expect['maxRounds']}개 이하) — 확인 질문을 또 열었어요")
    if expect.get("pruned") and not task.get("pruned"):
        fails.append("끝난 작업인데 prune하지 않았어요")
    if expect.get("domains") is not None:
        got = sorted(p.parent.name for p in (repo / "docs").glob("*/domain.json"))
        if got != sorted(expect["domains"]):
            fails.append(f"도메인 {got} (기대 {expect['domains']})")
    for dom, n in (expect.get("newTasksIn") or {}).items():
        before = {p.name for p in task_files(fixture, dom)}
        new = [p.name for p in task_files(repo, dom) if p.name not in before]
        if len(new) != n:
            fails.append(f"{dom}에 새 작업 {len(new)}개 (기대 {n}): {new}")
    for key, want in (expect.get("anyTaskStatus") or {}).items():
        if not any(stage(json.loads(p.read_text()), key).get("status") == want for p in task_files(repo)):
            fails.append(f"{key} 상태가 {want}인 작업이 없어요")
    if expect.get("copy"):
        fails += judge_copy(repo, expect)
    if expect.get("plugin"):
        fails += judge_plugin(repo, env, expect["plugin"])
    for word in expect.get("resultMentions") or []:
        if word not in result:
            fails.append(f"마지막 답에 '{word}'가 없어요 — 답 끝: {result.strip()[-300:]}")
    if expect.get("srcUnchanged"):
        changed = sh(repo, "git", "status", "--porcelain", "--", "src").stdout.strip()
        if changed:
            fails.append(f"승인 전에 src가 바뀌었어요: {changed.splitlines()[:5]}")
    return fails


def run_case(case_dir, args):
    case = json.loads((case_dir / "case.json").read_text())
    fixture = case_dir / "fixture"
    tmp = Path(tempfile.mkdtemp(prefix=f"flow-regress-{case_dir.name}-"))
    repo = tmp / "repo"
    shutil.copytree(fixture, repo)
    for cmd in (("git", "init", "-q", "-b", "main"), ("git", "add", "-A"),
                ("git", "-c", "user.email=regress@local", "-c", "user.name=regress", "commit", "-qm", "fixture"),
                ("git", "switch", "-q", "-c", case["branch"])):
        sh(repo, *cmd)
    if (case_dir / "branch").is_dir():  # work already done on the branch, committed on top of the fixture
        shutil.copytree(case_dir / "branch", repo, dirs_exist_ok=True)
        sh(repo, "git", "add", "-A")
        sh(repo, "git", "-c", "user.email=regress@local", "-c", "user.name=regress", "commit", "-qm", "branch work")
    cmd = ["claude", "-p", case["prompt"], "--output-format", "json", "--permission-mode", "bypassPermissions",
           "--no-session-persistence"]
    if args.model:
        cmd += ["--model", args.model]
    started = time.time()
    home = tmp / "flow-home"
    if (case_dir / "home").is_dir():
        shutil.copytree(case_dir / "home", home)
    else:
        home.mkdir()
    env = {**os.environ, "FLOW_NO_OPEN": "1", "FLOW_HOME": str(home)}
    try:
        proc = sh(repo, *cmd, env=env, timeout=args.timeout)
        out, code = proc.stdout, proc.returncode
    except subprocess.TimeoutExpired:
        out, code = "", "timeout"
    cost, result = None, ""
    try:
        data = json.loads(out)
        res = next((m for m in reversed(data) if m.get("type") == "result"), {}) if isinstance(data, list) else data
        cost, result = res.get("total_cost_usd"), str(res.get("result") or "")
    except ValueError:
        pass
    fails = [f"claude -p exit {code}"] if code else []
    fails += judge(repo, fixture, case.get("expect") or {}, env, result)
    if not args.keep and not fails:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"case": case_dir.name, "ok": not fails, "fails": fails, "seconds": round(time.time() - started),
            "cost": cost, "dir": None if not fails and not args.keep else str(repo)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", action="append", default=[], help="glob on case names")
    ap.add_argument("-j", "--jobs", type=int, default=1)
    ap.add_argument("--model")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--keep", action="store_true", help="keep temp repos of passing cases too")
    ap.add_argument("--json", help="write the results to this file")
    args = ap.parse_args()
    cases = sorted(p for p in EVALS.iterdir() if (p / "case.json").is_file()
                   and (not args.case or any(fnmatch.fnmatch(p.name, g) for g in args.case)))
    if not cases:
        sys.exit("사례가 없어요")
    print(f"사례 {len(cases)}개 실행 중 (동시 {args.jobs})", flush=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda c: run_case(c, args), cases))
    for r in results:
        cost = f" ${r['cost']:.2f}" if r["cost"] else ""
        print(f"{'통과' if r['ok'] else '실패'}  {r['case']}  {r['seconds']}s{cost}")
        for f in r["fails"]:
            print(f"    - {f}")
        if r["dir"]:
            print(f"    저장소: {r['dir']}")
    total = sum(r["cost"] or 0 for r in results)
    print(f"통과 {sum(r['ok'] for r in results)}/{len(results)} · 비용 ${total:.2f}")
    if args.json:
        Path(args.json).write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    sys.exit(0 if all(r["ok"] for r in results) else 1)


if __name__ == "__main__":
    main()
